from sqlalchemy import create_engine, text
from contextlib import contextmanager

DB_URL = "postgresql://postgres.wqqalipwyntzygedmpdb:recensireifimmi@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DB_URL, pool_pre_ping=True)
    return _engine

@contextmanager
def get_conn():
    with get_engine().begin() as conn:
        yield conn

def init_db():
    pass  # Tabelle già create su Supabase

def backup_db():
    return None  # Backup gestito da Supabase
