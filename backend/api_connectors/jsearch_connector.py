"""
CONNECTOR 1 — JSearch
Host    : jsearch.p.rapidapi.com
Endpoint: /search
Searches: LinkedIn · Indeed · Glassdoor · ZipRecruiter
"""
import http.client, json, urllib.parse, hashlib, datetime, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_keys import RAPIDAPI_KEY

HOST    = "jsearch.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-key':  RAPIDAPI_KEY,
    'x-rapidapi-host': HOST,
    'Content-Type':    "application/json",
}

# Common skills for description-based extraction (fallback)
SKILL_LIST = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
    "React", "Vue", "Angular", "Node.js", "FastAPI", "Django", "Flask",
    "PyTorch", "TensorFlow", "scikit-learn", "Pandas", "NumPy",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    "LangChain", "LLM", "RAG", "Transformers", "HuggingFace",
    "Git", "CI/CD", "REST", "GraphQL", "Spark",
]

_JOB_TYPE_MAP = {
    "FULLTIME":   "Full-time",
    "PARTTIME":   "Part-time",
    "CONTRACTOR": "Contract",
    "INTERN":     "Internship",
}

_DATE_POSTED_MAP = {
    "today": "today",
    "3days": "3days",
    "week":  "week",
    "month": "month",
}


def _extract_skills(description, qualifications):
    """Extract skills from structured qualifications list or description text."""
    found = []
    text = " ".join(qualifications) if qualifications else (description or "")
    text_lower = text.lower()
    for skill in SKILL_LIST:
        if skill.lower() in text_lower and skill not in found:
            found.append(skill)
        if len(found) >= 8:
            break
    return found


def _experience_from_months(months):
    try:
        m = int(months or 0)
    except (TypeError, ValueError):
        return ""
    if m <= 0:
        return ""
    if m <= 23:
        return "Entry"
    if m <= 60:
        return "Mid"
    if m <= 120:
        return "Senior"
    return "Executive"


def _is_new(date_str):
    if not date_str:
        return False
    try:
        posted = datetime.date.fromisoformat(date_str[:10])
        return (datetime.date.today() - posted).days <= 1
    except (ValueError, TypeError):
        return False


# ── RAW CALL (kept for standalone test) ──────────────────────────
def raw_call():
    conn = http.client.HTTPSConnection(HOST)
    conn.request("GET",
        "/search?query=AI+engineer&page=1&num_pages=1&country=us&date_posted=all",
        headers=HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")


# ── NORMALIZED fetch ──────────────────────────────────────────────
def fetch_jsearch_jobs(query="AI engineer", location="",
                       date_posted="", country="us", num_pages=1):
    dp = _DATE_POSTED_MAP.get(date_posted, "all")
    q  = f"{query} in {location}" if location else query
    params = urllib.parse.urlencode({
        "query":       q,
        "page":        1,
        "num_pages":   num_pages,
        "country":     country,
        "date_posted": dp,
    })
    conn = http.client.HTTPSConnection(HOST)
    conn.request("GET", f"/search?{params}", headers=HEADERS)
    res  = conn.getresponse()
    resp = json.loads(res.read().decode("utf-8"))
    return [_normalize(j) for j in resp.get("data", []) if isinstance(j, dict)]


def _normalize(j):
    # Salary
    sal_min = int(j.get("job_min_salary") or 0)
    sal_max = int(j.get("job_max_salary") or 0)
    if sal_min and sal_max:
        sal_str = f"${sal_min:,}\u2013${sal_max:,}"
    elif sal_min:
        sal_str = f"${sal_min:,}+"
    else:
        sal_str = "Not stated"

    # Remote
    is_remote = str(j.get("job_is_remote", "")).lower() in ("true", "1", "yes")
    remote = "Remote" if is_remote else "On-site"

    # Job type
    jt_raw   = (j.get("job_employment_type") or "").upper()
    job_type = _JOB_TYPE_MAP.get(jt_raw, "")

    # Experience
    exp_data   = j.get("job_required_experience") or {}
    months     = exp_data.get("required_experience_in_months") if isinstance(exp_data, dict) else None
    experience = _experience_from_months(months)

    # Skills
    highlights = j.get("job_highlights") or {}
    quals      = highlights.get("Qualifications", []) if isinstance(highlights, dict) else []
    description = j.get("job_description") or ""
    skills     = _extract_skills(description, quals)

    # Date
    date_str = (j.get("job_posted_at_datetime_utc") or "")[:10]

    # ID
    uid = str(j.get("job_id") or j.get("job_apply_link") or
              (j.get("job_title", "") + j.get("employer_name", "")))
    jid = hashlib.md5(uid.encode()).hexdigest()[:12]

    # Location
    city    = j.get("job_city") or ""
    country = j.get("job_country") or ""
    loc     = ", ".join(filter(None, [city, country])) or "Global"

    return {
        "id":           jid,
        "title":        j.get("job_title", ""),
        "company":      j.get("employer_name", "Unknown"),
        "location":     loc,
        "country":      country,
        "remote":       remote,
        "job_type":     job_type,
        "experience":   experience,
        "salary_min":   sal_min,
        "salary_max":   sal_max,
        "salary_str":   sal_str,
        "skills":       skills,
        "description":  description[:400] + ("\u2026" if len(description) > 400 else ""),
        "url":          j.get("job_apply_link") or j.get("job_google_link") or "#",
        "source":       "JSearch",
        "source_color": "#FF6B8A",
        "date_posted":  date_str,
        "is_new":       _is_new(date_str),
    }


# ── STANDALONE TEST ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 56)
    print("  CONNECTOR 1 — JSearch")
    print("  Host:", HOST)
    print("=" * 56)
    out = raw_call()
    print(out[:600] + ("\u2026" if len(out) > 600 else ""))
