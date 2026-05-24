import unittest
import os
from pathlib import Path

from sandbox.autonomy.swarm import (
    verify_safe_path,
    CodeAgent,
    FileAgent,
    ResearchAgent,
    SANDBOX_DIR
)

class SwarmSandboxTests(unittest.TestCase):

    def setUp(self):
        self.code_agent = CodeAgent()
        self.file_agent = FileAgent()
        # Ensure sandbox exists
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    def test_verify_safe_path_allowed(self):
        # Path inside sandbox should succeed
        allowed = Path("sandbox/temp_build/test_script.py")
        resolved = verify_safe_path(allowed)
        self.assertEqual(resolved, allowed.resolve())

    def test_verify_safe_path_blocked_escape(self):
        # Escape path should raise PermissionError
        escaped = Path("sandbox/temp_build/../../security/signature_verifier.py")
        with self.assertRaises(PermissionError):
            verify_safe_path(escaped)

    def test_verify_safe_path_blocked_absolute(self):
        # Absolute system path outside sandbox should raise PermissionError
        abs_path = Path("C:/Windows/System32")
        with self.assertRaises(PermissionError):
            verify_safe_path(abs_path)

    def test_code_agent_write_and_read_safe(self):
        filename = "test_write.py"
        code = "print('hello from sandbox')"
        
        # Write
        res_write = self.code_agent.write_code(filename, code)
        self.assertIn("Successfully wrote", res_write)
        
        # Read
        res_read = self.code_agent.read_code(filename)
        self.assertEqual(res_read, code)
        
        # Clean up
        self.file_agent.delete_file(filename)

    def test_code_agent_write_blocked_outside(self):
        filename = "../../escaped.py"
        code = "print('escaping')"
        with self.assertRaises(PermissionError):
            self.code_agent.write_code(filename, code)

    def test_file_agent_delete_blocked_outside(self):
        filename = "../../escaped.py"
        with self.assertRaises(PermissionError):
            self.file_agent.delete_file(filename)

if __name__ == "__main__":
    unittest.main()
