import asyncio
from dotenv import load_dotenv
load_dotenv()

from database import engine
from sqlalchemy import text

async def test_column():
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'generations_number'"))
            rows = result.fetchall()
            print('Column exists:', bool(rows))
            if rows:
                print('Column name:', rows[0][0])
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_column())