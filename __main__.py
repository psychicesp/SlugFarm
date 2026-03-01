# %%
from src.slug_farm.request_slugs import RequestSlug

rest_slug = RequestSlug(
    name="dumb",
    base_url="https://www.dumb_url.com?dumb_param=dumb",
)

butt_slug = rest_slug.branch(
    branch_name="butt",
    url_segment="butt?butt_param=dumb",
)

# %%
