import multiprocessing
import os
import time
import uuid

def sub_agent_worker(task_id, task_type, payload, result_queue):
    """
    Dedicated worker function to be executed in a separate process.
    """
    print(f"[SWARM-AGENT-{task_id}] Starting {task_type} task...")
    
    # Simulate resource heavy work
    try:
        if task_type == "research":
            # Mock research logic
            time.sleep(2)
            result = f"Research complete for payload: {payload}"
        elif task_type == "code":
            # Mock coding logic
            time.sleep(3)
            result = f"Code generated for payload: {payload}"
        elif task_type == "test":
            # Mock testing logic
            time.sleep(1)
            result = f"Test results for payload: {payload}"
        else:
            result = f"Unknown task type: {task_type}"
            
        result_queue.put({"task_id": task_id, "status": "COMPLETED", "result": result})
    except Exception as e:
        result_queue.put({"task_id": task_id, "status": "FAILED", "error": str(e)})

class SwarmOrchestrator:
    def __init__(self, max_agents=3):
        self.max_agents = max_agents
        self.result_queue = multiprocessing.Queue()
        self.active_agents = {} # task_id: process

    def spawn_agent(self, task_type, payload):
        """
        Spawns a new sub-agent process if under the max_agents limit.
        """
        if len(self.active_agents) >= self.max_agents:
            print("[SWARM] Max agent limit reached. Waiting for a slot...")
            return None

        task_id = str(uuid.uuid4())[:8]
        process = multiprocessing.Process(
            target=sub_agent_worker,
            args=(task_id, task_type, payload, self.result_queue)
        )
        
        self.active_agents[task_id] = process
        process.start()
        print(f"[SWARM] Spawned Agent {task_id} for {task_type}")
        return task_id

    def collect_results(self):
        """
        Checks the result queue and cleans up finished processes.
        """
        results = []
        while not self.result_queue.empty():
            res = self.result_queue.get()
            task_id = res.get("task_id")
            if task_id in self.active_agents:
                self.active_agents[task_id].join()
                del self.active_agents[task_id]
                print(f"[SWARM] Agent {task_id} rejoined.")
            results.append(res)
        return results

    def shutdown(self):
        """
        Terminates all active agents.
        """
        for task_id, process in self.active_agents.items():
            if process.is_alive():
                process.terminate()
                print(f"[SWARM] Agent {task_id} terminated.")
        self.active_agents.clear()

# Global orchestrator
swarm_orchestrator = SwarmOrchestrator()

if __name__ == "__main__":
    # Internal Swarm Test
    orch = SwarmOrchestrator()
    id1 = orch.spawn_agent("research", "Quantum Computing")
    id2 = orch.spawn_agent("code", "Sort Algorithm")
    
    print("[SWARM] Waiting for agents to finish...")
    max_wait = 10
    start_time = time.time()
    
    while len(orch.active_agents) > 0 and (time.time() - start_time) < max_wait:
        results = orch.collect_results()
        for r in results:
            print(f"[SWARM] Task {r['task_id']} Result: {r['result'] if 'result' in r else r['error']}")
        time.sleep(1)
    
    orch.shutdown()
