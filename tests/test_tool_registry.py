import pytest
from smartmyodoo.swarm.tools import TOOL_REGISTRY, _generate_schema, register_tool

def test_tool_registry_contains_odoo_search():
    assert "odoo_search" in TOOL_REGISTRY
    assert callable(TOOL_REGISTRY["odoo_search"]["callable"])
    assert "schema" in TOOL_REGISTRY["odoo_search"]

def test_schema_generation():
    def dummy_tool(arg1: str, arg2: int = 5) -> str:
        """Dummy docstring."""
        return "ok"
    
    schema = _generate_schema(dummy_tool)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "dummy_tool"
    assert schema["function"]["description"] == "Dummy docstring."
    assert "arg1" in schema["function"]["parameters"]["properties"]
    assert "arg2" in schema["function"]["parameters"]["properties"]
    assert "arg1" in schema["function"]["parameters"]["required"]
    assert "arg2" not in schema["function"]["parameters"]["required"]

def test_scaffold_module_schema():
    schema = TOOL_REGISTRY["scaffold_module"]["schema"]
    assert "module_name" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["properties"]["module_name"]["type"] == "string"
