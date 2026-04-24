"""
CONNECTOR 3 — LinkedIn Job Search API
Host    : linkedin-job-search-api.p.rapidapi.com
Endpoint: /active-jb-1h
Source  : 8M+ AI-enriched LinkedIn jobs · hourly refresh
"""
import http.client, json, urllib.parse, hashlib, datetime, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_keys import RAPIDAPI_KEY

HOST    = "linkedin-job-search-api.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-key':  RAPIDAPI_KEY,
    'x-rapidapi-host': HOST,
    'Content-Type':    "application/json",
}

# Skill extraction list (fallback)
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
    "full-time":    "Full-time",
    "full_time":    "Full-time",
    "fulltime":     "Full-time",
    "part-time":    "Part-time",
    "part_time":    "Part-time",
    "parttime":     "Part-time",
    "contract":     "Contract",
    "contractor":   "Contract",
    "internship":   "Internship",
    "intern":       "Internship",
}

# LinkedIn seniority_level → experience
_SENIORITY_MAP = {
    "entry level":      "Entry",
    "associate":        "Mid",
    "mid-senior level": "Mid",
    "mid senior level": "Mid",
    "senior":           "Senior",
    "director":         "Executive",
    "executive":        "Executive",
    "not applicable":   "",
    "internship":       "Entry",
}


def _experience_from_seniority(seniority):
    if not seniority:
        return ""
    return _SENIORITY_MAP.get(str(seniority).lower().strip(), "")


def _extract_skills(description, skills_field):
    """Use API skills field if present, else scan description."""
    if skills_field and isinstance(skills_field, list):
        result = []
        for s in skills_field:
            # Can be a string or dict with "name" key
            name = s.get("name", "") if isinstance(s, dict) else str(s)
            name = name.strip()
            if name:
                result.append(name)
            if len(result) >= 8:
                break
        if result:
            return result
    # Fallback scan
    found = []
    text_lower = (description or "").lower()
    for skill in SKILL_LIST:
        if skill.lower() in text_lower and skill not in found:
            found.append(skill)
        if len(found) >= 8:
            break
    return found


def _normalize_location(loc):
    if not loc:
        return ""
    if isinstance(loc, list):
        return ", ".join(str(x) for x in loc[:2])
    return str(loc)


def _is_new(date_str):
    if not date_str:
        return False
    try:
        posted = datetime.date.fromisoformat(str(date_str)[:10])
        return (datetime.date.today() - posted).days <= 1
    except (ValueError, TypeError):
        return False


# ── RAW CALL (kept for standalone test) ──────────────────────────
def raw_call():
    conn = http.client.HTTPSConnection(HOST)
    conn.request("GET",
        "/active-jb-1h?limit=10&offset=0&description_type=text",
        headers=HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")


# ── NORMALIZED fetch ──────────────────────────────────────────────
def fetch_linkedin_jobs(title_filter="", location_filter="",
                        limit=50, offset=0):
    params = {"limit": limit, "offset": offset, "description_type": "text"}
    if title_filter:
        params["title_filter"] = title_filter
    if location_filter:
        params["location_filter"] = location_filter
    qs   = urllib.parse.urlencode(params)
    conn = http.client.HTTPSConnection(HOST)
    conn.request("GET", f"/active-jb-1h?{qs}", headers=HEADERS)
    res  = conn.getresponse()
    resp = json.loads(res.read().decode("utf-8"))
    jobs = resp if isinstance(resp, list) else resp.get("jobs", resp.get("data", []))
    return [_normalize(j) for j in jobs if isinstance(j, dict)]


def _normalize(j):
    # Location
    loc = _normalize_location(
        j.get("locations_raw") or j.get("location") or ""
    )
    country = j.get("country") or ""

    # Remote
    remote_raw = str(j.get("remote_derived") or j.get("remote") or "").lower()
    if remote_raw in ("true", "1", "yes", "remote"):
        remote = "Remote"
    elif "hybrid" in remote_raw:
        remote = "Hybrid"
    else:
        remote = "On-site"

    # Salary
    sal_min = int(j.get("salary_min") or 0)
    sal_max = int(j.get("salary_max") or 0)
    if sal_min and sal_max:
        sal_str = f"${sal_min:,}\u2013${sal_max:,}"
    elif sal_min:
        sal_str = f"${sal_min:,}+"
    else:
        sal_str = "Not stated"

    # Job type
    jt_raw   = (j.get("employment_type") or j.get("job_type") or "").lower().strip()
    job_type = _JOB_TYPE_MAP.get(jt_raw, "")

    # Experience
    seniority  = j.get("seniority_level") or j.get("experience_level") or ""
    experience = _experience_from_seniority(seniority)

    # Skills
    description = j.get("description") or ""
    skills      = _extract_skills(description, j.get("skills"))

    # Date
    date_str = (j.get("date_posted") or j.get("date_updated") or "")[:10]

    # ID
    uid = str(j.get("id") or j.get("url") or j.get("linkedin_job_url_cleaned") or
              ((j.get("title") or "") + (j.get("organization") or j.get("company") or "")))
    jid = hashlib.md5(uid.encode()).hexdigest()[:12]

    return {
        "id":           jid,
        "title":        j.get("title", ""),
        "company":      j.get("organization") or j.get("company") or "Unknown",
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
        "url":          j.get("url") or j.get("linkedin_job_url_cleaned") or "#",
        "source":       "LinkedIn",
        "source_color": "#0A66C2",
        "date_posted":  date_str,
        "is_new":       _is_new(date_str),
    }


# ── STANDALONE TEST ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 56)
    print("  CONNECTOR 3 — LinkedIn Job Search API")
    print("  Host:", HOST)
    print("=" * 56)
    out = raw_call()
    print(out[:600] + ("\u2026" if len(out) > 600 else ""))
