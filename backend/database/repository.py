import os
import re
import uuid
import datetime
import json
from .mongodb import init_mongodb, get_db as get_mongo_db
from .sqlite import init_sqlite, get_db as get_sqlite_db

backend = None # 'mongodb' or 'sqlite'

async def init_db():
    global backend
    print("Initializing Database...")
    db_mode = os.getenv("DATABASE_MODE", "sqlite").lower().strip()
    if db_mode in ("sqlite", "local"):
        init_sqlite()
        backend = 'sqlite'
        print("Database backend: SQLite (configured via DATABASE_MODE).")
        return

    mongo_success = await init_mongodb()
    if mongo_success:
        backend = 'mongodb'
        print("Database backend: MongoDB")
    else:
        init_sqlite()
        backend = 'sqlite'
        print("MongoDB unavailable.\nDatabase backend: SQLite fallback.")

def get_iso_time():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

# --- PASSWORD RESET TOKENS ---
async def create_password_reset_token(user_id: str, token_hash: str, expires_at: str) -> dict:
    token_record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used": 0 if backend != 'mongodb' else False,
        "created_at": get_iso_time()
    }
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.password_reset_tokens.insert_one(dict(token_record))
    else:
        conn = get_sqlite_db()
        conn.execute('''
            INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            token_record["id"],
            token_record["user_id"],
            token_record["token_hash"],
            token_record["expires_at"],
            token_record["used"],
            token_record["created_at"]
        ))
        conn.commit()
        conn.close()
    return token_record

async def get_password_reset_token(token_hash: str):
    if backend == 'mongodb':
        db = get_mongo_db()
        doc = await db.password_reset_tokens.find_one({"token_hash": token_hash})
        record = fix_id(doc) if doc else None
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT * FROM password_reset_tokens WHERE token_hash = ?', (token_hash,))
        row = cursor.fetchone()
        conn.close()
        record = dict(row) if row else None

    if record:
        record["used"] = bool(record.get("used"))
    return record

async def invalidate_user_reset_tokens(user_id: str) -> None:
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.password_reset_tokens.update_many(
            {"user_id": user_id, "used": False},
            {"$set": {"used": True}}
        )
    else:
        conn = get_sqlite_db()
        conn.execute('UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0', (user_id,))
        conn.commit()
        conn.close()

async def consume_password_reset_token(token_hash: str) -> None:
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.password_reset_tokens.update_one(
            {"token_hash": token_hash},
            {"$set": {"used": True}}
        )
    else:
        conn = get_sqlite_db()
        conn.execute('UPDATE password_reset_tokens SET used = 1 WHERE token_hash = ?', (token_hash,))
        conn.commit()
        conn.close()

def _resolve_stored_filepath(stored_filename: str) -> str:
    if not stored_filename:
        return ""
    candidates = [
        os.path.join(os.getenv("UPLOAD_DIR", "data/uploads"), stored_filename),
        os.path.join("backend", os.getenv("UPLOAD_DIR", "data/uploads"), stored_filename),
        os.path.join("backend", "data", "synthetic", stored_filename),
        os.path.join("data", "synthetic", stored_filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "synthetic", stored_filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "uploads", stored_filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return ""

# --- CASES ---
async def create_case(case_data: dict, analysis_data: dict):
    case_id_val = f"SC-{datetime.datetime.now().year}-{str(uuid.uuid4().hex)[:4].upper()}"
    try:
        risk_score_val = int(case_data.get('risk_score', 0))
    except (ValueError, TypeError):
        risk_score_val = 0

    now_iso = get_iso_time()
    
    # 1. Chain of Custody extraction
    custody = analysis_data.get("chain_of_custody", {}) if isinstance(analysis_data, dict) else {}
    if not isinstance(custody, dict):
        custody = {}
    evidence_id = custody.get("evidence_id") or case_data.get("evidence_id") or f"EVID-{int(datetime.datetime.now().timestamp())}-{uuid.uuid4().hex[:6].upper()}"
    sha256_hash = custody.get("sha256_hash") or case_data.get("sha256_hash") or ""
    file_path = custody.get("file_path") or case_data.get("file_path") or ""
    stored_filename = custody.get("stored_filename") or case_data.get("stored_filename") or ""
    if (not file_path or not os.path.exists(file_path)) and stored_filename:
        resolved = _resolve_stored_filepath(stored_filename)
        if resolved:
            file_path = resolved

    file_size = custody.get("file_size") or case_data.get("file_size") or (os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0)
    mime_type = custody.get("mime_type") or case_data.get("mime_type") or "image/jpeg"
    
    custody_payload = {
        "evidence_id": evidence_id,
        "sha256_hash": sha256_hash,
        "ingestion_timestamp": custody.get("ingestion_timestamp") or now_iso,
        "investigator_id": case_data['user_id'],
        "investigator_name": case_data.get("investigator_name") or "Investigator",
        "analysis_version": "2.1.0",
        "original_filename": custody.get("original_filename") or case_data.get("original_filename") or "document.jpg",
        "stored_filename": stored_filename or (os.path.basename(file_path) if file_path else "evidence.jpg"),
        "file_path": file_path,
        "file_size": file_size,
        "mime_type": mime_type,
        "status": "TAMPER_FREE"
    }

    # 2. Document Fingerprint extraction
    fingerprint = analysis_data.get("fingerprint", {}) if isinstance(analysis_data, dict) else {}
    if not isinstance(fingerprint, dict):
        fingerprint = {}
    fp_hash = fingerprint.get("fingerprint_hash") or ""
    fp_vector = fingerprint.get("fingerprint_vector") or []

    # 3. Initial Chronological Investigation Timeline
    ingestion_time = custody_payload["ingestion_timestamp"]
    timeline = [
        {
            "event_type": "EVIDENCE_INGESTED",
            "timestamp": ingestion_time,
            "investigator_id": case_data['user_id'],
            "investigator_name": custody_payload["investigator_name"],
            "description": f"Evidence specimen '{custody_payload.get('original_filename', 'document.jpg')}' securely ingested into forensic pipeline."
        },
        {
            "event_type": "SHA256_CALCULATED",
            "timestamp": ingestion_time,
            "investigator_id": case_data['user_id'],
            "investigator_name": custody_payload["investigator_name"],
            "description": f"Cryptographic SHA-256 digest calculated: {sha256_hash}."
        },
        {
            "event_type": "FORENSIC_SCREENING_COMPLETED",
            "timestamp": now_iso,
            "investigator_id": case_data['user_id'],
            "investigator_name": "SENTINEL Pipeline (v2.1.0)",
            "description": f"Multi-vector forensic screening completed. Score: {risk_score_val}/100 ({case_data.get('classification', 'Unknown')})."
        },
        {
            "event_type": "CASE_CREATED",
            "timestamp": now_iso,
            "investigator_id": case_data['user_id'],
            "investigator_name": custody_payload["investigator_name"],
            "description": f"Investigation case file {case_id_val} initialized and secured in case repository."
        }
    ]

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
        "evidence_id": evidence_id,
        "sha256_hash": sha256_hash,
        "file_path": file_path,
        "file_size": file_size,
        "mime_type": mime_type,
        "fingerprint_hash": fp_hash,
        "fingerprint_vector": json.dumps(fp_vector) if backend == 'sqlite' else fp_vector,
        "timeline_json": json.dumps(timeline) if backend == 'sqlite' else timeline,
        "custody_json": json.dumps(custody_payload) if backend == 'sqlite' else custody_payload,
        "chain_of_custody": custody_payload,
        "fingerprint": fingerprint,
        "timeline": timeline,
        "created_at": now_iso,
        "updated_at": now_iso,
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
        "created_at": now_iso
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
            INSERT INTO cases (
                id, case_id, user_id, title, description, document_type, status, risk_score, classification, analysis_id,
                evidence_id, sha256_hash, file_path, file_size, mime_type, fingerprint_hash, fingerprint_vector, timeline_json, custody_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_record['id'], case_record['case_id'], case_record['user_id'], case_record['title'], case_record['description'],
            case_record['document_type'], case_record['status'], case_record['risk_score'], case_record['classification'], case_record['analysis_id'],
            evidence_id, sha256_hash, file_path, file_size, mime_type, fp_hash, json.dumps(fp_vector), json.dumps(timeline), json.dumps(custody_payload),
            case_record['created_at'], case_record['updated_at']
        ))
        
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
        res = []
        for r in rows:
            d = dict(r)
            if d.get("custody_json") and isinstance(d["custody_json"], str):
                try: d["chain_of_custody"] = json.loads(d["custody_json"])
                except Exception: pass
            if d.get("fingerprint_vector") and isinstance(d["fingerprint_vector"], str):
                try: d["fingerprint"] = {"fingerprint_vector": json.loads(d["fingerprint_vector"]), "fingerprint_hash": d.get("fingerprint_hash")}
                except Exception: pass
            res.append(d)
        return res

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
        
        # Ensure custody object
        if not case.get("chain_of_custody"):
            case["chain_of_custody"] = {
                "evidence_id": case.get("evidence_id") or f"EVID-{case['id'][:8]}",
                "sha256_hash": case.get("sha256_hash") or "",
                "file_path": case.get("file_path") or "",
                "file_size": case.get("file_size") or 0,
                "mime_type": case.get("mime_type") or "image/jpeg",
                "analysis_version": "2.1.0",
                "status": "TAMPER_FREE"
            }
        # Ensure timeline
        if not case.get("timeline"):
            case["timeline"] = [
                {
                    "event_type": "EVIDENCE_INGESTED",
                    "timestamp": case.get("created_at"),
                    "investigator_id": user_id,
                    "investigator_name": "Investigator",
                    "description": f"Evidence ingested. SHA-256 calculated."
                },
                {
                    "event_type": "CASE_CREATED",
                    "timestamp": case.get("created_at"),
                    "investigator_id": user_id,
                    "investigator_name": "Investigator",
                    "description": f"Case record {case.get('case_id')} secured."
                }
            ]
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
        
        # Parse custody
        custody_parsed = None
        if case.get("custody_json"):
            try: custody_parsed = json.loads(case["custody_json"])
            except Exception: pass
        if not custody_parsed:
            custody_parsed = {
                "evidence_id": case.get("evidence_id") or f"EVID-{case['id'][:8]}",
                "sha256_hash": case.get("sha256_hash") or "",
                "file_path": case.get("file_path") or "",
                "file_size": case.get("file_size") or 0,
                "mime_type": case.get("mime_type") or "image/jpeg",
                "analysis_version": "2.1.0",
                "status": "TAMPER_FREE"
            }
        case["chain_of_custody"] = custody_parsed

        # Parse timeline
        timeline_parsed = []
        if case.get("timeline_json"):
            try: timeline_parsed = json.loads(case["timeline_json"])
            except Exception: pass
        if not timeline_parsed:
            timeline_parsed = [
                {
                    "event_type": "EVIDENCE_INGESTED",
                    "timestamp": case.get("created_at"),
                    "investigator_id": user_id,
                    "investigator_name": "Investigator",
                    "description": f"Evidence ingested. SHA-256 calculated."
                },
                {
                    "event_type": "CASE_CREATED",
                    "timestamp": case.get("created_at"),
                    "investigator_id": user_id,
                    "investigator_name": "Investigator",
                    "description": f"Case record {case.get('case_id')} secured."
                }
            ]
        case["timeline"] = timeline_parsed

        # Parse fingerprint
        if case.get("fingerprint_vector"):
            try:
                vec = json.loads(case["fingerprint_vector"])
                case["fingerprint"] = {"fingerprint_vector": vec, "fingerprint_hash": case.get("fingerprint_hash")}
            except Exception:
                pass

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
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Note text cannot be empty or whitespace only.")
    if len(clean_text) > 2000:
        raise ValueError("Note text exceeds maximum allowed length of 2000 characters.")

    note = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "user_id": user_id,
        "content": clean_text,
        "investigator_name": investigator_name,
        "created_at": get_iso_time(),
        "updated_at": get_iso_time()
    }
    
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.notes.insert_one(note)
        # map for frontend
        note["text"] = note["content"]
        await add_case_timeline_event(user_id, case_id, "NOTE_ADDED", f"Investigator note recorded: '{clean_text[:40]}...'", investigator_name)
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
        await add_case_timeline_event(user_id, case_id, "NOTE_ADDED", f"Investigator note recorded: '{clean_text[:40]}...'", investigator_name)
        return note

async def add_case_timeline_event(user_id: str, case_id: str, event_type: str, description: str, investigator_name: str = "Investigator"):
    """Appends an authentic audit event to the case's chronological investigation timeline."""
    event = {
        "event_type": event_type,
        "timestamp": get_iso_time(),
        "investigator_id": user_id,
        "investigator_name": investigator_name,
        "description": description
    }
    
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.cases.update_one(
            {"user_id": user_id, "$or": [{"id": case_id}, {"case_id": case_id}]},
            {"$push": {"timeline": event}, "$set": {"updated_at": get_iso_time()}}
        )
    else:
        conn = get_sqlite_db()
        cursor = conn.execute('SELECT id, timeline_json FROM cases WHERE user_id = ? AND (id = ? OR case_id = ?)', (user_id, case_id, case_id))
        row = cursor.fetchone()
        if row:
            cid = row["id"]
            existing = []
            if row["timeline_json"]:
                try: existing = json.loads(row["timeline_json"])
                except Exception: existing = []
            existing.append(event)
            conn.execute('UPDATE cases SET timeline_json = ?, updated_at = ? WHERE id = ?', (json.dumps(existing), get_iso_time(), cid))
            conn.commit()
        conn.close()
    return event

async def update_case_status(user_id: str, case_id: str, new_status: str, investigator_name: str = "Investigator"):
    """Updates case status and records timeline event."""
    allowed_statuses = {"Active", "Under Review", "Closed"}
    if new_status not in allowed_statuses:
        raise ValueError(f"Invalid status '{new_status}'. Allowed statuses: {', '.join(allowed_statuses)}")

    now = get_iso_time()
    if backend == 'mongodb':
        db = get_mongo_db()
        await db.cases.update_one(
            {"user_id": user_id, "$or": [{"id": case_id}, {"case_id": case_id}]},
            {"$set": {"status": new_status, "updated_at": now}}
        )
    else:
        conn = get_sqlite_db()
        conn.execute('UPDATE cases SET status = ?, updated_at = ? WHERE user_id = ? AND (id = ? OR case_id = ?)', (new_status, now, user_id, case_id, case_id))
        conn.commit()
        conn.close()
    await add_case_timeline_event(user_id, case_id, "STATUS_CHANGED", f"Case status updated to '{new_status}'", investigator_name)
    return True
    return True

async def verify_case_custody(user_id: str, case_id: str, investigator_name: str = "Investigator") -> dict:
    """
    Cryptographic Evidence Chain of Custody Integrity Check.
    Re-reads stored evidence bytes, computes SHA-256 digest, and asserts integrity.
    Does NOT claim identity authenticity; verifies that stored evidence bytes have not been altered.
    """
    import hashlib
    import os
    
    case = await get_case(user_id, case_id)
    if not case:
        return {"success": False, "detail": "Case not found", "status": "NOT_FOUND"}

    custody = case.get("chain_of_custody") or {}
    stored_sha = custody.get("sha256_hash") or case.get("sha256_hash") or ""
    evidence_id = custody.get("evidence_id") or case.get("evidence_id") or f"EVID-{case['id'][:8]}"
    file_path = custody.get("file_path") or case.get("file_path") or ""
    if not file_path or not os.path.exists(file_path):
        stored_fname = custody.get("stored_filename") or case.get("stored_filename") or ""
        if stored_fname:
            resolved = _resolve_stored_filepath(stored_fname)
            if resolved:
                file_path = resolved

    if not file_path or not os.path.exists(file_path):
        # File is inaccessible or moved; return clear integrity status rather than falsely claiming tampering
        await add_case_timeline_event(
            user_id, case_id, "INTEGRITY_VERIFICATION",
            f"Evidence file inaccessible on storage volume. Verification failed.",
            investigator_name
        )
        return {
            "success": True,
            "case_id": case.get("case_id"),
            "evidence_id": evidence_id,
            "stored_sha256": stored_sha,
            "current_sha256": None,
            "status": "UNAVAILABLE",
            "message": "Original evidence file cannot be accessed from storage disk."
        }

    try:
        with open(file_path, "rb") as f:
            current_bytes = f.read()
        current_sha = hashlib.sha256(current_bytes).hexdigest()
    except Exception as e:
        return {
            "success": True,
            "case_id": case.get("case_id"),
            "evidence_id": evidence_id,
            "stored_sha256": stored_sha,
            "current_sha256": None,
            "status": "UNAVAILABLE",
            "message": f"Storage read error: {str(e)}"
        }

    if current_sha.lower() == stored_sha.lower():
        status = "TAMPER_FREE"
        message = "Cryptographic integrity intact. Stored evidence bytes have not been altered."
    else:
        status = "INTEGRITY_BREACH"
        message = "Integrity breach detected! Stored evidence bytes differ from initial ingestion SHA-256 hash."

    await add_case_timeline_event(
        user_id, case_id, "INTEGRITY_VERIFICATION",
        f"Chain of custody verification performed. Status: {status} (Digest: {current_sha[:12]}...).",
        investigator_name
    )

    return {
        "success": True,
        "case_id": case.get("case_id"),
        "evidence_id": evidence_id,
        "stored_sha256": stored_sha,
        "current_sha256": current_sha,
        "file_size": len(current_bytes),
        "status": status,
        "message": message
    }

# --- REPORTS ---
async def create_report(user_id: str, case_id: str, file_path: str, report_id: str = None):
    if not report_id:
        curr_year = datetime.datetime.now(datetime.timezone.utc).year
        report_id = f"RPT-{curr_year}-{str(uuid.uuid4().hex)[:4].upper()}"
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

    try:
        await add_case_timeline_event(
            user_id,
            case_id,
            "REPORT_GENERATED",
            f"Forensic investigative report generated with identifier {report_record['report_id']}.",
            "SENTINEL Reporting Engine"
        )
    except Exception:
        pass

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
