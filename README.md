<div align="center">
  <img src="https://raw.githubusercontent.com/psychicesp/SlugFarm/main/SlugFarm.png" height="160" alt="logo">
  <h1>Slug Farm</h1>
</div>

> **Status:** For my use this is in beta, but for broad/general-purpose use, this is still effectively **pre-alpha ideation**.  

---

## What “slug” means here

Package gets its name from the idea of boiling a unit of functionality down to a small, addressable shape: a command and kwargs.

- The **object** is a `Slug` (`BashSlug`, `RequestSlug`, etc.)
- The **slug** is the name used to address that object inside a registry

So the slug is ultimately the registry key for a callable unit of work.

---

## What this is

Slug Farm is a framework for reducing different kinds of work into one callable shape:

```python
result = some_slug(command="...", task_kwargs={...})
```

There is also a `SlugRegistry` which stores those slugs by name

`result` is intended to always be a `SlugResult`.

### Core use case

I built this to enable **centralized task scheduling**, holding jobs and cron strings in SQL rather than crontabs which needed to be overwritten to finagle one little kwarg.

I wanted a way to represent tasks across different backends in one consistent structure so they could be stored, patched, replayed, and executed later without every integration inventing its own shape. To store and refer to such a function in SQL, it needed a unique identifier: **a "slug"**

The useful part is the uniformity:

> Any task becomes: **(slug name, command, kwargs)**

That has been especially useful for:
- REST APIs
- shell commands
- UDP messages
- Python callables I want accessible through the same registry shape

### How the project actually developed

This did **not** start as “look at this elegant abstraction.”

It started as a bespoke practical scheduling enabling tool not originally intended for broad use.

The original goal was to make it easy to define and store tasks in a persistent, patchable format. While building easy to define tasks stored in a persistent, patchable format, I found a second benefit that turned out to be one of the more interesting parts of the project: **it is a concise way to move through a branching structure while capturing every viable intermediate function on the way.**

That ended up being especially nice for tree-like RestAPIs and Bash commands

---

## What this is”

SlugFarm 'Slug' objects offer
- a persistent task shape
- one invocation model across different backends
- inheritance/branching for large families of related tasks
- something I can store in a database and patch without rewriting code paths

If you just want a small local abstraction around a handful of operations, then yes: a dictionary of functions is probably still the better tool.

---

## What it is not

This is **not** *currently*:
- a validation-heavy framework
- an automatic hydration system
- a polished declarative config engine
- a batteries-included orchestration platform
- a general replacement for normal Python APIs

Right now it is a working core for a very opinionated pattern. Being opinionated was necessary for succinct usage but the initial buy-in for opinionated structures is almost always a large barrier to entry, and to be perfectly transparent, right now a dictionary of functions is probably a better solution to whatever use-case you're considering over a SlugRegistry.

The fact is that DSLs are usually a bad idea and that opinionated structures take time to mature and become good, and this is still a young project.  I'm proud of it and I see potential but it is what it is.

---

## What’s in here right now

### BashSlug
Builds a command + flags list and executes with `subprocess`.

- Does **not** interpret pipes or shell operators (though workarounds exist)
- Literal `|` is treated as an argument, not an operator
- That restriction is intentional

### RequestSlug
Builds HTTP requests using `requests`, with inherited URL segments, parameter merging, and JSON-body logic.

- Supports placeholders like `/crops/{crop_name}`
- GET carries params
- POST/PUT/PATCH carry params and JSON bodies
- Includes include/exclude filtering for request data (this is admittedly a little clunk.  Will need usage to come up with a better way)

### UDP_Slug
Sends UDP payloads, optionally in bursts, with a shared UUID per run. These don't benefit from the branching declaration structure and I originally jsut made it so that I could put UDP calls into the same structure, but these ended up pretty nice for me to work with.

### PythonSlug
Wraps a Python callable so it fits the same `(command, task_kwargs)` invocation style.

This is mainly useful if you are already benefiting from the registry shape and want Python tasks to participate in the same system. 

---

## Registry

The registry is the part that makes the naming actually matter:

- the `Slug` object is the implementation
- the slug name is the address
- the registry is what makes tasks easy to store, replay, and patch

