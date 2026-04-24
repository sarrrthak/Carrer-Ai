"""
CareerAI Pro — Job Service
Orchestrates parallel fetching from JSearch, Active Jobs DB, and LinkedIn.
Provides in-process TTL caching and unified search interface.
"""
import concurrent.futures, hashlib, json, datetime, re, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jsearch_connector    import fetch_jsearch_jobs
from activejobs_connector import fetch_activejobs
from linkedin_connector   import fetch_linkedin_jobs

# ── Source metadata ───────────────────────────────────────────────
SOURCE_META = {
    "jsearch":    {"label": "JSearch",        "color": "#FF6B8A", "enabled": True},
    "activejobs": {"label": "Active Jobs DB", "color": "#9B6EFF", "enabled": False},  # endpoint disabled on this plan
    "linkedin":   {"label": "LinkedIn",       "color": "#0A66C2", "enabled": False},  # endpoint disabled on this plan
}

# ── Cache ─────────────────────────────────────────────────────────
_CACHE     = {}   # {cache_key: {"data": result_dict, "expires_at": float}}
CACHE_TTL  = 300  # 5 minutes
PER_SOURCE_TIMEOUT = 20  # seconds per API source (JSearch can be slow ~8-12s)

# ── Date window thresholds ────────────────────────────────────────
_DATE_WINDOWS = {
    "today":  0,
    "3days":  3,
    "week":   7,
    "month":  30,
}

_TITLE_NORMALIZE_RE = re.compile(r'[^a-z0-9 ]')


def _cache_key(params: dict) -> str:
    """MD5 of sorted serialised params (page/per_page excluded)."""
    filtered = {k: v for k, v in params.items()
                if k not in ("page", "per_page") and v not in (None, "", 0)}
    return hashlib.md5(json.dumps(filtered, sort_keys=True).encode()).hexdigest()


def _is_cached(key: str) -> bool:
    entry = _CACHE.get(key)
    return entry is not None and entry["expires_at"] > time.time()


def _date_filter(jobs: list, window: str) -> list:
    """Post-filter jobs by date window (for sources without native date param)."""
    days = _DATE_WINDOWS.get(window)
    if days is None:
        return jobs
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    result = []
    for j in jobs:
        dp = j.get("date_posted", "")
        if not dp:
            # No date info — include conservatively
            result.append(j)
            continue
        try:
            posted = datetime.date.fromisoformat(dp[:10])
            if posted >= cutoff:
                result.append(j)
        except (ValueError, TypeError):
            result.append(j)
    return result


def _normalize_title_key(title: str, company: str) -> str:
    """Normalized title+company key for deduplication."""
    t = _TITLE_NORMALIZE_RE.sub("", title.lower()).strip()
    c = _TITLE_NORMALIZE_RE.sub("", company.lower()).strip()
    return t + "|" + c


