import os

import pytest

from src.slug_farm.bash_slugs import BashSlug

# --- Fixtures ---


@pytest.fixture
def file_system_farm(tmp_path):
    """
    Creates a temporary sandbox directory for live execution tests.
    Structure:
    /farm/
      ├── grain.txt  (contains 'wheat')
      ├── corn.txt   (contains 'maize')
      └── harvest/   (directory)
          └── yields.csv
    """
    farm_dir = tmp_path / "farm"
    farm_dir.mkdir()

    (farm_dir / "grain.txt").write_text("wheat\nbarley\nrye")
    (farm_dir / "corn.txt").write_text("maize\nsweetcorn")

    harvest_dir = farm_dir / "harvest"
    harvest_dir.mkdir()
    (harvest_dir / "yields.csv").write_text("season,tons\n2025,500\n2026,750")

    return farm_dir.resolve()


@pytest.fixture
def git_tree():
    """Returns a standard git-style branching hierarchy for testing logic."""
    git = BashSlug(name="git", command="git")
    remote = git.branch(branch_name="remote", command="remote")
    remote_v = remote.branch(branch_name="verbose", slug_kwargs={"v": True})
    return {"git": git, "remote": remote, "verbose": remote_v}


# --- Structural & Logic Tests (Dry Runs) ---


def test_deep_inheritance_naming(git_tree):
    """Verify that the dot-notation name reflects the full inheritance path."""
    leaf = git_tree["verbose"]
    assert leaf.name == "git.remote.verbose"


def test_flag_sorting_logic():
    """Verify short and long flags sort by length then alphabet."""
    slug = BashSlug("test", "cmd", slug_kwargs={"zebra": 1, "a": True, "z": True})
    # Order should be: -a, -z, --apple, --zebra
    result = slug(
        test=True,
        task_kwargs={
            "apple": 2,
        },
    )

    assert result.output == "cmd -a -z --apple 2 --zebra 1"

    sub_slug_command_test = slug.branch(
        "sub",
        "sub_command",
        slug_kwargs={
            "mangos": 4,
        },
    )

    sub_result = sub_slug_command_test(task_kwargs={"c": True}, test=True)
    assert sub_result.output == "cmd -a -z --zebra 1 sub_command -c --mangos 4"


def test_complex_quoting_with_sed():
    """Verify that regex strings are safely escaped."""
    sed = BashSlug("editor", "sed")
    result = sed(
        command="file.txt",
        task_kwargs={
            "i": True,
            "e": "'s/wheat/GRAIN/g'",
        },
        test=True,
    )
    assert "'s/wheat/GRAIN/g'" in result.output


def test_prefix_wrapper_logic():
    """Verify prepending a 'wrapper' like 'time' or environment variables."""
    timer = BashSlug("timer", slug_kwargs={"-time": True})

    result = timer(
        command="ls",
        task_kwargs={"-la": True},
        test=True,
    )
    assert result.output == "-time ls -la"


# --- Live Execution Tests (Functional) ---


def test_live_grep_execution(file_system_farm):
    """Verify grep finds content within the temp file system."""
    grepper = BashSlug(name="grepper", command="grep")

    grep_with_flags = grepper.branch(
        "with_flags",
        slug_kwargs={
            "r": True,
            "n": True,
            "F": "wheat",
        },
    )

    result = grep_with_flags(
        command=str(file_system_farm),
    )

    assert result.ok is True
    assert "grain.txt" in result.output
    assert "1:wheat" in result.output
    assert "corn.txt" not in result.output


def test_live_find_directory_traversal(file_system_farm):
    """Verify find correctly uses single-dash predicates via manual override."""
    finder = BashSlug("finder", "find")
    path_slug = finder.branch("path", command=str(file_system_farm))
    result = path_slug(task_kwargs={"-name": "*.csv"})
    assert result.ok is True
    assert "yields.csv" in result.output


def test_live_execution_failure_capture():
    """Verify that a shell error is captured in the SlugResult error field."""
    lister = BashSlug("lister", "ls")
    result = lister(command="/tmp/folder_that_is_not_real_12345")

    assert result.ok is False
    assert result.status != 0
    assert "No such file or directory" in result.error


def test_slug_concatenation_simulation(file_system_farm):
    """
    Tests 'piping' logic by passing the output of one slug
    as the command input of another.
    """
    finder = BashSlug("finder", "find")
    find_res = finder(command=str(file_system_farm), task_kwargs={"-name": "grain.txt"})

    found_path = find_res.output.strip()

    reader = BashSlug("reader", "cat")
    read_res = reader(command=found_path)

    assert "wheat" in read_res.output
    assert "barley" in read_res.output


def test_pipe_limitation_awareness():
    """Verify that literal pipes in command strings are treated as arguments, not operators.
    For security reasons, it is key that this fails"""

    lister = BashSlug("ls", "ls")
    result = lister(command="| grep wheat")

    assert result.ok is False
    assert "No such file" in result.error


def test_piping_workaround(file_system_farm):
    """
    Simulation of 'ls | grep grain' by passing ls output
    to a grep command that searches the text.
    """
    lister = BashSlug("lister", "ls")
    ls_result = lister(command=str(file_system_farm))

    assert "grain.txt" in ls_result.output

    grepper = BashSlug("grepper", "grep")
    paths = [str(file_system_farm / f) for f in ls_result.output.split()]
    result = grepper(command=" ".join(paths), task_kwargs={"e": "wheat"})

    assert "grain.txt" in result.output
    assert "wheat" in result.output
