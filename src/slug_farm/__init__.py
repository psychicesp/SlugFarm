from .base import CommandSegment, Slug, SlugRegistry, SlugResult
from .bash_slugs import BashSlug
from .python_slug import PythonSlug
from .request_slugs import RequestPackage, RequestSlug
from .udp_slugs import UDP_Package, UDP_Slug
from .registries import SlugRegistry

__all__ = [
    "CommandSegment",
    "Slug",
    "SlugRegistry",
    "SlugResult",
    "BashSlug",
    "PythonSlug",
    "RequestPackage",
    "RequestSlug",
    "UDP_Package",
    "UDP_Slug",
]