def _paginate(result: dict, page: int, per_page: int) -> dict:
    jobs  = result["jobs"]
    start = (page - 1) * per_page
    end   = start + per_page
    total = result["total"]
    return {
        **result,
        "jobs":        jobs[start:end],
        "page":        page,
        "per_page":    per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


def search_jobs(query="", location="", remote="", job_type="",
                experience="", date_posted="", salary_min=0,
                page=1, per_page=20, sources=None) -> dict:
    """
    Fetch, deduplicate, filter, and paginate jobs from all enabled sources.

    Args:
        query:       Keyword / job title search term
        location:    City or country string
        remote:      "Remote" | "Hybrid" | "On-site" | ""
        job_type:    "Full-time" | "Part-time" | "Contract" | "Internship" | ""
        experience:  "Entry" | "Mid" | "Senior" | "Executive" | ""
        date_posted: "today" | "3days" | "week" | "month" | ""
        salary_min:  Minimum salary (0 = any)
        page:        Page number (1-based)
        per_page:    Results per page (max 50)
        sources:     List of source keys to use (None = all enabled)

    Returns:
        dict with jobs (paginated), total, page, per_page, total_pages,
             sources, errors, from_cache, cached_at
    """
    # Build cache key from filter params (exclude pagination)
    cache_params = {
        "q":           query,
        "location":    location,
        "remote":      remote,
        "job_type":    job_type,
        "experience":  experience,
        "date_posted": date_posted,
        "salary_min":  salary_min,
        "sources":     sorted(sources) if sources else "all",
    }
    key = _cache_key(cache_params)

    if _is_cached(key):
        cached = _CACHE[key]["data"]
        result = {**cached, "from_cache": True}
        return _paginate(result, page, per_page)

    # Determine active sources
    enabled = {k for k, v in SOURCE_META.items() if v.get("enabled")}
    active  = (set(sources) & enabled) if sources else enabled

    # Build task list
    tasks = [
        ("jsearch",    fetch_jsearch_jobs,
         {"query": query or "software engineer", "location": location,
          "date_posted": date_posted or "", "num_pages": 2}),
        ("activejobs", fetch_activejobs,
         {"title_filter": query, "location_filter": location}),
        ("linkedin",   fetch_linkedin_jobs,
         {"title_filter": query, "location_filter": location, "limit": 50}),
    ]
    tasks = [(k, fn, kw) for k, fn, kw in tasks if k in active]

    raw_results = {}
    errors      = {}

    # Parallel fetch with per-source timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(tasks), 1)) as pool:
        futures = {pool.submit(fn, **kw): key_name for key_name, fn, kw in tasks}
        for future, key_name in futures.items():
            try:
                raw_results[key_name] = future.result(timeout=PER_SOURCE_TIMEOUT)
            except concurrent.futures.TimeoutError:
                future.cancel()
                errors[key_name]      = "timeout"
                raw_results[key_name] = []
            except Exception as exc:
                errors[key_name]      = str(exc)[:120]
                raw_results[key_name] = []

    # Merge with deduplication
    seen_ids     = set()
    seen_urls    = set()
    seen_titles  = set()
    merged       = []
    source_counts = {}

    for src_key, jobs in raw_results.items():
        source_counts[src_key] = 0
        if not isinstance(jobs, list):
            errors[src_key] = f"Unexpected type: {type(jobs).__name__}"
            continue

        # Apply date filter for sources that don't support it natively
        if date_posted and src_key != "jsearch":
            jobs = _date_filter(jobs, date_posted)

        for j in jobs:
            jid    = j.get("id", "")
            url    = j.get("url", "")
            tk     = _normalize_title_key(j.get("title", ""), j.get("company", ""))

            # Dedup by id
            if jid and jid in seen_ids:
                continue
            # Dedup by url
            if url and url != "#" and url in seen_urls:
                continue
            # Dedup by title+company
            if tk and len(tk) > 2 and tk in seen_titles:
                continue

            if jid:     seen_ids.add(jid)
            if url and url != "#": seen_urls.add(url)
            if tk:      seen_titles.add(tk)

            merged.append(j)
            source_counts[src_key] += 1

    # Server-side post-filters
    if remote:
        merged = [j for j in merged
                  if (j.get("remote") or "").lower() == remote.lower()]
    if job_type:
        merged = [j for j in merged
                  if (j.get("job_type") or "").lower() == job_type.lower()]
    if experience:
        merged = [j for j in merged
                  if (j.get("experience") or "").lower() == experience.lower()]
    if salary_min:
        merged = [j for j in merged
                  if (j.get("salary_max") or 0) >= salary_min
                  or (j.get("salary_min") or 0) >= salary_min]

    # Sort: is_new first, then descending by date_posted
    new_jobs  = [j for j in merged if j.get("is_new")]
    rest_jobs = [j for j in merged if not j.get("is_new")]
    rest_jobs.sort(key=lambda j: j.get("date_posted") or "", reverse=True)
    merged = new_jobs + rest_jobs

    result = {
        "jobs":       merged,
        "total":      len(merged),
        "sources":    source_counts,
        "errors":     errors,
        "from_cache": False,
        "cached_at":  datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # Store in cache (full unsliced result)
    _CACHE[key] = {
        "data":       result,
        "expires_at": time.time() + CACHE_TTL,
    }

    return _paginate(result, page, per_page)
