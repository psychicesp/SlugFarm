import os
from uuid import uuid4

import pytest

from slug_farm import SlugRegistry, PythonSlug, BashSlug


# --- Structural & Logic Tests (Dry Runs) ---


# --- Live Execution Tests (Functional) ---

def test_function_calling():
    test_registry = SlugRegistry()

    def four():
        return 4
 
    def add_four(number:int):
        return number + 4 

    four_slug = PythonSlug(name = "four", python_func=four)
    add_four_slug = PythonSlug(name = "add_four", python_func=add_four)

    test_registry.register(four_slug)
    test_registry.register(add_four_slug)
    
    assert test_registry["four"]().output == 4
    assert test_registry["add_four"](task_kwargs = {"number": 4}).output==8