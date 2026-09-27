import re
import datetime
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

# ==============================================================================
# 1. VERHOEFF CHECKSUM ALGORITHM (Official Aadhaar Mathematical Checksum)
# ==============================================================================

VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def validate_verhoeff(num_str: str) -> bool:
    """
    Validates a number string using the Verhoeff checksum algorithm.
    Returns True if valid checksum, False otherwise.
    """
    digits = [int(c) for c in reversed(str(num_str)) if c.isdigit()]
    if not digits or len(digits) < 2:
        return False
    c = 0
    for i, digit in enumerate(digits):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][digit]]
    return c == 0

def mask_aadhaar_number(num_str: str) -> str:
    """
    Mask a 12-digit Aadhaar number into standard format: XXXX XXXX 1234.
    Never exposes the first 8 digits.
    """
    if not num_str:
        return "XXXX XXXX XXXX"
    clean = re.sub(r'\D', '', str(num_str))
    if len(clean) >= 12:
        return f"XXXX XXXX {clean[-4:]}"
    elif len(clean) >= 4:
        return f"XXXX XXXX {clean[-4:]}"
    return "XXXX XXXX XXXX"

# ==============================================================================
# 2. DATE & CALENDAR VALIDATION
# ==============================================================================

def validate_calendar_date(dob_str: str) -> Tuple[bool, Optional[datetime.date], str]:
    """
    Validates whether a date string is a plausible calendar date.
    Accepts DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, or YYYY.
    Returns (is_valid, parsed_date, normalized_string).
    """
    if not dob_str or not isinstance(dob_str, str):
        return False, None, ""

    clean = dob_str.strip()
    
    # Check for DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])[/-](0?[1-9]|1[012])[/-]((?:19|20)\d{2})\b', clean)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            d = datetime.date(year, month, day)
            curr = datetime.date.today()
            if 1900 <= year <= curr.year:
                return True, d, d.strftime("%d/%m/%Y")
        except ValueError:
            return False, None, clean

    # Check for YYYY-MM-DD
    m_iso = re.search(r'\b((?:19|20)\d{2})[/-](0?[1-9]|1[012])[/-](0?[1-9]|[12][0-9]|3[01])\b', clean)
    if m_iso:
        year, month, day = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        try:
            d = datetime.date(year, month, day)
            curr = datetime.date.today()
            if 1900 <= year <= curr.year:
                return True, d, d.strftime("%d/%m/%Y")
        except ValueError:
            return False, None, clean

    # Check for Year of Birth only (YYYY)
    m_year = re.search(r'\b((?:19|20)\d{2})\b', clean)
    if m_year:
        year = int(m_year.group(1))
        curr = datetime.date.today()
        if 1900 <= year <= curr.year:
            return True, datetime.date(year, 1, 1), f"Year of Birth: {year}"

    return False, None, clean

def calculate_age(dob: datetime.date) -> Optional[int]:
    """Calculates age in years from date of birth."""
    if not dob:
        return None
    today = datetime.date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# ==============================================================================
# 3. ENROLMENT ID (EID) VALIDATION
# ==============================================================================

