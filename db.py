import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

DB_PATH = Path("data") / "micarboglino.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        # Tabella principale
        conn.execute("""
        CREATE TABLE IF NOT EXISTS films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            film_raw TEXT,
            titolo TEXT,
            regista TEXT,
            paese TEXT,
            anno INTEGER,
            note TEXT,

            regia_annika REAL,
            regia_francesco REAL,
            fotografia_annika REAL,
            fotografia_francesco REAL,
            sceneggiatura_annika REAL,
            sceneggiatura_francesco REAL,
            recitazione_annika REAL,
            recitazione_francesco REAL,
            globale_annika REAL,
            globale_francesco REAL,

            media_annika REAL,
            media_francesco REAL,
            voto_finale REAL,
            indice_conflitto REAL
        );
        """)

        # Cronologia: snapshot PRIMA di ogni modifica
        conn.execute("""
        CREATE TABLE IF NOT EXISTS film_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            film_id INTEGER NOT NULL,
            changed_at TEXT NOT NULL,
            changed_by TEXT,

            titolo TEXT,
            anno INTEGER,
            note TEXT,

            regia_annika REAL,
            regia_francesco REAL,
            fotografia_annika REAL,
            fotografia_francesco REAL,
            sceneggiatura_annika REAL,
            sceneggiatura_francesco REAL,
            recitazione_annika REAL,
            recitazione_francesco REAL,
            globale_annika REAL,
            globale_francesco REAL,

            media_annika REAL,
            media_francesco REAL,
            voto_finale REAL,
            indice_conflitto REAL,

            FOREIGN KEY(film_id) REFERENCES films(id)
        );
        """)


def backup_db():
    """
    Crea una copia del DB in data/backup/.
    Ritorna il path della copia se esiste il DB, altrimenti None.
    """
    if DB_PATH.exists():
        backup_dir = DB_PATH.parent / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dst = backup_dir / f"micarboglino_{ts}.db"
        shutil.copy2(DB_PATH, dst)
        return str(dst)
    return None
