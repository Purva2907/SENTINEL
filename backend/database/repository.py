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
async def create_user(name: str, email: str, password_hash: str, role: str = 'investigator', department: str = 'Forensic Screening Unit', badge_number: str = None, avatar: str = None):
    if not badge_number:
        badge_number = f"SEN-{str(uuid.uuid4().hex)[:4].upper()}"
    user = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "department": department or 'Forensic Screening Unit',
        "badge_number": badge_number,
        "avatar": avatar or '',
        "created_at": get_iso_time(),
        "updated_at": get_iso_time()
    }
    
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.users.insert_one(user)
    else:
        conn = get_sqlite_db()
        conn.execute('''
            INSERT INTO users (id, name, email, password_hash, role, department, badge_number, avatar, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user['id'], user['name'], user['email'], user['password_hash'], user['role'], user['department'], user['badge_number'], user['avatar'], user['created_at'], user['updated_at']))
        conn.commit()
        conn.close()
    
    return user

async def get_user_by_email(email: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        user = fix_id(await db.users.find_one({"email": email}))
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        user = dict(row) if row else None
        
    if user:
        if not user.get("department"):
            user["department"] = "Forensic Screening Unit"
        if not user.get("badge_number"):
            user["badge_number"] = f"SEN-{user['id'][:4].upper()}"
        if "avatar" not in user or user.get("avatar") is None:
            user["avatar"] = ""
    return user

async def get_user_by_id(user_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        user = fix_id(await db.users.find_one({"id": user_id}))
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        user = dict(row) if row else None
        
    if user:
        if not user.get("department"):
            user["department"] = "Forensic Screening Unit"
        if not user.get("badge_number"):
            user["badge_number"] = f"SEN-{user['id'][:4].upper()}"
        if "avatar" not in user or user.get("avatar") is None:
            user["avatar"] = ""
    return user

async def update_user_profile(user_id: str, name: str, department: str = None, badge_number: str = None, avatar: str = None):
    now = get_iso_time()
    if backend == 'mongodb':
        db = get_mongo_db()
        update_fields = {"name": name, "updated_at": now}
        if department is not None:
            update_fields["department"] = department
        if badge_number is not None:
            update_fields["badge_number"] = badge_number
        if avatar is not None:
            update_fields["avatar"] = avatar
        await db.users.update_one({"id": user_id}, {"$set": update_fields})
        return await get_user_by_id(user_id)
    else:
        conn = get_sqlite_db()
        conn.execute('''
            UPDATE users
            SET name = ?, department = COALESCE(?, department), badge_number = COALESCE(?, badge_number), avatar = COALESCE(?, avatar), updated_at = ?
            WHERE id = ?
        ''', (name, department, badge_number, avatar, now, user_id))
        conn.commit()
        conn.close()
        return await get_user_by_id(user_id)

async def update_user_password(user_id: str, password_hash: str):
    now = get_iso_time()
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.users.update_one({"id": user_id}, {"$set": {"password_hash": password_hash, "updated_at": now}})
    else:
        conn = get_sqlite_db()
        conn.execute('UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?', (password_hash, now, user_id))
        conn.commit()
        conn.close()
    return True

# --- CASES ---
async def create_case(case_data: dict, analysis_data: dict):
    case_id_val = f"SC-{datetime.datetime.now().year}-{str(uuid.uuid4().hex)[:4].upper()}"
    try:
        risk_score_val = int(case_data.get('risk_score', 0))
    except (ValueError, TypeError):
        risk_score_val = 0

    case_record = {
        "id": str(uuid.uuid4()),
        "case_id": case_id_val,
        "user_id": case_data['user_id'],
        "title": case_data['title'],
        "description": case_data.get('description', ''),
        "document_type": case_data.get('document_type', 'Unknown'),
        "status": case_data.get('status', 'Active'),
        "risk_score": risk_score_val,
        "classification": case_data.get('classification', 'Unknown'),
        "created_at": get_iso_time(),
        "updated_at": get_iso_time(),
    }
    
    analysis_json_str = json.dumps(analysis_data) if not isinstance(analysis_data, str) else analysis_data
    analysis_record = {
        "id": str(uuid.uuid4()),
        "case_id": case_record['id'],
        "user_id": case_data['user_id'],
        "document_type": case_record['document_type'],
        "risk_score": case_record['risk_score'],
        "classification": case_record['classification'],
        "analysis_json": analysis_data if backend == 'mongodb' else analysis_json_str,
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
        ''', (analysis_record['id'], analysis_record['case_id'], analysis_record['user_id'], analysis_record['document_type'], analysis_record['risk_score'], analysis_record['classification'], analysis_json_str, analysis_record['created_at']))
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
        case = await db.cases.find_one({"user_id": user_id, "$or": [{"id": case_id}, {"case_id": case_id}]})
        if not case: return None
        analysis = await db.analyses.find_one({"id": case.get("analysis_id")})
        if analysis:
            fix_id(analysis)
            parsed = analysis.get("analysis_json")
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except Exception:
                    pass
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if k not in analysis:
                        analysis[k] = v
            case["analysis"] = analysis
        case["notes"] = await get_case_notes(user_id, case['id'])
        return fix_id(case)
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM cases WHERE user_id = ? AND (id = ? OR case_id = ?)', (user_id, case_id, case_id))
        case_row = cursor.fetchone()
        if not case_row:
            conn.close()
            return None
            
        case = dict(case_row)
        a_cursor = conn.execute('SELECT * FROM analyses WHERE id = ?', (case['analysis_id'],))
        a_row = a_cursor.fetchone()
        if a_row:
            analysis = dict(a_row)
            try:
                parsed = json.loads(analysis['analysis_json'])
            except Exception:
                parsed = analysis['analysis_json']
            analysis['analysis_json'] = parsed
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if k not in analysis:
                        analysis[k] = v
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
async def create_report(user_id: str, case_id: str, file_path: str, report_id: str = None):
    if not report_id:
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
        fix_id(report_record)
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
        reports = fix_ids(reports)
        for r in reports:
            case = await db.cases.find_one({"user_id": user_id, "$or": [{"id": r.get("case_id")}, {"case_id": r.get("case_id")}]})
            if case:
                r["case_title"] = case.get("title", "Untitled Case")
                r["readable_case_id"] = case.get("case_id", r.get("case_id"))
                r["risk_score"] = case.get("risk_score", 0)
                r["classification"] = case.get("classification", "Unknown")
                r["document_type"] = case.get("document_type", "Unknown")
            else:
                r["case_title"] = "Forensic Case"
                r["readable_case_id"] = r.get("case_id")
        return reports
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('''
            SELECT r.*, c.title as case_title, c.case_id as readable_case_id, c.risk_score, c.classification, c.document_type
            FROM reports r
            LEFT JOIN cases c ON (r.case_id = c.id OR r.case_id = c.case_id)
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            if not d.get("readable_case_id"):
                d["readable_case_id"] = d.get("case_id")
            if not d.get("case_title"):
                d["case_title"] = "Forensic Case"
            res.append(d)
        return res

async def get_report(user_id: str, report_id: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        return fix_id(await db.reports.find_one({"user_id": user_id, "$or": [{"id": report_id}, {"report_id": report_id}]}))
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM reports WHERE user_id = ? AND (id = ? OR report_id = ?)', (user_id, report_id, report_id))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

# --- ANALYTICS ---
async def get_analytics(user_id: str):
    cases = await list_cases(user_id)
    total = len(cases)
    if total == 0:
        return {
            "total_investigations": 0,
            "average_risk": 0.0,
            "classification": {
                "likely_authentic": 0,
                "review_required": 0,
                "high_suspicion": 0
            },
            "document_types": {}
        }
        
    avg_risk = sum([int(c.get('risk_score') or 0) for c in cases]) / total
    
    classes = {"Likely Authentic": 0, "Review Required": 0, "High Suspicion": 0}
    docs = {}
    
    for c in cases:
        cls = c.get('classification', 'Unknown')
        if cls in classes:
            classes[cls] += 1
        elif cls.title() in classes:
            classes[cls.title()] += 1
        else:
            classes["Review Required"] += 1
        
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
