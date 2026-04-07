"""
Quick startup verification script - checks if SPARK servers are running
"""
import time
import sys

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "--quiet"])
    import httpx

def check_server(url, name, max_attempts=30):
    """Check if a server is responding"""
    print(f"\nChecking {name}...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                print(f"✓ {name} is running at {url}")
                return True
        except Exception:
            pass
        
        if attempt < max_attempts:
            print(f"  Attempt {attempt}/{max_attempts} - waiting...", end='\r')
            time.sleep(2)
    
    print(f"✗ {name} is not responding at {url}")
    return False

def main():
    print("\n" + "="*60)
    print("  S.P.A.R.K Server Status Check")
    print("="*60)
    
    backend_ok = check_server("http://localhost:8000/api/health", "Backend Server")
    frontend_ok = check_server("http://localhost:5173", "Frontend Server")
    
    print("\n" + "="*60)
    print("  Status Summary")
    print("="*60)
    
    if backend_ok and frontend_ok:
        print("\n✓ All servers are running!")
        print("\n  Backend:  http://localhost:8000")
        print("  Frontend: http://localhost:5173")
        print("\n  → Open http://localhost:5173 in your browser")
        return 0
    else:
        print("\n✗ Some servers are not running:")
        if not backend_ok:
            print("  - Backend (run: python run_server.py)")
        if not frontend_ok:
            print("  - Frontend (run: npm run dev)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
