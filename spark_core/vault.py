import os
import json
from cryptography.fernet import Fernet

class SparkVault:
    def __init__(self, vault_file="spark_vault.enc", key_file="master.key"):
        self.vault_file = vault_file
        self.key_file = key_file
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)

    def _load_or_generate_key(self):
        """Loads the master key from disk or generates a new one if missing."""
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            print(f"[VAULT] Generated new master key at {self.key_file}")
            return key

    def _read_vault(self):
        """Reads and decrypts the vault file."""
        if not os.path.exists(self.vault_file):
            return {}
        
        try:
            with open(self.vault_file, "rb") as f:
                encrypted_data = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"[VAULT] Error reading vault: {e}")
            return {}

    def _write_vault(self, data):
        """Encrypts and writes the data to the vault file."""
        try:
            json_data = json.dumps(data).encode()
            encrypted_data = self.fernet.encrypt(json_data)
            
            with open(self.vault_file, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            print(f"[VAULT] Error writing vault: {e}")

    def set_secret(self, name, value):
        """Saves a secret to the encrypted vault."""
        data = self._read_vault()
        data[name] = value
        self._write_vault(data)
        print(f"[VAULT] Successfully stored secret: {name}")

    def get_secret(self, name):
        """Retrieves a secret from the encrypted vault."""
        data = self._read_vault()
        value = data.get(name)
        if value:
            # For security, we don't log the value itself
            # print(f"[VAULT] Retrieved secret: {name}")
            return value
        return None

# Global instance
spark_vault = SparkVault()

if __name__ == "__main__":
    # Banker Test
    test_vault = SparkVault("test_vault.enc", "test_master.key")
    test_vault.set_secret("test_api_key", "sk-1234567890abcdef")
    
    # Retrieve
    val = test_vault.get_secret("test_api_key")
    print(f"Banker Test Result: {'PASS' if val == 'sk-1234567890abcdef' else 'FAIL'}")
    
    # Verify file is encrypted (should not contain the plain text key)
    with open("test_vault.enc", "rb") as f:
        content = f.read()
        if b"sk-1234567890abcdef" in content:
            print("SECURITY ALERT: Vault is storing plain text!")
        else:
            print("Encryption Verified: Plain text not found in vault file.")
    
    # Clean up test files
    os.remove("test_vault.enc")
    os.remove("test_master.key")
