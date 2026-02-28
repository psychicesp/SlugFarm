#%%
from src.slug_farm.bash_slugs import BashSlug

docker_slug = BashSlug(
    name="docker",
    command="docker",
)

docker_ps = docker_slug.branch(
    branch_name="ps",
    command="ps"
)

# %%
