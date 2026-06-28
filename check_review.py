import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect("postgresql://aerp:aerp_password@localhost:5432/aerp_db")
    rows = await conn.fetch("SELECT id, status, error FROM pull_requests ORDER BY created_at DESC LIMIT 1")
    for row in rows:
        print(dict(row))
    await conn.close()

asyncio.run(run())