`SlugRegistry` core works now. It is meant to be so much more, but its core is usable for my SQL-backed task scheduling so it has at least one use-case.  Maybe more

---

## Installation

```bash
pip install slug_farm
```

From source:

```bash
git clone <repo>
cd SlugFarm
pip install -e ".[dev]"
```

---

## Quickstart

### BashSlug

```python
from slug_farm import BashSlug

git = BashSlug(name="git", command="git")
status = git.branch(branch_name="status", command="status")

result = status(task_kwargs={"untracked-status": "no", "s": True})
# executes: git status -s --untracked-status no
```

### RequestSlug

```python
from slug_farm import RequestSlug

api = RequestSlug(
    name="api",
    base_url="https://example.com/v1",
    headers=SOME_HEADERS_DEFINED_ELSEWHERE,
)

crops = api.branch(
    branch_name="crops",
    url_segment="crops",
)

get_result = crops(task_kwargs={"limit": 10})

add_crops = crops.branch(
    branch_name="add",
    url_segment="add",
    method="POST",
)

add_crops(task_kwargs={"apples": 10})
# Sends POST to https://example.com/v1/crops/add
```

For placeholder-based routes:

```python
get_specific = crops.branch(
    branch_name="specific",
    url_segment="{crop_id}",
)

get_specific(task_kwargs={"crop_id": "crop_2b67d"})
# Sends GET to https://example.com/v1/crops/crop_2b67d
```

### UDP_Slug

```python
from slug_farm import UDP_Slug

slug = UDP_Slug(
    "telemetry",
    url="127.0.0.1",
    port=9999,
    burst_size=5,
    burst_delay_ms=50,
)

result = slug(task_kwargs={"hello": "world"})
print(result.ok, result.status)
```

---

## Current limitations

A few things are important to say plainly:

- this structure is opinionated.  This is necessary but the package simply is not mature enough to benefit from it and now mainly carries the drawbacks
- some workflows will feel cleaner with ordinary functions
- validation and declarative hydration are **not** real parts of the package yet
- error messaging still has room to improve.  Opinionated packages can have beautiful clean and informative error structures.  This hasn't them.
- the broader persistence tooling is still early

The pitch is:

> If you want a rigid but useful task shape that works across multiple backends and can be addressed by name, this may be a very good fit.

---

## Where I want to take it

Not part of the current identity yet, but very much the direction:

- YAML-based slug hydration delcaration and hydration
    - This would add another step in the process, but that step could be very helpful.  The output of a YAML validator can help early users learn the opinionated structure MUCH better than doc-strings and error messages
- better validation and better author-facing errors
- clearer persistence workflows around registries
    - This does not have any native enablers of the SQL-backed slug registry I made it for, and that might be nice

Those are not being listed as current features. They are the obvious next places this structure could pay off.

---

## Contributing

PRs and tests are welcome, especially around:

- registry behavior
- persistence patterns
- clearer docs and examples
- better error messages
- logging integration
    - I personally write around pythons `logging` modules weird global behavior, so any logging integration should not lean it either
- edge-case safety
- declarative setup and hydration paths
- `requests.Session` integration with `RequestSlug`, but I'm waiting for a less shoe-horned usecase for it to precipitate

One of the upsides of an opinionated structure is that it creates room for better tooling. That is still one of the most interesting things about this project.

---

## Postscript: where the branching pattern gets good

The strongest part of this library is not “I can call one thing.”

The strongest part is that it gives you a concise way to move through a branching structure while capturing every viable intermediate function on the way.

That means the intermediate nodes are not throwaway setup code. They are real reusable objects.

### Postscript A: wide branching API capture

This is the clearest example.

Say you are capturing a section of a project-management API:

- `/v1/orgs/{org_id}`
- `/v1/orgs/{org_id}/projects`
- `/v1/orgs/{org_id}/projects/{project_id}`
- `/v1/orgs/{org_id}/projects/{project_id}/tasks`
- `/v1/orgs/{org_id}/projects/{project_id}/tasks/{task_id}`
- `/v1/orgs/{org_id}/projects/{project_id}/tasks/{task_id}/comments`
- `/v1/orgs/{org_id}/projects/{project_id}/members`

