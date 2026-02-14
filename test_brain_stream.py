import asyncio
from spark.modules.brain import think_stream

async def main():
    question = input("Ask S.P.A.R.K. anything to test its streaming brain: ")
    print("\n--- S.P.A.R.K. Streams ---")
    async for chunk in think_stream(question):
        print(chunk, end='', flush=True)
    print("\n-------------------------")

if __name__ == '__main__':
    asyncio.run(main())
