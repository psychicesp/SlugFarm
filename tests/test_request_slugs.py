import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI, HTTPException
from yarl import URL

from slug_farm import RequestPackage, RequestSlug


@pytest.fixture(scope="module")
def farm_server():
    app = FastAPI()
    database = {
        "crops": {
            "corn": {
                "name": "corn",
                "tons": 100,
            },
            "soy": {
                "name": "soybeans",
                "tons": 80,
            },
        },
    }

    @app.get("/crops")
    def list_crops():
        return database["crops"]

    @app.post("/crops", status_code=201)
    def create_crop(payload: dict):
        name = payload.get("name")
        database["crops"][name] = payload
        return payload

    @app.patch("/crops/{name}")
    def update_crop(name: str, payload: dict):
        if name not in database["crops"]:
            raise HTTPException(status_code=404, detail="not found")
        database["crops"][name].update(payload)
        return database["crops"][name]

    # --- NEW ENDPOINT FOR PLACEHOLDERS ---
    @app.delete("/crops/{name}")
    def delete_crop(name: str):
        if name not in database["crops"]:
            raise HTTPException(status_code=404, detail="not found")
        return database["crops"].pop(name)

    config = uvicorn.Config(app, host="127.0.0.1", port=8080, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield "http://127.0.0.1:8080"

    server.should_exit = True
    thread.join(timeout=2)


# --- Structural & Logic Tests (Dry Runs) ---


@pytest.mark.dependency()
def test_slug_initialization():
    """Verify basic attribute storage and upper-casing."""
    slug = RequestSlug(
        name="root",
        base_url="https://api.farm.com",
        method="post",
        timeout=30,
    )
    result = slug(test=True)
    package = result.output
    assert slug.method == "POST"
    assert slug.timeout == 30
    assert package.url == "https://api.farm.com/"


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

    strict_slug.method = "POST"

    post_result = strict_slug(
        task_kwargs={
            "id": 1,
            "name": "wheat",
            "secret_key": "hacker",
        },
        test=True,
    )

    pkg = post_result.output
    assert "id" in pkg.params
    assert "name" in pkg.params
    assert "secret_key" not in pkg.params, (
        "Filter failed to exclude unauthorized param!"
    )
    assert "id" not in pkg.json_body
    assert "name" not in pkg.json_body
    assert "secret_key" in pkg.json_body
    assert "secret_key" in pkg.json_body


def test_placeholder_structural_logic():
    """Verify regex replacement and error handling without a live server."""
    slug = RequestSlug(
        name="placeholder_test", base_url="https://api.com/v1/{ category }/{item_id}"
    )

    result = slug(
        task_kwargs={"category": "fruits", "item_id": 55, "extra": "stay"}, test=True
    )
    pkg = result.output

    assert pkg.url == "https://api.com/v1/fruits/55"
    assert "category" in pkg.params
    assert "item_id" in pkg.params

    with pytest.raises(Exception, match="Unable to place"):
        slug(task_kwargs={"category": "missing_item_id"}, test=True)


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
    assert "corn" in result.output
    assert "soy" in result.output


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


@pytest.mark.dependency(depends=["test_modification_patch"])
def test_placeholder_live_execution(farm_server):
    """Verify live DELETE request using URL placeholders."""
    api = RequestSlug("farm", base_url=farm_server)

    delete_slug = api.branch(
        "delete_crop", url_segment="/crops/{crop_name}", method="DELETE"
    )

    result = delete_slug(task_kwargs={"crop_name": "wheat"})

    assert result.status == 200
    assert result.output["name"] == "wheat"

    check = RequestSlug("check", base_url=f"{farm_server}/crops")()
    assert "wheat" not in check.output