You can define that shape as a branching tree and keep the intermediate objects meaningful:

```python
from slug_farm import RequestSlug

API_HEADERS = {
    "Authorization": "Bearer <token>",
    "Accept": "application/json",
}

api = RequestSlug(
    name="pm_api",
    base_url="https://api.example.com/v1",
    headers=API_HEADERS,
)

orgs = api.branch(
    branch_name="orgs",
    url_segment="orgs",
)

org = orgs.branch(
    branch_name="org",
    url_segment="{org_id}",
)

projects = org.branch(
    branch_name="projects",
    url_segment="projects",
)

list_projects = projects

create_project = projects.branch(
    branch_name="create",
    method="POST",
)

project = projects.branch(
    branch_name="project",
    url_segment="{project_id}",
)

update_project = project.branch(
    branch_name="update",
    method="PATCH",
)

delete_project = project.branch(
    branch_name="delete",
    method="DELETE",
)

members = project.branch(
    branch_name="members",
    url_segment="members",
)

list_members = members

add_member = members.branch(
    branch_name="add",
    method="POST",
)

tasks = project.branch(
    branch_name="tasks",
    url_segment="tasks",
)

list_tasks = tasks

create_task = tasks.branch(
    branch_name="create",
    method="POST",
)

task = tasks.branch(
    branch_name="task",
    url_segment="{task_id}",
)

update_task = task.branch(
    branch_name="update",
    method="PATCH",
)

delete_task = task.branch(
    branch_name="delete",
    method="DELETE",
)

comments = task.branch(
    branch_name="comments",
    url_segment="comments",
)

list_comments = comments

create_comment = comments.branch(
    branch_name="create",
    method="POST",
)

comment = comments.branch(
    branch_name="comment",
    url_segment="{comment_id}",
)

delete_comment = comment.branch(
    branch_name="delete",
    method="DELETE",
)
```

And then use whichever level of the tree you actually need:

```python
projects_result = list_projects(task_kwargs={"org_id": "org_123", "limit": 25})

create_task_result = create_task(
    task_kwargs={
        "org_id": "org_123",
        "project_id": "proj_9",
        "title": "Draft release notes",
        "priority": "high",
    }
)

delete_comment_result = delete_comment(
    task_kwargs={
        "org_id": "org_123",
        "project_id": "proj_9",
        "task_id": "task_44",
        "comment_id": "cmt_12",
    }
)
```

That is the gold nugget I did not set out looking for.

It is a concise way to navigate a branching structure and preserve all the useful intermediate handles instead of just hardcoding a pile of endpoint-specific functions.

### Postscript B: branching bash command families

The same pattern can be nice with command families too.

Take a git-flavored hierarchy where the intermediate branches are worth keeping around:

```python
from slug_farm import BashSlug

git = BashSlug(name="git", command="git")

remote = git.branch(
    branch_name="remote",
    command="remote",
)

remote_add = remote.branch(
    branch_name="add",
    command="add",
)

remote_remove = remote.branch(
    branch_name="remove",
    command="remove",
)

checkout = git.branch(
    branch_name="checkout",
    command="checkout",
)

checkout_new = checkout.branch(
    branch_name="new",
    slug_kwargs={"b": True},
)

log = git.branch(
    branch_name="log",
    command="log",
)

log_oneline = log.branch(
    branch_name="oneline",
    slug_kwargs={"oneline": True},
)

log_graph = log_oneline.branch(
    branch_name="graph",
    slug_kwargs={"graph": True},
)
```

And then call any level you want:

```python
remote_add(command="origin https://github.com/example/repo.git")

checkout_new(command="feature/crops")

log_graph(task_kwargs={"decorate": True, "all": True}, test=True)
# git log --oneline --graph --all --decorate
```

This works well when a command family has a natural branching structure and you want to capture the intermediate steps as reusable named objects instead of rebuilding them every time.

Even bypassing the SlugRegistry, it makes it easy to shove all bash commands and RestAPI function declaration into a single file and to import from there.  For me it also got very readable very quickly and scanning through pythonified RestAPI functions and a Swagger page side-by-side has been very efficient.

---

## License

MIT. See LICENSE.