import os
import unittest
import ast


class TestSmartChatManifest(unittest.TestCase):
    def setUp(self):
        super(TestSmartChatManifest, self).setUp()
        self.manifest_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "__manifest__.py"
        )

    def test_manifest_keys(self):
        """Testuje czy manifest posiada kluczowe elementy"""
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_content = f.read()

        manifest_dict = ast.literal_eval(manifest_content)

        # Sprawdzamy kluczowe property dla modułu OWL
        self.assertIn("depends", manifest_dict)
        self.assertIn("data", manifest_dict)
        self.assertIn("assets", manifest_dict)

        # Weryfikacja czy web i base są w zależnościach
        self.assertIn("web", manifest_dict["depends"])
        self.assertIn("base", manifest_dict["depends"])

        # Weryfikacja czy assets_backend ma zadeklarowane pliki widgetu
        assets_backend = manifest_dict["assets"].get("web.assets_backend", [])
        self.assertTrue(any("chat_widget.js" in path for path in assets_backend))
        self.assertTrue(any("shadow_banner.js" in path for path in assets_backend))
