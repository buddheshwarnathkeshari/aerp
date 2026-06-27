import asyncio
from backend.config.settings import get_settings
settings = get_settings()
from langgraph.checkpoint.redis import RedisSaver

def main():
    try:
        with RedisSaver.from_conn_string(settings.redis_url) as checkpointer:
            print("Successfully entered context manager")
    except Exception as e:
        import traceback
        traceback.print_exc()

main()
