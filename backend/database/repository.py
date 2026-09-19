import uuid
import datetime
import json
from .mongodb import init_mongodb, get_db as get_mongo_db
from .sqlite import init_sqlite, get_db as get_sqlite_db

backend = None # 'mongodb' or 'sqlite'

async def init_db():
    global backend
    print("Initializing Database...")
    mongo_success = await init_mongodb()
    if mongo_success:
        backend = 'mongodb'
        print("Database backend: MongoDB")
    else:
        init_sqlite()
        backend = 'sqlite'
        print("MongoDB unavailable.\nDatabase backend: SQLite fallback.")

def get_iso_time():
    return datetime.datetime.utcnow().isoformat() + "Z"

def fix_id(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def fix_ids(docs):
    return [fix_id(d) for d in docs]

# --- USERS ---
async def create_user(name: str, email: str, password_hash: str, role: str = 'investigator'):
    user = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "created_at": get_iso_time(),
        "updated_at": get_iso_time()
    }
    
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.users.insert_one(user)
    else:
        conn = get_sqlite_db()
        conn.execute('''
            INSERT INTO users (id, name, email, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user['id'], user['name'], user['email'], user['password_hash'], user['role'], user['created_at'], user['updated_at']))
        conn.commit()
        conn.close()
    
    return user

async def get_user_by_email(email: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        return fix_id(await db.users.find_one({"email": email}))
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

async def get_user_by_id(user_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        return fix_id(await db.users.find_one({"id": user_id}))
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

# --- CASES ---
async def create_case(case_data: dict, analysis_data: dict):
    case_id_val = f"SC-{datetime.datetime.now().year}-{str(uuid.uuid4().hex)[:4].upper()}"
    case_record = {
        "id": str(uuid.uuid4()),
        "case_id": case_id_val,
        "user_id": case_data['user_id'],
        "title": case_data['title'],
        "description": case_data.get('description', ''),
        "document_type": case_data.get('document_type', 'Unknown'),
        "status": case_data.get('status', 'Active'),
        "risk_score": case_data.get('risk_score', 0),
        "classification": case_data.get('classification', 'Unknown'),
        "created_at": get_iso_time(),
        "updated_at": get_iso_time(),
    }
    
    analysis_record = {
        "id": str(uuid.uuid4()),
        "case_id": case_record['id'],
        "user_id": case_data['user_id'],
        "document_type": case_record['document_type'],
        "risk_score": case_record['risk_score'],
        "classification": case_record['classification'],
        "analysis_json": json.dumps(analysis_data) if backend == 'sqlite' else analysis_data,
        "created_at": get_iso_time()
    }
    case_record['analysis_id'] = analysis_record['id']

    if backend == 'mongodb':
        db = get_mongo_db()
        await db.cases.insert_one(case_record)
        await db.analyses.insert_one(analysis_record)
        fix_id(case_record)
        fix_id(analysis_record)
    else:
        conn = get_sqlite_db()
        conn.execute('''
            INSERT INTO cases (id, case_id, user_id, title, description, document_type, status, risk_score, classification, analysis_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (case_record['id'], case_record['case_id'], case_record['user_id'], case_record['title'], case_record['description'], case_record['document_type'], case_record['status'], case_record['risk_score'], case_record['classification'], case_record['analysis_id'], case_record['created_at'], case_record['updated_at']))
        
        conn.execute('''
            INSERT INTO analyses (id, case_id, user_id, document_type, risk_score, classification, analysis_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (analysis_record['id'], analysis_record['case_id'], analysis_record['user_id'], analysis_record['document_type'], analysis_record['risk_score'], analysis_record['classification'], analysis_record['analysis_json'], analysis_record['created_at']))
        conn.commit()
        conn.close()
        
    return case_record

async def list_cases(user_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        cases = await db.cases.find({"user_id": user_id}).sort("created_at", -1).to_list(1000)
        return fix_ids(cases)
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM cases WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

async def get_case(user_id: str, case_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        case = await db.cases.find_one({"user_id": user_id, "id": case_id})
        if not case: return None
        analysis = await db.analyses.find_one({"id": case.get("analysis_id")})
        case["analysis"] = fix_id(analysis)
        case["notes"] = await get_case_notes(user_id, case['id'])
        return fix_id(case)
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM cases WHERE user_id = ? AND id = ?', (user_id, case_id))
        case_row = cursor.fetchone()
        if not case_row:
            conn.close()
            return None
            
        case = dict(case_row)
        a_cursor = conn.execute('SELECT * FROM analyses WHERE id = ?', (case['analysis_id'],))
        a_row = a_cursor.fetchone()
        if a_row:
            analysis = dict(a_row)
            analysis['analysis_json'] = json.loads(analysis['analysis_json'])
            case['analysis'] = analysis
            
        case['notes'] = await get_case_notes(user_id, case['id'])
        conn.close()
        return case

async def get_case_notes(user_id: str, case_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        notes = await db.notes.find({"case_id": case_id}).sort("created_at", 1).to_list(100)
        for n in notes:
            n["text"] = n.get("content", "")
        return fix_ids(notes)
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('''
            SELECT notes.*, users.name as investigator_name 
            FROM notes 
            JOIN users ON notes.user_id = users.id 
            WHERE case_id = ? 
            ORDER BY notes.created_at ASC
        ''', (case_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r["id"], "case_id": r["case_id"], "user_id": r["user_id"], "text": r["content"], "created_at": r["created_at"], "investigator_name": r["investigator_name"]} for r in rows]

async def create_case_note(user_id: str, case_id: str, text: str, investigator_name: str):
    note = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "user_id": user_id,
        "content": text,
        "investigator_name": investigator_name,
        "created_at": get_iso_time(),
        "updated_at": get_iso_time()
    }
    
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.notes.insert_one(note)
        # map for frontend
        note["text"] = note["content"]
        return fix_id(note)
    else:
        conn = get_sqlite_db()
        conn.execute('''
            INSERT INTO notes (id, case_id, user_id, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (note['id'], note['case_id'], note['user_id'], note['content'], note['created_at'], note['updated_at']))
        conn.commit()
        conn.close()
        note["text"] = note["content"]
        return note

# --- REPORTS ---
async def create_report(user_id: str, case_id: str, file_path: str):
    report_id = f"RPT-2026-{str(uuid.uuid4().hex)[:4].upper()}"
    report_record = {
        "id": str(uuid.uuid4()),
        "report_id": report_id,
        "case_id": case_id,
        "user_id": user_id,
        "file_path": file_path,
        "created_at": get_iso_time()
    }
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.reports.insert_one(report_record)
    else:
        conn = get_sqlite_db()
        conn.execute('''
            INSERT INTO reports (id, report_id, case_id, user_id, file_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (report_record['id'], report_record['report_id'], report_record['case_id'], report_record['user_id'], report_record['file_path'], report_record['created_at']))
        conn.commit()
        conn.close()
    return report_record

async def list_reports(user_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        reports = await db.reports.find({"user_id": user_id}).sort("created_at", -1).to_list(1000)
        return fix_ids(reports)
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

async def get_report(user_id: str, report_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        return fix_id(await db.reports.find_one({"user_id": user_id, "id": report_id}))
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM reports WHERE user_id = ? AND id = ?', (user_id, report_id))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

# --- ANALYTICS ---
async def get_analytics(user_id: str):
    cases = await list_cases(user_id)
    total = len(cases)
    if total == 0:
        return {"total_investigations": 0}
        
    avg_risk = sum([c.get('risk_score', 0) for c in cases]) / total
    
    classes = {"Likely Authentic": 0, "Review Required": 0, "High Suspicion": 0}
    docs = {}
    
    for c in cases:
        cls = c.get('classification', 'Unknown')
        if cls in classes: classes[cls] += 1
        
        dtype = c.get('document_type', 'Unknown')
        docs[dtype] = docs.get(dtype, 0) + 1
        
    return {
        "total_investigations": total,
        "average_risk": round(avg_risk, 1),
        "classification": {
            "likely_authentic": classes["Likely Authentic"],
            "review_required": classes["Review Required"],
            "high_suspicion": classes["High Suspicion"]
        },
        "document_types": docs
    }
