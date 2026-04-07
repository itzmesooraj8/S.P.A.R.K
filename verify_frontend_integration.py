"""
Frontend Integration Verification

Checks that all frontend hooks and components are properly configured
to connect with backend real-time services.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class FrontendVerifier:
    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.issues: List[Dict] = []
        self.checks_passed = 0
        self.checks_failed = 0
        
    def log_pass(self, check_name: str, message: str = ""):
        """Log a passing check"""
        print(f"✅ {check_name}: {message}")
        self.checks_passed += 1
        
    def log_fail(self, check_name: str, message: str, file_path: str = ""):
        """Log a failing check"""
        print(f"❌ {check_name}: {message}")
        if file_path:
            print(f"   File: {file_path}")
        self.checks_failed += 1
        self.issues.append({
            "check": check_name,
            "message": message,
            "file": file_path
        })
        
    def log_warn(self, check_name: str, message: str):
        """Log a warning"""
        print(f"⚠️  {check_name}: {message}")
        
    def check_file_exists(self, rel_path: str, description: str) -> bool:
        """Check if a file exists"""
        full_path = self.src_dir / rel_path
        if full_path.exists():
            self.log_pass(description, f"Found at {rel_path}")
            return True
        else:
            self.log_fail(description, f"File not found: {rel_path}")
            return False
            
    def check_file_contains(self, rel_path: str, pattern: str, description: str) -> bool:
        """Check if a file contains a pattern"""
        full_path = self.src_dir / rel_path
        if not full_path.exists():
            self.log_fail(description, f"File not found: {rel_path}")
            return False
            
        try:
            content = full_path.read_text(encoding='utf-8')
            if re.search(pattern, content, re.MULTILINE):
                self.log_pass(description)
                return True
            else:
                self.log_fail(description, f"Pattern '{pattern}' not found", str(rel_path))
                return False
        except Exception as e:
            self.log_fail(description, f"Error reading file: {e}", str(rel_path))
            return False
            
    def verify_websocket_hooks(self):
        """Verify WebSocket hooks are properly implemented"""
        print("\n📋 Verifying WebSocket Hooks")
        print("-" * 60)
        
        # Check useVoiceEngine hook
        self.check_file_exists(
            "hooks/useVoiceEngine.ts",
            "Voice Engine Hook"
        )
        self.check_file_contains(
            "hooks/useVoiceEngine.ts",
            r"ws://.*?/ws/ai",
            "Voice Engine WebSocket connection"
        )
        
        # Check useAIEvents hook
        self.check_file_exists(
            "hooks/useAIEvents.ts",
            "AI Events Hook"
        )
        self.check_file_contains(
            "hooks/useAIEvents.ts",
            r"/ws/ai",
            "AI Events WebSocket connection"
        )
        
        # Check useWakeWordListener hook
        self.check_file_exists(
            "hooks/useWakeWordListener.ts",
            "Wake Word Listener Hook"
        )
        
        # Check usePersonalAISocket hook
        self.check_file_exists(
            "hooks/usePersonalAISocket.ts",
            "Personal AI Socket Hook"
        )
        self.check_file_contains(
            "hooks/usePersonalAISocket.ts",
            r"/ws/personal/chat",
            "Personal AI WebSocket connection"
        )
        
    def verify_state_stores(self):
        """Verify Zustand stores are properly set up"""
        print("\n📋 Verifying State Stores")
        print("-" * 60)
        
        # Task store
        self.check_file_exists(
            "store/useTaskStore.ts",
            "Task Store"
        )
        self.check_file_contains(
            "store/useTaskStore.ts",
            r"localStorage|persist",
            "Task Store persistence"
        )
        
        # Briefing store
        self.check_file_exists(
            "store/useBriefingStore.ts",
            "Briefing Store"
        )
        
        # Connection store
        if self.check_file_exists("store/useConnectionStore.ts", "Connection Store"):
            self.check_file_contains(
                "store/useConnectionStore.ts",
                r"isConnected|connectionStatus",
                "Connection Store state"
            )
            
    def verify_api_clients(self):
        """Verify API client libraries"""
        print("\n📋 Verifying API Clients")
        print("-" * 60)
        
        # Task API client
        self.check_file_exists(
            "lib/tasks.ts",
            "Task API Client"
        )
        self.check_file_contains(
            "lib/tasks.ts",
            r"/api/personal/tasks",
            "Task API endpoints"
        )
        
    def verify_hud_components(self):
        """Verify HUD components"""
        print("\n📋 Verifying HUD Components")
        print("-" * 60)
        
        # Main HUD layout
        self.check_file_exists(
            "components/hud/HudLayout.tsx",
            "HUD Layout"
        )
        
        # Command bar
        self.check_file_exists(
            "components/hud/CommandBar.tsx",
            "Command Bar"
        )
        
        # Task panel
        self.check_file_exists(
            "components/hud/modules/TaskPanel.tsx",
            "Task Panel"
        )
        
        # Bottom dock
        self.check_file_exists(
            "components/hud/BottomDock.tsx",
            "Bottom Dock"
        )
        
    def verify_vite_config(self):
        """Verify Vite configuration for backend proxy"""
        print("\n📋 Verifying Vite Configuration")
        print("-" * 60)
        
        vite_config = Path("vite.config.ts")
        if vite_config.exists():
            content = vite_config.read_text(encoding='utf-8')
            if re.search(r"proxy.*?/api", content, re.DOTALL):
                self.log_pass("Vite Proxy Config", "Backend proxy configured")
            else:
                self.log_warn("Vite Proxy Config", "Proxy configuration not found (may use direct connection)")
        else:
            self.log_fail("Vite Config", "vite.config.ts not found")
            
    def verify_env_config(self):
        """Verify environment configuration"""
        print("\n📋 Verifying Environment Configuration")
        print("-" * 60)
        
        env_file = Path(".env")
        if env_file.exists():
            content = env_file.read_text(encoding='utf-8')
            
            # Check backend URL
            if "VITE_API_BASE" in content or "VITE_BACKEND_PORT" in content:
                self.log_pass("Frontend Env Vars", "Backend connection configured")
            else:
                self.log_warn("Frontend Env Vars", "Backend URL not explicitly configured")
                
            # Check WebSocket verbose mode
            if "VITE_VERBOSE_WS" in content:
                self.log_pass("WebSocket Debug Mode", "Configured")
            else:
                self.log_warn("WebSocket Debug Mode", "Not configured (optional)")
        else:
            self.log_warn("Environment File", ".env file not found (using defaults)")
            
    def run_all_checks(self):
        """Run all verification checks"""
        print("\n" + "="*60)
        print("  S.P.A.R.K Frontend Integration Verification")
        print("="*60)
        
        self.verify_websocket_hooks()
        self.verify_state_stores()
        self.verify_api_clients()
        self.verify_hud_components()
        self.verify_vite_config()
        self.verify_env_config()
        
        # Summary
        print("\n" + "="*60)
        print("  Verification Summary")
        print("="*60)
        print(f"\n✅ Checks Passed: {self.checks_passed}")
        print(f"❌ Checks Failed: {self.checks_failed}")
        
        if self.checks_failed == 0:
            print("\n🎉 All frontend integration checks passed!")
            print("Frontend is properly configured for real-time features.")
        else:
            print(f"\n⚠️  {self.checks_failed} check(s) failed.")
            print("\nIssues found:")
            for issue in self.issues:
                print(f"  - {issue['check']}: {issue['message']}")
                if issue['file']:
                    print(f"    File: {issue['file']}")
                    
        print("\n" + "="*60 + "\n")
        
        return self.checks_failed == 0


def main():
    """Main entry point"""
    import sys
    
    # Change to project root
    os.chdir(Path(__file__).parent)
    
    verifier = FrontendVerifier()
    success = verifier.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
