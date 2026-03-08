import hashlib
import hmac
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("PORTFOLIO_DATA_DIR", os.path.join(BASE_DIR, "data"))
USERS_DB = os.path.join(DATA_DIR, "users.db")
PBKDF2_ITERATIONS = 200_000

# 현재 활성 사용자 DB 경로 (set_current_user로 설정)
_current_db_path = os.path.join(BASE_DIR, "portfolio.db")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def normalize_username(username):
    return username.strip()


def validate_username(username):
    username = normalize_username(username)
    if len(username) < 2 or len(username) > 30:
        return "아이디는 2자 이상 30자 이하여야 합니다."
    if not all(char.isalnum() or char in ("_", "-", ".") for char in username):
        return "아이디는 한글/영문/숫자와 . _ - 만 사용할 수 있습니다."
    return None


def _user_db_path(username):
    normalized = normalize_username(username)
    safe_name = "".join(char for char in normalized if char.isalnum() or char in ("_", "-")) or "user"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
    return os.path.join(DATA_DIR, f"{safe_name}_{digest}.db")


def _legacy_user_db_path(username):
    safe_name = "".join(char for char in normalize_username(username) if char.isalnum() or char in ("_", "-"))
    return os.path.join(DATA_DIR, f"{safe_name}.db")


def set_current_user(username):
    """현재 사용자의 DB 경로 설정"""
    global _current_db_path
    _ensure_data_dir()
    current_path = _user_db_path(username)
    legacy_path = _legacy_user_db_path(username)
    if os.path.exists(legacy_path) and not os.path.exists(current_path):
        _current_db_path = legacy_path
    else:
        _current_db_path = current_path


