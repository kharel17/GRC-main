#!/usr/bin/env python
"""
Database initialization script for GRC Platform
Handles migrations and seeding of initial data
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def main():
    try:
        print("🔄 Initializing GRC Platform Database...")
        
        # Import after path is set
        from app.database import engine, SessionLocal
        from app.models.base import Base
        from backend.seed import init_db, seed_data
        
        print("✓ Imports successful")
        
        # Create tables
        print("📊 Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Tables created successfully")
        
        # Seed initial data
        print("🌱 Seeding initial data...")
        await seed_data()
        print("✓ Database seeded successfully")
        
        print("\n✅ Database initialization complete!")
        print("   Backend is ready to connect to frontend")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
