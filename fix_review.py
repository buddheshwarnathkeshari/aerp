import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect("postgresql://aerp:aerp_password@localhost:5432/aerp_db")
    # Change status back to queued or tell user to resubmit
    await conn.execute("UPDATE pull_requests SET status = 'queued', error = NULL WHERE id = 'a58dcf88-bccd-4e12-8754-a655d03fd084'")
    await conn.close()

asyncio.run(run())
