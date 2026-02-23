import asyncio
from spark_core.sandbox.docker_env import DockerEnvironment

async def main():
    print("Testing Sandbox Initialization...")
    env = DockerEnvironment(image="spark_dev_env")
    started = await env.setup()
    if not started:
        print("FAILED to setup sandbox.")
        return

    print("Sandbox started. Testing Heavy Scans...")
    
    await env.write_file("test.py", "def my_func():\n  pass\n")

    
    # Run flake8
    res = await env.run_command("flake8 .")
    print(f"Flake8 exit code: {res.exit_code}")
    
    # Run mypy
    res = await env.run_command("mypy .")
    print(f"Mypy exit code: {res.exit_code}")

    # Run bandit
    res = await env.run_command("bandit -r . -f json")
    print(f"Bandit exit code: {res.exit_code}")
    
    # Run radon
    res = await env.run_command("radon cc . -s -a")
    print(f"Radon exit code: {res.exit_code}")
    
    # Teardown
    await env.teardown()
    print("Test Complete.")

asyncio.run(main())
