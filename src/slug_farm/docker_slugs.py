from src.slug_farm.base import Slug, SlugResult


class DockerSlug(Slug):
    def execute(self, tokens: list[str]) -> SlugResult:
        full_tokens = ["docker", "exec"] + tokens
        return super().execute(full_tokens)


# # Deep usage
# # 1. Base docker slug with 'exec' flags
# d = DockerSlug("root_exec").branch("root_session", "", {"u": "root"})
# # 2. Target a specific container
# d_target = d.branch("my_app_container", "my_app_1")
# # 3. Final call
# # ['docker', 'exec', '-u', 'root', 'my_app_1', 'ls', '-la']
# d_target("ls", {"la": True})
