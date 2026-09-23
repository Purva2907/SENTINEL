import sqlite3
import json
import os

DB_PATH = os.environ.get("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "data", "sentinel.db"))

def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'investigator',
            department TEXT DEFAULT 'Forensic Screening Unit',
            badge_number TEXT,
            avatar TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    # Safe column additions if existing database doesn't have them yet
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'Forensic Screening Unit'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN badge_number TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
    except Exception:
        pass
    
    # Cases Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            case_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            document_type TEXT,
            status TEXT DEFAULT 'Active',
            risk_score INTEGER,
            classification TEXT,
            analysis_id TEXT,
            evidence_id TEXT,
            sha256_hash TEXT,
            file_path TEXT,
            file_size INTEGER,
            mime_type TEXT,
            fingerprint_hash TEXT,
            fingerprint_vector TEXT,
            timeline_json TEXT,
            custody_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Safe migrations for existing databases
    for col, col_type in [
        ("evidence_id", "TEXT"),
        ("sha256_hash", "TEXT"),
        ("file_path", "TEXT"),
        ("file_size", "INTEGER"),
        ("mime_type", "TEXT"),
        ("fingerprint_hash", "TEXT"),
        ("fingerprint_vector", "TEXT"),
        ("timeline_json", "TEXT"),
        ("custody_json", "TEXT")
    ]:
        try:
            cursor.execute(f"ALTER TABLE cases ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    
    # Analyses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            document_type TEXT,
            risk_score INTEGER,
            classification TEXT,
            analysis_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            report_id TEXT UNIQUE NOT NULL,
            case_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Notes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Note: DB functions logic will be wrapped in repository.py 
