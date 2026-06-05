import os
import unittest
from unittest.mock import patch, MagicMock
import vault

class TestSmartMyVault(unittest.TestCase):
    
    def setUp(self):
        vault.PIN_SALT_FILE = "test_pin_salt.cfg"
        vault.MASTER_SALT_FILE = "test_master_salt.cfg"
        vault.PIN_KEY_FILE = "test_pin_key.enc"
        vault.MASTER_KEY_FILE = "test_master_key.enc"
        vault.VAULT_DATA_FILE = "test_vault_data.enc"
        
        self.files_to_cleanup = [
            vault.PIN_SALT_FILE, vault.MASTER_SALT_FILE, 
            vault.PIN_KEY_FILE, vault.MASTER_KEY_FILE, vault.VAULT_DATA_FILE
        ]
        
        for f in self.files_to_cleanup:
            if os.path.exists(f): os.remove(f)

    def tearDown(self):
        for f in self.files_to_cleanup:
            if os.path.exists(f): os.remove(f)

    @patch('getpass.getpass')
    def test_init_success(self, mock_getpass):
        # pin, confirm_pin, master, confirm_master
        mock_getpass.side_effect = ["1111", "1111", "masterpass", "masterpass"]
        vault.init_vault()
        
        self.assertTrue(os.path.exists(vault.VAULT_DATA_FILE))
        self.assertTrue(os.path.exists(vault.PIN_KEY_FILE))
        self.assertTrue(os.path.exists(vault.MASTER_KEY_FILE))

    @patch('getpass.getpass')
    def test_init_fail_mismatch_pin(self, mock_getpass):
        mock_getpass.side_effect = ["1111", "2222"]
        with self.assertRaises(SystemExit):
            vault.init_vault()

    @patch('getpass.getpass')
    def test_add_and_list_secret(self, mock_getpass):
        # Init
        mock_getpass.side_effect = ["1111", "1111", "masterpass", "masterpass", "1111", "my_super_secret"]
        vault.init_vault()
        
        # Add (asks for PIN then secret)
        vault.add_secret("TEST_KEY")
        
        # Verify
        vk = vault.get_vault_key_from_pin("1111")
        data = vault.load_vault(vk)
        self.assertIn("TEST_KEY", data)
        self.assertEqual(data["TEST_KEY"]["password"], "my_super_secret")

    @patch('pyperclip.copy')
    @patch('getpass.getpass')
    def test_copy_secret(self, mock_getpass, mock_copy):
        # Init -> Add -> Copy
        mock_getpass.side_effect = ["1111", "1111", "master", "master", "1111", "secret_for_copy", "1111"]
        vault.init_vault()
        vault.add_secret("COPY_KEY")
        vault.copy_secret("COPY_KEY")
        
        mock_copy.assert_called_once_with("secret_for_copy")

    @patch('getpass.getpass')
    def test_delete_and_restore_secret(self, mock_getpass):
        mock_getpass.side_effect = ["1111", "1111", "master", "master", "1111", "secret_val", "1111", "1111"]
        vault.init_vault()
        vault.add_secret("DEL_KEY")
        vault.delete_secret("DEL_KEY")
        
        vk = vault.get_vault_key_from_pin("1111")
        data = vault.load_vault(vk)
        # Soft delete check
        self.assertIn("deleted_at", data["DEL_KEY"])
        
        # Odbuduj za pomocą restore_secret
        vault.restore_secret("DEL_KEY")
        data_restored = vault.load_vault(vk)
        self.assertNotIn("deleted_at", data_restored["DEL_KEY"])

    @patch('getpass.getpass')
    def test_forget_password_wrong_pin(self, mock_getpass):
        mock_getpass.side_effect = ["1111", "1111", "master", "master"]
        vault.init_vault()
        
        with self.assertRaises(ValueError):
            vault.get_vault_key_from_pin("9999", exit_on_fail=False)

    @patch('getpass.getpass')
    def test_master_password_decryption(self, mock_getpass):
        mock_getpass.side_effect = ["1111", "1111", "master_secure", "master_secure"]
        vault.init_vault()
        
        # Próba odzyskania klucza z prawidłowym master password
        vk_master = vault.get_vault_key_from_master("master_secure")
        vk_pin = vault.get_vault_key_from_pin("1111")
        self.assertEqual(vk_master, vk_pin) # Dowodzi że asymetria ról działa dla Key Encrypting Key!
        
        # Złe master password
        with self.assertRaises(ValueError):
            vault.get_vault_key_from_master("wrong_master", exit_on_fail=False)

    @patch('sys.exit')
    @patch('subprocess.run')
    @patch('getpass.getpass')
    def test_run_command_flattener(self, mock_getpass, mock_run, mock_exit):
        mock_getpass.side_effect = ["1111", "1111", "master", "master", "1111", "secret_for_run", "1111"]
        vault.init_vault()
        vault.add_secret("RUN_SECRET")
        
        mock_run.return_value = MagicMock(returncode=0)
        vault.run_wrapped_command(["echo", "hello"])
        
        call_args, call_kwargs = mock_run.call_args
        env_passed = call_kwargs.get('env')
        
        # Sprawdzanie flattenowania ENV
        self.assertIn("RUN_SECRET_PASSWORD", env_passed)
        self.assertEqual(env_passed["RUN_SECRET_PASSWORD"], "secret_for_run")
        self.assertEqual(env_passed["RUN_SECRET"], "secret_for_run") # Fallback string logic

    @patch('getpass.getpass')
    def test_update_pin(self, mock_getpass):
        mock_getpass.side_effect = ["1111", "1111", "master", "master"]
        vault.init_vault()
        
        # Change PIN from 1111 to 2222
        vk_old = vault.get_vault_key_from_pin("1111")
        vault.update_pin(vk_old, "2222")
        
        # Ensure old PIN fails
        with self.assertRaises(ValueError):
            vault.get_vault_key_from_pin("1111", exit_on_fail=False)
            
        # Ensure new PIN works and gets the same key
        vk_new = vault.get_vault_key_from_pin("2222", exit_on_fail=False)
        self.assertEqual(vk_old, vk_new)

    @patch('getpass.getpass')
    def test_3_day_auto_purge(self, mock_getpass):
        import datetime
        mock_getpass.side_effect = ["1111", "1111", "master", "master", "1111"]
        vault.init_vault()
        
        vk = vault.get_vault_key_from_pin("1111", exit_on_fail=False)
        
        # Inject old deleted items directly
        data = {
            "OLD_DEL": {"password": "x", "deleted_at": (datetime.datetime.now() - datetime.timedelta(days=4)).isoformat()},
            "NEW_DEL": {"password": "y", "deleted_at": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()},
            "ACTIVE": {"password": "z"}
        }
        vault.save_vault(vk, data)
        
        # get_secrets should purge OLD_DEL but keep NEW_DEL and ACTIVE
        # Since get_secrets with vk doesn't prompt for password
        purged_data = vault.get_secrets(vk)
        
        self.assertNotIn("OLD_DEL", purged_data)
        self.assertIn("NEW_DEL", purged_data)
        self.assertIn("ACTIVE", purged_data)

    def test_load_vault_bad_key(self):
        with open(vault.VAULT_DATA_FILE, "wb") as f:
            f.write(b"bad_data_that_is_not_encrypted")
        # Ensure bad key throws VaultDecryptionError instead of sys.exit
        import base64
        bad_vk = base64.urlsafe_b64encode(b"0" * 32)
        with self.assertRaises(vault.VaultDecryptionError):
            vault.load_vault(bad_vk)

if __name__ == '__main__':
    unittest.main()
