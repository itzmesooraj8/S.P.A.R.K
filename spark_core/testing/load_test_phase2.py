import time
import tracemalloc
import sys
import os
import json
import asyncio

# Add spark_core to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.registry import project_registry
from intelligence.cross_analyzer import cross_analyzer

def generate_mock_project(pid: str, num_files=1000, num_funcs=10000):
    ctx = project_registry.load_project(pid, f"/mock/{pid}")
    
    # Generate large dummy graph
    nodes = []
    edges = []
    
    for i in range(num_files):
        nodes.append({"id": f"file_{i}", "type": "file"})
    for i in range(num_funcs):
        nodes.append({"id": f"func_{i}", "type": "function"})
    for i in range(num_funcs):
        edges.append({"source": f"func_{i}", "target": f"file_{i % num_files}"})
        
    ctx.state.update("code_graph", {"nodes": nodes, "edges": edges})
    ctx.state.update("metrics", {
        "circular_dependencies": (len(pid) % 3) * 2, # varying deterministically
        "lint_errors": 50,
        "type_errors": 20
    })
    ctx.state.update("sandbox_state", {
        "is_running": True,
        "last_cmd": f"npm run test --project {pid}",
        "last_exit_code": 0
    })

async def run_tests():
    print("🚀 Starting Phase 2 Load Validation\n")
    
    # 1. Setup 10 large projects
    print("📦 Bootstrapping 10 large mock projects (1000 files, 10k funcs each)...")
    start_time = time.time()
    for i in range(10):
        generate_mock_project(f"load_test_proj_{i}")
    print(f"✅ Bootstrapping completed in {(time.time() - start_time):.2f}s\n")
    
    # 2. Snapshot Scalability & Memory Leak Test
    print("⏱️ Running Scalability & Retention Test (20 iterations)...")
    tracemalloc.start()
    
    latencies = []
    payload_sizes = []
    
    for i in range(20):
        t0 = time.time()
        res = cross_analyzer.analyze_all(project_registry)
        t1 = time.time()
        
        latencies.append((t1 - t0) * 1000)
        payload_sizes.append(len(json.dumps(res)))
        
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    avg_latency = sum(latencies) / len(latencies)
    avg_payload_kb = (sum(payload_sizes) / len(payload_sizes)) / 1024
    
    print(f"✅ Scalability Results:")
    print(f"   - Avg Analyzer Latency: {avg_latency:.2f}ms (Target: < 300ms)")
    print(f"   - Avg JSON Payload Size: {avg_payload_kb:.2f}KB (Target: < 200KB)")
    print(f"   - Memory Delta: {current_mem / 1024 / 1024:.2f}MB (Peak: {peak_mem / 1024 / 1024:.2f}MB)")
    print()
    
    # 3. Determinism Test
    print("🔍 Running Determinism Test (20 iterations)...")
    health_scores = set()
    for i in range(20):
        res = cross_analyzer.analyze_all(project_registry)
        health_scores.add(res["system_health_score"])
        
    print(f"✅ Determinism Results: {len(health_scores)} unique health scores.")
    if len(health_scores) == 1:
        print(f"   - Score remained rock solid at: {list(health_scores)[0]}/100")
    else:
        print(f"   - ⚠️ DRIFT DETECTED: {health_scores}")
    print()
    
    # 4. Rapid Focus Switching Test
    print("🔄 Running Rapid Focus Switching Test (50 context switches)...")
    switch_times = []
    for i in range(50):
        t0 = time.time()
        pid = f"load_test_proj_{i % 10}"
        project_registry.switch_focus(pid)
        switch_times.append((time.time() - t0) * 1000)
        
    avg_switch = sum(switch_times) / len(switch_times)
    print(f"✅ Rapid Switching complete.")
    print(f"   - Avg Switch Latency: {avg_switch:.2f}ms")
    print(f"   - Active Focus: {project_registry.current_focus}")

if __name__ == "__main__":
    asyncio.run(run_tests())