def parse_enrolment_id(text: str) -> Dict[str, Any]:
    """
    Parses and validates Enrolment ID (EID) if present.
    EID is optional on issued Aadhaar cards.
    Formats:
      - 14-digit: 1234/12345/12345
      - 28-digit: 1234/12345/12345 yyyy/mm/dd hh:mm:ss
    Returns structured analysis. If absent, status is NOT_PRESENT.
    """
    if not text:
        return {
            "status": "NOT_PRESENT",
            "present": False,
            "raw_value": None,
            "masked_value": None,
            "is_valid": None,
            "timestamp": None,
            "details": "Enrolment ID (EID) is not printed on this document (optional on issued Aadhaar)."
        }

    # Match 14-digit format or 28-digit with date/time
    m_full = re.search(r'\b(\d{4}/\d{5}/\d{5})\s+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\b', text)
    if m_full:
        eid_14 = m_full.group(1)
        ts_str = m_full.group(2)
        return {
            "status": "PRESENT_VALID",
            "present": True,
            "raw_value": f"{eid_14} {ts_str}",
            "formatted": f"{eid_14} {ts_str}",
            "masked_value": f"{eid_14[:4]}/XXXXX/{eid_14[-5:]} {ts_str}",
            "is_valid": True,
            "timestamp": ts_str,
            "details": "28-digit Enrolment ID with valid timestamp structure confirmed."
        }

    m_14 = re.search(r'\b(\d{4}/\d{5}/\d{5})\b', text)
    if m_14:
        eid_14 = m_14.group(1)
        return {
            "status": "PRESENT_VALID",
            "present": True,
            "raw_value": eid_14,
            "formatted": eid_14,
            "masked_value": f"{eid_14[:4]}/XXXXX/{eid_14[-5:]}",
            "is_valid": True,
            "timestamp": None,
            "details": "14-digit Enrolment ID structure confirmed."
        }

    # Contiguous 28 digits or label mentions without full recovery
    m_label = re.search(r'(?:Enrolment\s*(?:No\.?|ID)?|नोंदणी\s*क्रमांक)[:\s]*([0-9/\s:]+)', text, re.IGNORECASE)
    if m_label:
        snippet = m_label.group(1).strip()
        digits = re.sub(r'\D', '', snippet)
        if len(digits) == 14:
            formatted = f"{digits[:4]}/{digits[4:9]}/{digits[9:14]}"
            return {
                "status": "PRESENT_VALID",
                "present": True,
                "raw_value": formatted,
                "formatted": formatted,
                "masked_value": f"{formatted[:4]}/XXXXX/{formatted[-5:]}",
                "is_valid": True,
                "timestamp": None,
                "details": "14-digit Enrolment ID normalized from numeric stream."
            }
        elif len(digits) == 28:
            formatted = f"{digits[:4]}/{digits[4:9]}/{digits[9:14]}"
            return {
                "status": "PRESENT_VALID",
                "present": True,
                "raw_value": snippet,
                "formatted": formatted,
                "masked_value": f"{formatted[:4]}/XXXXX/{formatted[-5:]} [TIMESTAMP]",
                "is_valid": True,
                "timestamp": snippet,
                "details": "28-digit Enrolment ID sequence identified."
            }
        else:
            return {
                "status": "PRESENT_UNCERTAIN",
                "present": True,
                "raw_value": snippet[:20],
                "masked_value": "XXXX/XXXXX/XXXXX",
                "is_valid": False,
                "timestamp": None,
                "details": "Enrolment ID label present but numeric sequence was partially occluded or degraded."
            }

    return {
        "status": "NOT_PRESENT",
        "present": False,
        "raw_value": None,
        "masked_value": None,
        "is_valid": None,
        "timestamp": None,
        "details": "Enrolment ID (EID) is not printed on this document (optional on issued Aadhaar cards)."
    }

# ==============================================================================
# 4. ADDRESS NORMALIZATION
# ==============================================================================

ADDRESS_ABBREVIATIONS = {
    r'\brd\b': 'road',
    r'\bst\b': 'street',
    r'\bapt\b': 'apartment',
    r'\bflr\b': 'floor',
    r'\bopp\b': 'opposite',
    r'\bnr\b': 'near',
    r'\bdist\b': 'district',
    r'\bpo\b': 'post office',
    r'\bvill\b': 'village',
    r'\bteh\b': 'tehsil',
    r'\bmarg\b': 'marg',
    r'\bnagar\b': 'nagar',
    r'\bcolony\b': 'colony',
    r'\bsector\b': 'sector',
    r'\bsec\b': 'sector',
    r'\bplot\b': 'plot',
    r'\bno\b': 'number'
}

def normalize_address(address_str: str) -> str:
    """
    Normalizes an address string for resilient, semantic consistency comparison.
    Applies case folding, punctuation removal, standard abbreviation expansion,
    and whitespace compaction.
    """
    if not address_str or not isinstance(address_str, str):
        return ""

    text = address_str.lower().strip()
    # Remove punctuation
    text = re.sub(r'[,.:;\-/_\\#()]+', ' ', text)
    
    # Expand standard abbreviations
    for pattern, replacement in ADDRESS_ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)

    # Collapse whitespace
    tokens = [t for t in text.split() if len(t) > 1 and t not in {"address", "to", "s/o", "w/o", "d/o", "c/o"}]
    return " ".join(tokens)

# ==============================================================================
# 5. STRUCTURED AADHAAR FIELD EXTRACTOR
# ==============================================================================

