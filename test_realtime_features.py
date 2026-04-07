"""
S.P.A.R.K Real-Time Features Verification Script

This script tests all real-time communication features:
- Backend server startup
- WebSocket connections (all namespaces)
- Voice engine initialization
- Memory system connectivity
- Frontend-backend integration points

Usage:
    python test_realtime_features.py
"""

import asyncio
import sys
import os
import time
import json
from typing import Dict, Any, List
import websockets
from urllib.parse import urljoin

# Add spark_core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "spark_core"))

class RealTimeTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.results = []
        self.httpx = None
        
    async def setup(self):
        """Setup HTTP client"""
        import httpx
        self.httpx = httpx.AsyncClient(timeout=30.0)
        
    async def teardown(self):
        """Cleanup"""
        if self.httpx:
            await self.httpx.aclose()
            
    def log_result(self, test_name: str, status: str, message: str = "", details: Any = None):
        """Log test result"""
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{emoji} [{test_name}] {status}: {message}")
        self.results.append({
            "test": test_name,
            "status": status,
            "message": message,
            "details": details
        })
        
    # ===== PHASE 1: Backend Service Verification =====
    
    async def test_backend_health(self):
        """Test backend health endpoint"""
        try:
            response = await self.httpx.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                self.log_result("Backend Health", "PASS", f"Status: {data.get('status')}", data)
                return True
            else:
                self.log_result("Backend Health", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Backend Health", "FAIL", str(e))
            return False
            
    async def test_backend_version(self):
        """Test backend version endpoint"""
        try:
            response = await self.httpx.get(f"{self.base_url}/api/version")
            if response.status_code == 200:
                data = response.json()
                self.log_result("Backend Version", "PASS", f"Version: {data.get('version')}", data)
                return True
            else:
                self.log_result("Backend Version", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Backend Version", "FAIL", str(e))
            return False
            
    async def test_memory_stats(self):
        """Test memory system connectivity"""
        try:
            response = await self.httpx.get(f"{self.base_url}/api/memory/stats")
            if response.status_code == 200:
                data = response.json()
                self.log_result("Memory Stats", "PASS", 
                              f"Entities: {data.get('entities', 0)}, Relations: {data.get('relations', 0)}", 
                              data)
                return True
            else:
                self.log_result("Memory Stats", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Memory Stats", "FAIL", str(e))
            return False
            
    async def test_voice_engine_status(self):
        """Test voice engine availability"""
        try:
            response = await self.httpx.get(f"{self.base_url}/api/voice/engine")
            if response.status_code == 200:
                data = response.json()
                self.log_result("Voice Engine", "PASS", f"Engine: {data.get('engine')}", data)
                return True
            else:
                self.log_result("Voice Engine", "WARN", f"HTTP {response.status_code} (may not be initialized)")
                return False
        except Exception as e:
            self.log_result("Voice Engine", "WARN", f"Not available: {e}")
            return False
            
    # ===== PHASE 2: WebSocket Testing =====
    
    async def test_websocket_connection(self, namespace: str, test_name: str):
        """Test WebSocket connection to a specific namespace"""
        ws_url = f"{self.ws_url}{namespace}"
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as websocket:
                # Wait for any initial message
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message) if message else {}
                    self.log_result(test_name, "PASS", f"Connected and received: {type(data).__name__}", data)
                    return True
                except asyncio.TimeoutError:
                    # Some WebSockets don't send initial message
                    self.log_result(test_name, "PASS", "Connected (no initial message)")
                    return True
        except Exception as e:
            self.log_result(test_name, "FAIL", str(e))
            return False
            
    async def test_all_websockets(self):
        """Test all WebSocket namespaces"""
        namespaces = [
            ("/ws/ai", "WebSocket /ws/ai"),
            ("/ws/system", "WebSocket /ws/system"),
            ("/ws/combat", "WebSocket /ws/combat"),
            ("/ws/globe", "WebSocket /ws/globe"),
        ]
        
        results = []
        for namespace, test_name in namespaces:
            result = await self.test_websocket_connection(namespace, test_name)
            results.append(result)
            await asyncio.sleep(0.5)  # Small delay between connections
            
        return all(results)
        
    # ===== PHASE 3: Voice System Testing =====
    
    async def test_tts_synthesis(self):
        """Test TTS synthesis endpoint"""
        try:
            response = await self.httpx.post(
                f"{self.base_url}/api/voice/speak",
                json={"text": "Testing SPARK voice synthesis"}
            )
            if response.status_code == 200:
                self.log_result("TTS Synthesis", "PASS", "TTS endpoint working")
                return True
            else:
                self.log_result("TTS Synthesis", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("TTS Synthesis", "WARN", f"Not available: {e}")
            return False
            
    async def test_available_voices(self):
        """Test available voices endpoint"""
        try:
            response = await self.httpx.get(f"{self.base_url}/api/voice/voices")
            if response.status_code == 200:
                data = response.json()
                voice_count = len(data.get('voices', []))
                self.log_result("Available Voices", "PASS", f"{voice_count} voices available", data)
                return True
            else:
                self.log_result("Available Voices", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Available Voices", "WARN", f"Not available: {e}")
            return False
            
    # ===== PHASE 4: Task & Briefing Real-Time Sync =====
    
    async def test_task_crud(self):
        """Test task CRUD operations"""
        try:
            # Create task
            create_response = await self.httpx.post(
                f"{self.base_url}/api/personal/tasks",
                json={
                    "title": "Test Real-Time Sync",
                    "description": "Automated test task",
                    "status": "PENDING",
                    "priority": 1
                }
            )
            
            if create_response.status_code != 200:
                self.log_result("Task CRUD", "FAIL", f"Create failed: HTTP {create_response.status_code}")
                return False
                
            task_data = create_response.json()
            task_id = task_data.get('id')
            
            # List tasks
            list_response = await self.httpx.get(f"{self.base_url}/api/personal/tasks")
            if list_response.status_code != 200:
                self.log_result("Task CRUD", "FAIL", f"List failed: HTTP {list_response.status_code}")
                return False
                
            # Delete task
            delete_response = await self.httpx.delete(f"{self.base_url}/api/personal/tasks/{task_id}")
            if delete_response.status_code != 200:
                self.log_result("Task CRUD", "FAIL", f"Delete failed: HTTP {delete_response.status_code}")
                return False
                
            self.log_result("Task CRUD", "PASS", "Create, List, Delete operations working")
            return True
            
        except Exception as e:
            self.log_result("Task CRUD", "FAIL", str(e))
            return False
            
    async def test_briefing_crud(self):
        """Test briefing CRUD operations"""
        try:
            # Create briefing
            create_response = await self.httpx.post(
                f"{self.base_url}/api/personal/briefings",
                json={
                    "title": "Test Briefing",
                    "content_text": "Automated test briefing content",
                    "mood": "NEUTRAL"
                }
            )
            
            if create_response.status_code != 200:
                self.log_result("Briefing CRUD", "FAIL", f"Create failed: HTTP {create_response.status_code}")
                return False
                
            briefing_data = create_response.json()
            briefing_id = briefing_data.get('id')
            
            # Get latest briefing
            latest_response = await self.httpx.get(f"{self.base_url}/api/personal/briefings/latest")
            if latest_response.status_code != 200:
                self.log_result("Briefing CRUD", "FAIL", f"Get latest failed: HTTP {latest_response.status_code}")
                return False
                
            # Delete briefing
            delete_response = await self.httpx.delete(f"{self.base_url}/api/personal/briefings/{briefing_id}")
            if delete_response.status_code != 200:
                self.log_result("Briefing CRUD", "FAIL", f"Delete failed: HTTP {delete_response.status_code}")
                return False
                
            self.log_result("Briefing CRUD", "PASS", "Create, Get Latest, Delete operations working")
            return True
            
        except Exception as e:
            self.log_result("Briefing CRUD", "FAIL", str(e))
            return False
            
    # ===== PHASE 5: Performance Metrics =====
    
    async def test_websocket_latency(self):
        """Measure WebSocket round-trip latency"""
        ws_url = f"{self.ws_url}/ws/ai"
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as websocket:
                # Measure ping-pong latency
                start_time = time.time()
                pong = await websocket.ping()
                await pong
                latency_ms = (time.time() - start_time) * 1000
                
                status = "PASS" if latency_ms < 100 else "WARN"
                self.log_result("WebSocket Latency", status, f"{latency_ms:.2f}ms")
                return latency_ms < 200  # Allow up to 200ms
        except Exception as e:
            self.log_result("WebSocket Latency", "FAIL", str(e))
            return False
            
    # ===== Main Test Runner =====
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("  S.P.A.R.K Real-Time Features Test Suite")
        print("="*60 + "\n")
        
        await self.setup()
        
        # Phase 1: Backend Services
        print("\n📋 Phase 1: Backend Service Verification")
        print("-" * 60)
        await self.test_backend_health()
        await self.test_backend_version()
        await self.test_memory_stats()
        await self.test_voice_engine_status()
        
        # Phase 2: WebSocket Testing
        print("\n📋 Phase 2: WebSocket Connections")
        print("-" * 60)
        await self.test_all_websockets()
        
        # Phase 3: Voice System
        print("\n📋 Phase 3: Voice System")
        print("-" * 60)
        await self.test_available_voices()
        await self.test_tts_synthesis()
        
        # Phase 4: Real-Time Data Sync
        print("\n📋 Phase 4: Real-Time Data Synchronization")
        print("-" * 60)
        await self.test_task_crud()
        await self.test_briefing_crud()
        
        # Phase 5: Performance
        print("\n📋 Phase 5: Performance Metrics")
        print("-" * 60)
        await self.test_websocket_latency()
        
        await self.teardown()
        
        # Summary
        print("\n" + "="*60)
        print("  Test Summary")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        total = len(self.results)
        
        print(f"\n✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print(f"⚠️  Warnings: {warned}/{total}")
        
        if failed == 0:
            print("\n🎉 All critical tests passed! Real-time features are operational.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Review output above for details.")
            
        print("\n" + "="*60 + "\n")
        
        return failed == 0


async def main():
    """Main entry point"""
    # Check if backend is running
    print("🔍 Checking if backend is running on http://localhost:8000...")
    
    suite = RealTimeTestSuite()
    success = await suite.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
