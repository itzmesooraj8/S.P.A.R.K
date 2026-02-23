import asyncio
from llm.hybrid_engine import HybridLLM

async def main():
    llm = HybridLLM(model='deepseek-r1:latest')
    print("Available?", await llm.is_local_available())
    async for t in llm.generate('Answer clearly.', 'hi'):
        print(t, end='', flush=True)

asyncio.run(main())
