import unittest
import json
import os
import datetime
import vault
import vault_server

class TestVaultServer(unittest.TestCase):
    def setUp(self):
        vault.PIN_SALT_FILE = "test_api_pin_salt.cfg"
        vault.MASTER_SALT_FILE = "test_api_master_salt.cfg"
        vault.PIN_KEY_FILE = "test_api_pin_key.enc"
        vault.MASTER_KEY_FILE = "test_api_master_key.enc"
        vault.VAULT_DATA_FILE = "test_api_vault_data.enc"
        
        self.files_to_cleanup = [
            vault.PIN_SALT_FILE, vault.MASTER_SALT_FILE, 
            vault.PIN_KEY_FILE, vault.MASTER_KEY_FILE, vault.VAULT_DATA_FILE
        ]
        
        for f in self.files_to_cleanup:
            if os.path.exists(f): os.remove(f)
            
        vault.init_vault_core("1111", "master")
        self.app = vault_server.app.test_client()
        self.app.testing = True
        
        self.token = "1111"
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        for f in self.files_to_cleanup:
            if os.path.exists(f): os.remove(f)

    def test_api_crud_operations(self):
        # 1. CREATE
        res = self.app.post("/api/secrets/TEST_CRUD_API", 
                            json={"password": "api_test_password"},
                            headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.data)["success"])

        # 2. READ (Verify created)
        res = self.app.get("/api/secrets", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("TEST_CRUD_API", data)
        self.assertEqual(data["TEST_CRUD_API"]["password"], "api_test_password")

        # 3. SOFT DELETE
        res = self.app.delete("/api/secrets/TEST_CRUD_API", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.data)["success"])

        # 4. READ (Verify soft deleted - should still be in data but with deleted_at)
        res = self.app.get("/api/secrets", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("TEST_CRUD_API", data)
        self.assertIn("deleted_at", data["TEST_CRUD_API"])

        # 5. RESTORE
        res = self.app.post("/api/secrets/TEST_CRUD_API/restore", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.data)["success"])
        
        # 6. READ (Verify restored)
        res = self.app.get("/api/secrets", headers=self.headers)
        data = json.loads(res.data)
        self.assertIn("TEST_CRUD_API", data)
        self.assertNotIn("deleted_at", data["TEST_CRUD_API"])
        
        # 7. PERMANENT DELETE
        res = self.app.delete("/api/secrets/TEST_CRUD_API/permanent", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.data)["success"])
        
        # 8. READ (Verify permanent deletion)
        res = self.app.get("/api/secrets", headers=self.headers)
        data = json.loads(res.data)
        self.assertNotIn("TEST_CRUD_API", data)

    def test_api_unauthorized(self):
        # Missing auth header
        res = self.app.get("/api/secrets")
        self.assertEqual(res.status_code, 401)
        
        # Bad auth header
        res = self.app.get("/api/secrets", headers={"Authorization": "Bearer bad_pin"})
        self.assertEqual(res.status_code, 401)

    def test_api_change_pin_non_admin(self):
        # Login as user (1111 is pin)
        res = self.app.post("/api/change-pin", 
                            json={"new_pin": "2222"},
                            headers={"Authorization": "Bearer 1111"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Admin role required", json.loads(res.data)["error"])
        
    def test_api_change_pin_admin(self):
        # Login as admin (master)
        res = self.app.post("/api/change-pin", 
                            json={"new_pin": "2222"},
                            headers={"Authorization": "Bearer master"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.data)["success"])

    def test_api_status(self):
        res = self.app.get("/api/status")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(json.loads(res.data)["initialized"])

    def test_api_init_already_initialized(self):
        res = self.app.post("/api/init", json={"pin": "1234", "master": "admin"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Already initialized", json.loads(res.data)["error"])

    def test_api_init_missing_data(self):
        # We need to test the condition where data is missing, we can temporarily bypass the exists check
        import vault
        with unittest.mock.patch('os.path.exists', return_value=False):
            res = self.app.post("/api/init", json={"pin": "12"})
            self.assertEqual(res.status_code, 400)
            self.assertIn("Wymagany PIN", json.loads(res.data)["error"])

            res2 = self.app.post("/api/init", json={"pin": "123", "master": "admin"})
            self.assertEqual(res2.status_code, 400)
            self.assertIn("PIN musi mieć", json.loads(res2.data)["error"])

    def test_api_auth(self):
        # Valid user
        res = self.app.post("/api/auth", json={"password": "1111"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data)["role"], "user")
        
        # Valid admin
        res = self.app.post("/api/auth", json={"password": "master"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data)["role"], "admin")
        
        # Invalid
        res = self.app.post("/api/auth", json={"password": "bad"})
        self.assertEqual(res.status_code, 401)

    def test_api_change_pin_missing_new_pin(self):
        res = self.app.post("/api/change-pin", 
                            json={},
                            headers={"Authorization": "Bearer master"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("New PIN is required", json.loads(res.data)["error"])

if __name__ == "__main__":
    unittest.main()
