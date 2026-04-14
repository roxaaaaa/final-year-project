import asyncio
from dotenv import load_dotenv
load_dotenv()

from database import engine
from sqlalchemy import text

async def check_alembic_version():
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text('SELECT * FROM alembic_version'))
            rows = result.fetchall()
            print("Alembic version table exists:")
            for row in rows:
                print(row)
        except Exception as e:
            print(f"Error checking alembic_version: {e}")

if __name__ == "__main__":
    asyncio.run(check_alembic_version())