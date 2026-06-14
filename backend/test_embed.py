import os
import asyncio
from langchain_google_genai import GoogleGenerativeAIEmbeddings

async def main():
    api_key = os.getenv("GOOGLE_API_KEY", "")
    
    models_to_test = [
        "models/gemini-embedding-001",
    ]
    
    for m in models_to_test:
        try:
            print(f"Testing {m}...")
            embedder = GoogleGenerativeAIEmbeddings(model=m, google_api_key=api_key)
            res = await embedder.aembed_query("Hello world")
            print(f"SUCCESS: {m} returned vector of size {len(res)}")
        except Exception as e:
            print(f"FAILED: {m} error: {str(e)}")

asyncio.run(main())
