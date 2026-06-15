"""S1.4 (dowód): scaffold_module blokuje path traversal z wejścia LLM.

PRZED: module_name szło wprost do os.path.join → '../..' pozwalało pisać poza custom_addons/.
PO: walidacja regexem + wymuszenie ścieżki wewnątrz custom_addons/.
"""

from smartmyodoo.swarm.tools import scaffold_module


def test_blocks_path_traversal():
    assert scaffold_module("../evil").startswith("❌")
    assert scaffold_module("../../etc/passwd").startswith("❌")
    assert scaffold_module("foo/bar").startswith("❌")
    assert scaffold_module("").startswith("❌")


def test_valid_module_name_creates_module(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = scaffold_module("sprzedaz_raporty")
    assert "Utworzono" in res
    assert (
        tmp_path / "custom_addons" / "sprzedaz_raporty" / "__manifest__.py"
    ).exists()
