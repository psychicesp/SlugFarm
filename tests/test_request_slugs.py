import threading

import pytest
from flask import Flask, jsonify, request
from werkzeug.serving import make_server
from yarl import URL

from src.slug_farm.request_slugs import RequestPackage, RequestSlug


@pytest.fixture(scope="module")
def farm_server():
    app = Flask(__name__)
    database = {"crops": {}}

    @app.route("/crops", methods=["GET", "POST"])
    def crops_handler():
        if request.method == "POST":
            data = request.json
            name = data.get("name")
            database["crops"][name] = data
            return jsonify(data), 201
        return jsonify(database["crops"])

    @app.route("/crops/<name>", methods=["PATCH"])
    def update_handler(name):
        if name not in database["crops"]:
            return jsonify({"error": "not found"}), 404
        database["crops"][name].update(request.json)
        return jsonify(database["crops"][name]), 200

    server = make_server("127.0.0.1", 8080, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:8080"
    server.shutdown()


# --- Structural & Logic Tests (Dry Runs) ---


@pytest.mark.dependency()
def test_slug_initialization():
    """Verify basic attribute storage and upper-casing."""
    slug = RequestSlug(
        name="root",
        base_url="https://api.farm.com",
        method="post",  # Testing case-insensitivity
        timeout=30,
    )
    result = slug(test=True)
    package = result.output
    assert slug.method == "POST"
    assert slug.timeout == 30
    assert str(package.url) == "https://api.farm.com"


@pytest.mark.dependency(depends=["test_slug_initialization"])
def test_branching_and_url_assembly():
    """Verify path concatenation and parameter merging."""
    root = RequestSlug(
        name="api",
        base_url="https://farm.com/v1",
        params={"api_key": "123"},
    )

    leaf = root.branch(
        branch_name="crops",
        url_segment="/wheat",
        sub_params={"units": "tons"},
    )

    result = leaf(test=True)
    package = result.output

    assert package.url == "https://farm.com/v1/wheat"
    assert package.params == {"api_key": "123", "units": "tons"}
    assert leaf.name == "crops.api"


@pytest.mark.dependency(depends=["test_branching_and_url_assembly"])
def test_param_filtering_logic():
    """Verify include/exclude logic in the Package assembly."""
    strict_slug = RequestSlug(
        name="strict", base_url="https://api.com", include_params=["id", "name"]
    )

    result = strict_slug(
        task_kwargs={"id": 1, "name": "wheat", "secret_key": "hacker"}, test=True
    )
    pkg = result.output

    assert "id" in pkg.params
    assert "name" in pkg.params
    assert "secret_key" not in pkg.params, (
        "Filter failed to exclude unauthorized param!"
    )


@pytest.mark.dependency(depends=["test_param_filtering_logic"])
def test_get_vs_post_body_logic():
    """Verify that GET requests don't carry JSON bodies."""
    root = RequestSlug("api", "https://api.com")

    # A GET request with kwargs
    result = root(task_kwargs={"search": "wheat"}, test=True)
    get_pkg = result.output

    assert get_pkg.method == "GET"
    assert get_pkg.params["search"] == "wheat"
    assert get_pkg.json_body == {}, "GET request should have empty json_body"

    # A POST request with same kwargs
    post_slug = root.branch("sender", method="POST")

    result = post_slug(task_kwargs={"amount": 10}, test=True)
    post_pkg = result.output
    assert post_pkg.method == "POST"
    assert post_pkg.json_body["amount"] == 10


# --- Live Execution Tests (Functional) ---
@pytest.mark.dependency()
def test_discovery_get(farm_server):
    """WEIGHT 1: Verify the API is up and empty."""
    api = RequestSlug("farm", base_url=farm_server)
    crops = api.branch("crops", url_segment="/crops")

    result = crops()
    assert result.ok is True
    assert result.output == {}


@pytest.mark.dependency(depends=["test_discovery_get"])
def test_creation_post(farm_server):
    """WEIGHT 2: Create a resource. Fails if GET failed."""
    api = RequestSlug("farm", base_url=farm_server)
    crops = api.branch("crops", url_segment="/crops", method="POST")

    # We plant 500 tons of wheat
    result = crops(task_kwargs={"name": "wheat", "tons": 500})

    assert result.status == 201
    assert result.output["name"] == "wheat"


@pytest.mark.dependency(depends=["test_creation_post"])
def test_modification_patch(farm_server):
    """WEIGHT 3: Update a resource. Fails if POST failed."""
    api = RequestSlug("farm", base_url=farm_server)
    wheat_api = api.branch("wheat", url_segment="/crops/wheat", method="PATCH")

    result = wheat_api(task_kwargs={"tons": 1200})

    assert result.ok is True
    assert result.output["tons"] == 1200

    final_check = RequestSlug("check", base_url=f"{farm_server}/crops")()
    assert final_check.output["wheat"]["tons"] == 1200
