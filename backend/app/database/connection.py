"""
backend/app/database/connection.py
Establishes the SQLite database connection using Peewee ORM.
"""

import os
from peewee import SqliteDatabase
from swarm.config import settings

# Ensure the sessions folder exists inside data_room
db_dir = os.path.join(settings.data_room_dir, "sessions")
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "metadata.db")

db = SqliteDatabase(db_path)

def get_db():
    """Returns the database instance."""
    return db