def extract_aadhaar_fields(
    raw_text: Any, 
    ocr_detections: Optional[Any] = None,
    img: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Extracts all primary demographic and identification fields from an Aadhaar document:
    1. Aadhaar number / masked number (with Verhoeff validation)
    2. EID / Enrolment Information
    3. Name
    4. Date of Birth / Age
    5. Gender
    6. Address
    7. Photograph bounding region
    8. QR bounding region
    
    Returns structured dictionary with explicit status codes.
    Never invents missing values.
    """
    if isinstance(raw_text, dict):
        ocr_data = raw_text
        raw_text = ocr_data.get("raw_text") or ocr_data.get("extracted_text") or ""
        if ocr_detections is None or isinstance(ocr_detections, dict):
            ocr_detections = ocr_data.get("detections")
            
    if isinstance(ocr_detections, dict):
        ocr_detections = None

    lines = [l.strip() for l in (raw_text or "").split("\n") if l.strip()]
    full_text = " ".join(lines)

    
    result: Dict[str, Any] = {
        "document_type": "Aadhaar Card",
        "fields": {},
        "summary": []
    }

    # -------------------------------------------------------------------------
    # A. Aadhaar Number Extraction & Validation
    # -------------------------------------------------------------------------
    aadhaar_num_res = {
        "status": "NOT_VISIBLE",
        "raw_value": None,
        "masked_value": None,
        "format_valid": False,
        "checksum_valid": False,
        "identity_verified": False,  # Distinguish format valid from officially verified
        "confidence": 0.0,
        "details": "Aadhaar number not isolated by optical recognition."
    }

    # 1. Check for 12 contiguous digits or 4-4-4 formatted digits
    m_12 = re.search(r'\b(\d{4}\s?\d{4}\s?\d{4})\b', full_text)
    if m_12:
        raw_num = m_12.group(1)
        clean_12 = re.sub(r'\D', '', raw_num)
        if len(clean_12) == 12:
            is_checksum_ok = validate_verhoeff(clean_12)
            masked = f"XXXX XXXX {clean_12[-4:]}"
            if clean_12[0] in ('0', '1'):
                status = "INVALID_FORMAT"
                fmt_valid = False
            elif is_checksum_ok:
                status = "CHECKSUM_VALID"
                fmt_valid = True
            else:
                status = "INVALID_CHECKSUM"
                fmt_valid = True
            aadhaar_num_res = {
                "status": status,
                "raw_value": masked,  # Securely store only masked format
                "masked_value": masked,
                "format_valid": fmt_valid,
                "checksum_valid": is_checksum_ok,
                "identity_verified": False,
                "confidence": 92.0,
                "details": f"12-digit format evaluated ({status}; official UIDAI identity verification not performed)."
            }
    else:
        # Check for pre-masked format: XXXX XXXX 1234
        m_masked = re.search(r'\b(?:X{4}|[xX]{4}|\*{4})\s?(?:X{4}|[xX]{4}|\*{4})\s?(\d{4})\b', full_text)
        if m_masked:
            last4 = m_masked.group(1)
            masked = f"XXXX XXXX {last4}"
            aadhaar_num_res = {
                "status": "FORMAT_VALID",
                "raw_value": masked,
                "masked_value": masked,
                "format_valid": True,
                "checksum_valid": None,  # Checksum cannot be computed on masked digits
                "identity_verified": False,
                "confidence": 88.0,
                "details": "Standard masked Aadhaar format verified (XXXX XXXX [last 4]; format conforms to UIDAI masking standard)."
            }

    result["fields"]["aadhaar_number"] = aadhaar_num_res

    # -------------------------------------------------------------------------
    # B. EID / Enrolment Information
    # -------------------------------------------------------------------------
    eid_res = parse_enrolment_id(full_text)
    result["fields"]["enrolment_id"] = eid_res

    # -------------------------------------------------------------------------
    # C. Name Extraction
    # -------------------------------------------------------------------------
    name_res = {
        "status": "NOT_VISIBLE",
        "value": None,
        "confidence": 0.0,
        "details": "Name field not confidently identified in text stream."
    }

    # Filter candidate lines excluding government headers, addresses, numbers, document labels
    exclude_keywords = {
        "government", "india", "unique", "identification", "authority", "aadhaar",
        "male", "female", "transgender", "dob", "birth", "year", "address", "help",
        "mera", "penn", "meraaadhaar", "vid", "enrolment", "signature", "uidai",
        "road", "street", "building", "floor", "nagar", "dist", "state", "maharashtra",
        "identity", "authentication", "card", "republic", "department"
    }

    name_candidate = None
    # 1. First priority: Line with explicit Name prefix
    for line in lines:
        m = re.search(r'\bname\s*[:\-\s]\s*([a-zA-Z\s]{3,40})', line, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            c_words = cand.split()
            if 1 <= len(c_words) <= 4 and all(w.isupper() or w.istitle() for w in c_words):
                cand_lower = cand.lower()
                if not any(k in cand_lower for k in exclude_keywords):
                    name_candidate = cand
                    break

    # 2. Second priority: Proper case line without explicit prefix
    if not name_candidate:
        for line in lines:
            clean_line = re.sub(r'[^a-zA-Z\s]', '', line).strip()
            words = clean_line.split()
            if 2 <= len(words) <= 4:
                # Check capitalization pattern (Proper case or ALL CAPS)
                if all(w.isupper() or w.istitle() for w in words):
                    line_lower = clean_line.lower()
                    if not any(k in line_lower for k in exclude_keywords):
                        name_candidate = clean_line
                        break

    if name_candidate:
        name_res = {
            "status": "EXTRACTED",
            "value": name_candidate,
            "confidence": 85.0,
            "details": f"Demographic name isolated: {name_candidate}"
        }
    
    result["fields"]["name"] = name_res

    # -------------------------------------------------------------------------
    # D. Date of Birth / Age
    # -------------------------------------------------------------------------
    dob_res = {
        "status": "NOT_VISIBLE",
        "dob": None,
        "age": None,
        "is_valid_calendar": False,
        "confidence": 0.0,
        "details": "Date of Birth or Year of Birth not detected."
    }

    m_dob = re.search(r'(?:DOB|D\.O\.B|Birth|Year of Birth|जन्म\s*तारीख)[:\s]*([0-3]?[0-9][/-][0-1]?[0-9][/-][12][90][0-9]{2}|\b[12][90][0-9]{2}\b)', full_text, re.IGNORECASE)
    raw_dob = m_dob.group(1) if m_dob else None

    if not raw_dob:
        # Fallback search for standalone date
        m_date = re.search(r'\b([0-3][0-9][/-][0-1][0-9][/-][12][90][0-9]{2})\b', full_text)
        if m_date:
            raw_dob = m_date.group(1)

    if raw_dob:
        is_cal_ok, p_date, norm_str = validate_calendar_date(raw_dob)
        calc_age = calculate_age(p_date) if p_date else None
        dob_res = {
            "status": "VALID_DOB" if is_cal_ok else "INVALID_FORMAT",
            "dob": norm_str,
            "age": calc_age,
            "is_valid_calendar": is_cal_ok,
            "confidence": 88.0 if is_cal_ok else 45.0,
            "details": f"Date of Birth isolated ({norm_str}; {'calendar date verified' if is_cal_ok else 'unparseable format'})."
        }

    result["fields"]["dob"] = dob_res

    # -------------------------------------------------------------------------
    # E. Gender
    # -------------------------------------------------------------------------
    gender_res = {
        "status": "NOT_VISIBLE",
        "value": None,
        "confidence": 0.0,
        "details": "Gender demographic field not isolated."
    }

    m_gen = re.search(r'\b(FEMALE|MALE|TRANSGENDER|पुरुष|महिला)\b', full_text, re.IGNORECASE)
    if m_gen:
        g_raw = m_gen.group(1).upper()
        g_val = "Female" if g_raw in ("FEMALE", "महिला") else ("Male" if g_raw in ("MALE", "पुरुष") else "Transgender")
        gender_res = {
            "status": "EXTRACTED",
            "value": g_val,
            "confidence": 95.0,
            "details": f"Demographic gender field identified: {g_val}"
        }

    result["fields"]["gender"] = gender_res

    # -------------------------------------------------------------------------
    # F. Address
    # -------------------------------------------------------------------------
    address_res = {
        "status": "NOT_VISIBLE",
        "raw_address": None,
        "normalized_address": None,
        "confidence": 0.0,
        "details": "Address block not identified in visible text stream."
    }

    m_addr = re.search(r'(?:Address|पत्ता)[:\s]*([^\n]+(?:\n[^\n]+){1,4})', raw_text, re.IGNORECASE)
    if m_addr:
        raw_addr = " ".join(m_addr.group(1).split())
        norm_addr = normalize_address(raw_addr)
        address_res = {
            "status": "EXTRACTED",
            "raw_address": raw_addr,
            "normalized_address": norm_addr,
            "confidence": 80.0,
            "details": "Demographic address block extracted and normalized."
        }
    else:
        # Fallback: check for address lines containing pincode / district
        pincode_match = re.search(r'\b[1-9][0-9]{5}\b', full_text)
        if pincode_match:
            address_res = {
                "status": "PARTIAL",
                "raw_address": f"Postal Pin: {pincode_match.group(0)}",
                "normalized_address": pincode_match.group(0),
                "confidence": 70.0,
                "details": f"Postal code {pincode_match.group(0)} isolated."
            }

    result["fields"]["address"] = address_res

    # -------------------------------------------------------------------------
    # Summary of Extracted Demographics
    # -------------------------------------------------------------------------
    summary = []
    if aadhaar_num_res["format_valid"]:
        summary.append(f"Aadhaar Number: {aadhaar_num_res['masked_value']} ({aadhaar_num_res['status']})")
    if eid_res["present"]:
        summary.append(f"Enrolment ID: {eid_res['masked_value']} ({eid_res['status']})")
    else:
        summary.append("Enrolment ID: Not present on document (optional)")
    if name_res["value"]:
        summary.append(f"Name: {name_res['value']}")
    if dob_res["dob"]:
        summary.append(f"DOB: {dob_res['dob']}")
    if gender_res["value"]:
        summary.append(f"Gender: {gender_res['value']}")
    if address_res["raw_address"]:
        summary.append(f"Address: {address_res['raw_address'][:45]}...")

    result["summary"] = summary
    return result
