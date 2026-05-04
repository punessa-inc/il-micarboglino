from sqlalchemy import create_engine, text
from contextlib import contextmanager
import streamlit as st

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = st.secrets["DB_URL"]
        _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine

@contextmanager
def get_conn():
    with get_engine().begin() as conn:
        yield conn

def init_db():
    pass  # Tabelle già create su Supabase

def backup_db():
    return None  # Backup gestito da Supabase
