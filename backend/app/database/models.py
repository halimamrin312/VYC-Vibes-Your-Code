"""
backend/app/database/models.py
Defines the database models for storing M&A audit session states.
"""

import datetime
from peewee import Model, CharField, TextField, DateTimeField
from backend.app.database.connection import db

class BaseModel(Model):
    class Meta:
        database = db

class AuditSession(BaseModel):
    session_id = CharField(primary_key=True, max_length=255)
    target_company = CharField(max_length=255)
    industry_sector = CharField(max_length=50)
    hitl_status = CharField(max_length=20, default="IDLE")
    pending_hitl_question = TextField(null=True)
    accumulated_red_flags = TextField(default="[]")  # JSON serialized
    history = TextField(default="[]")  # JSON serialized
    agent_reports = TextField(default="{}")  # JSON serialized
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    """Initializes the database and creates tables if they do not exist."""
    db.connect(reuse_if_open=True)
    db.create_tables([AuditSession])
    db.close()
