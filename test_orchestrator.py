import asyncio
from spark.orchestration.orchestrator import orchestrate_conversation

async def main():
    user_input = input("Ask S.P.A.R.K. anything (with tool use!): ")
    print("\n--- S.P.A.R.K. Streams ---")
    async for chunk in orchestrate_conversation(user_input):
        print(chunk, end='', flush=True)
    print("\n-------------------------")

if __name__ == '__main__':
    asyncio.run(main())