def get_connection():
    _ensure_data_dir()
    conn = sqlite3.connect(_current_db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ========== User Auth ==========

def init_users_db():
    """사용자 계정 DB 초기화"""
    _ensure_data_dir()
    conn = sqlite3.connect(USERS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${password_hash.hex()}"


def _verify_password(password, stored_hash):
    if stored_hash.startswith("pbkdf2_sha256$"):
        _, iterations, salt_hex, hash_hex = stored_hash.split("$", 3)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
        return hmac.compare_digest(candidate, hash_hex)

    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, stored_hash)


def register_user(username, password):
    """회원가입. 성공 시 True, 이미 존재하면 False"""
    _ensure_data_dir()
    username = normalize_username(username)
    conn = sqlite3.connect(USERS_DB)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, _hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username, password):
    """로그인 검증. 성공 시 True"""
    _ensure_data_dir()
    username = normalize_username(username)
    conn = sqlite3.connect(USERS_DB)
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    if row and _verify_password(password, row[0]):
        return True
    return False


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT DEFAULT '',
            school TEXT DEFAULT '',
            major TEXT DEFAULT '',
            status TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            period TEXT,
            role TEXT,
            description TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS practicals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            organization TEXT,
            period TEXT,
            description TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            period TEXT,
            tech_stack TEXT,
            role TEXT,
            description TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            period TEXT,
            description TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS strengths (
            id INTEGER PRIMARY KEY,
            content TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS weaknesses (
            id INTEGER PRIMARY KEY,
            content TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            position TEXT,
            prompt TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 기본 프로필 행이 없으면 생성
    c.execute("SELECT COUNT(*) FROM profile")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO profile (id, name, school, major, status) VALUES (1, '', '', '', '')")

    # 기본 강점 행이 없으면 생성
    c.execute("SELECT COUNT(*) FROM strengths")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO strengths (id, content) VALUES (1, '')")

    # 기본 단점 행이 없으면 생성
    c.execute("SELECT COUNT(*) FROM weaknesses")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO weaknesses (id, content) VALUES (1, '')")

    conn.commit()
    conn.close()


# ========== Profile ==========

def get_profile():
    conn = get_connection()
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"id": 1, "name": "", "school": "", "major": "", "status": ""}


def update_profile(name, school, major, status):
    conn = get_connection()
    conn.execute(
        "UPDATE profile SET name=?, school=?, major=?, status=? WHERE id=1",
        (name, school, major, status)
    )
    conn.commit()
    conn.close()


# ========== Experiences ==========

def get_experiences():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM experiences ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_experience(company, period, role, description):
    conn = get_connection()
    conn.execute(
        "INSERT INTO experiences (company, period, role, description) VALUES (?, ?, ?, ?)",
        (company, period, role, description)
    )
    conn.commit()
    conn.close()


def update_experience(id, company, period, role, description):
    conn = get_connection()
    conn.execute(
        "UPDATE experiences SET company=?, period=?, role=?, description=? WHERE id=?",
        (company, period, role, description, id)
    )
    conn.commit()
    conn.close()


def delete_experience(id):
    conn = get_connection()
    conn.execute("DELETE FROM experiences WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ========== Practicals ==========

def get_practicals():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM practicals ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_practical(name, organization, period, description):
    conn = get_connection()
    conn.execute(
        "INSERT INTO practicals (name, organization, period, description) VALUES (?, ?, ?, ?)",
        (name, organization, period, description)
    )
    conn.commit()
    conn.close()


def update_practical(id, name, organization, period, description):
    conn = get_connection()
    conn.execute(
        "UPDATE practicals SET name=?, organization=?, period=?, description=? WHERE id=?",
        (name, organization, period, description, id)
    )
    conn.commit()
    conn.close()


def delete_practical(id):
    conn = get_connection()
    conn.execute("DELETE FROM practicals WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ========== Projects ==========

def get_projects():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_project(name, period, tech_stack, role, description):
    conn = get_connection()
    conn.execute(
        "INSERT INTO projects (name, period, tech_stack, role, description) VALUES (?, ?, ?, ?, ?)",
        (name, period, tech_stack, role, description)
    )
    conn.commit()
    conn.close()


def update_project(id, name, period, tech_stack, role, description):
    conn = get_connection()
    conn.execute(
        "UPDATE projects SET name=?, period=?, tech_stack=?, role=?, description=? WHERE id=?",
        (name, period, tech_stack, role, description, id)
    )
    conn.commit()
    conn.close()


def delete_project(id):
    conn = get_connection()
    conn.execute("DELETE FROM projects WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ========== Skills ==========

def get_skills():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM skills ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_skill(skill):
    conn = get_connection()
    conn.execute("INSERT INTO skills (skill) VALUES (?)", (skill,))
    conn.commit()
    conn.close()


def delete_skill(id):
    conn = get_connection()
    conn.execute("DELETE FROM skills WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ========== Certifications ==========

def get_certifications():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM certifications ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_certification(name, date):
    conn = get_connection()
    conn.execute("INSERT INTO certifications (name, date) VALUES (?, ?)", (name, date))
    conn.commit()
    conn.close()


def update_certification(id, name, date):
    conn = get_connection()
    conn.execute("UPDATE certifications SET name=?, date=? WHERE id=?", (name, date, id))
    conn.commit()
    conn.close()


def delete_certification(id):
    conn = get_connection()
    conn.execute("DELETE FROM certifications WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ========== Activities ==========

def get_activities():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM activities ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_activity(name, period, description):
    conn = get_connection()
    conn.execute(
        "INSERT INTO activities (name, period, description) VALUES (?, ?, ?)",
        (name, period, description)
    )
    conn.commit()
    conn.close()


def update_activity(id, name, period, description):
    conn = get_connection()
    conn.execute(
        "UPDATE activities SET name=?, period=?, description=? WHERE id=?",
        (name, period, description, id)
    )
    conn.commit()
    conn.close()


def delete_activity(id):
    conn = get_connection()
    conn.execute("DELETE FROM activities WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ========== Strengths ==========

def get_strengths():
    conn = get_connection()
    row = conn.execute("SELECT * FROM strengths WHERE id = 1").fetchone()
    conn.close()
    if row:
        return dict(row)["content"]
    return ""


def update_strengths(content):
    conn = get_connection()
    conn.execute("UPDATE strengths SET content=? WHERE id=1", (content,))
    conn.commit()
    conn.close()


# ========== Weaknesses ==========

def get_weaknesses():
    conn = get_connection()
    row = conn.execute("SELECT * FROM weaknesses WHERE id = 1").fetchone()
    conn.close()
    if row:
        return dict(row)["content"]
    return ""


def update_weaknesses(content):
    conn = get_connection()
    conn.execute("UPDATE weaknesses SET content=? WHERE id=1", (content,))
    conn.commit()
    conn.close()


# ========== History ==========

def get_history():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM history ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_history(company, position, prompt):
    conn = get_connection()
    conn.execute(
        "INSERT INTO history (company, position, prompt) VALUES (?, ?, ?)",
        (company, position, prompt)
    )
    conn.commit()
    conn.close()


def delete_history(id):
    conn = get_connection()
    conn.execute("DELETE FROM history WHERE id=?", (id,))
    conn.commit()
    conn.close()


# ========== Full Portfolio ==========

def get_full_portfolio():
    return {
        "profile": get_profile(),
        "experiences": get_experiences(),
        "practicals": get_practicals(),
        "projects": get_projects(),
        "skills": get_skills(),
        "certifications": get_certifications(),
        "activities": get_activities(),
        "strengths": get_strengths(),
        "weaknesses": get_weaknesses(),
    }


def clear_all_portfolio():
    """포트폴리오 전체 초기화"""
    conn = get_connection()
    conn.execute("UPDATE profile SET name='', school='', major='', status='' WHERE id=1")
    conn.execute("DELETE FROM experiences")
    conn.execute("DELETE FROM practicals")
    conn.execute("DELETE FROM projects")
    conn.execute("DELETE FROM skills")
    conn.execute("DELETE FROM certifications")
    conn.execute("DELETE FROM activities")
    conn.execute("UPDATE strengths SET content='' WHERE id=1")
    conn.execute("UPDATE weaknesses SET content='' WHERE id=1")
    conn.commit()
    conn.close()


def clear_section(section_name):
    """특정 섹션만 초기화"""
    conn = get_connection()
    if section_name == "profile":
        conn.execute("UPDATE profile SET name='', school='', major='', status='' WHERE id=1")
    elif section_name == "experiences":
        conn.execute("DELETE FROM experiences")
    elif section_name == "practicals":
        conn.execute("DELETE FROM practicals")
    elif section_name == "projects":
        conn.execute("DELETE FROM projects")
    elif section_name == "skills":
        conn.execute("DELETE FROM skills")
    elif section_name == "certifications":
        conn.execute("DELETE FROM certifications")
    elif section_name == "activities":
        conn.execute("DELETE FROM activities")
    elif section_name == "strengths":
        conn.execute("UPDATE strengths SET content='' WHERE id=1")
    elif section_name == "weaknesses":
        conn.execute("UPDATE weaknesses SET content='' WHERE id=1")
    conn.commit()
    conn.close()

