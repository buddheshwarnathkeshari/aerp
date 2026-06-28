import os
import asyncio
from backend.utils.llm_factory import get_embedder

async def main():
    try:
        print("Testing embedder from llm_factory...")
        embedder = get_embedder()
        res = await embedder.aembed_query("Hello world")
        print(f"SUCCESS: Embedder returned vector of size {len(res)}")
    except Exception as e:
        print(f"FAILED: error: {str(e)}")

asyncio.run(main())
