import os
from uuid import uuid4

import pytest

from slug_farm import SlugRegistry, PythonSlug, BashSlug

@pytest.fixture
def populate_registry():
    
    test_registry = SlugRegistry()
    
    def four():
        return 4
    
    def add_four(number:int):
        return number + 4 
    
    four_slug = PythonSlug(name = "four", python_func=four)
    add_four_slug = PythonSlug(name = "four", python_func=add_four)