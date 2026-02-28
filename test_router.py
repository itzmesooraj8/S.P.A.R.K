import asyncio
from spark_core.tools.router import ToolRouter

async def main():
    router = ToolRouter()
    
    # Test get_time
    print("Testing get_time...")
    res = await router.execute_raw({"tool": "get_time", "arguments": {}})
    print(res)
    
    # Test ping
    print("Testing ping...")
    res = await router.execute_raw({"tool": "ping", "arguments": {}})
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
