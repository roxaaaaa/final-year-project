"""CLI: create all ORM tables once (async engine). Run when setting up a new database."""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

async def create_tables():
    """Connect with DATABASE_URL and call Base.metadata.create_all."""
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Tables created successfully!")

    except Exception as e:
        print(f"Error creating tables: {e}")
        raise

    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())