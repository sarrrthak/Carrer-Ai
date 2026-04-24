"""
CareerAI Pro — Patch Script
Run this ONCE from inside careerai_pro_modified/:
    python APPLY_PATCH.py
It overwrites only the 3 files that had bugs.
"""
import os, sys, shutil, textwrap

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = {}

# ── FILE 1: backend/api_connectors/__init__.py ──────────────────────
FILES["backend/api_connectors/__init__.py"] = textwrap.dedent('''
"""
CareerAI Pro — API Connectors
"""
import concurrent.futures, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jsearch_connector    import fetch_jsearch_jobs,    raw_call as _r1
from activejobs_connector import fetch_activejobs,      raw_call as _r2
from linkedin_connector   import fetch_linkedin_jobs,   raw_call as _r3
from indeed_connector     import fetch_indeed_jobs,     raw_call as _r4
from glassdoor_connector  import fetch_glassdoor_jobs,  raw_call as _r5
from jobsapi_connector    import fetch_indeed_jobs as fetch_indeed12, raw_call as _r6

SOURCE_META = {
    "jsearch":    {"label": "JSearch",        "color": "#FF6B8A", "enabled": True},
    "activejobs": {"label": "Active Jobs DB", "color": "#9B6EFF", "enabled": False},
    "linkedin":   {"label": "LinkedIn",       "color": "#0A66C2", "enabled": False},
    "indeed":     {"label": "Jobs API",       "color": "#F5C842", "enabled": True},
    "glassdoor":  {"label": "Glassdoor",      "color": "#0CAA41", "enabled": True},
    "indeed12":   {"label": "Indeed",         "color": "#003A9B", "enabled": True},
}

def connector_status():
    return {k: v["enabled"] for k, v in SOURCE_META.items()}

def fetch_all_jobs(query="", location="", remote="",
                   sources=None, limit_per_source=50, parallel=True):
    enabled = {k for k, v in SOURCE_META.items() if v.get("enabled", True)}
    active  = (set(sources) if sources else enabled) & enabled

    tasks = [
        ("jsearch",    fetch_jsearch_jobs,  {"query": query or "AI engineer", "location": location}),
        ("activejobs", fetch_activejobs,    {"title_filter": query, "location_filter": location}),
        ("linkedin",   fetch_linkedin_jobs, {"title_filter": query, "location_filter": location, "limit": limit_per_source}),
        ("indeed",     fetch_indeed_jobs,   {"query": query or "AI engineer"}),
        ("glassdoor",  fetch_glassdoor_jobs,{"keyword": query or "AI engineer", "location": location}),
        ("indeed12",   fetch_indeed12,      {"query": query or "AI engineer"}),
    ]
    tasks = [(k, fn, kw) for k, fn, kw in tasks if k in active]

    results, errors = {}, {}
    if parallel and len(tasks) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as pool:
            futures = {pool.submit(fn, **kw): key for key, fn, kw in tasks}
            for future, key in futures.items():
                try:
                    results[key] = future.result(timeout=15)
                except Exception as exc:
                    errors[key]  = str(exc)
                    results[key] = []
    else:
        for key, fn, kw in tasks:
            try:
                results[key] = fn(**kw)
            except Exception as exc:
                errors[key]  = str(exc)
                results[key] = []

    seen, merged, src_count = set(), [], {}
    for key, jobs in results.items():
        src_count[key] = 0
        if not isinstance(jobs, list):
            errors[key] = f"Unexpected response type: {type(jobs)}"
            continue
        for j in jobs:
            url = j.get("url", "")
            if url and url != "#" and url in seen:
                continue
            if url:
                seen.add(url)
            if remote and j.get("remote", "").lower() != remote.lower():
                continue
            merged.append(j)
            src_count[key] += 1

    return {"jobs": merged, "total": len(merged), "sources": src_count, "errors": errors}

if __name__ == "__main__":
    tests = [
        ("1 — JSearch",     _r1),
        ("2 — Active Jobs", _r2),
        ("3 — LinkedIn",    _r3),
        ("4 — Jobs API",    _r4),
        ("5 — Glassdoor",   _r5),
        ("6 — Indeed12",    _r6),
    ]
    for name, fn in tests:
        print(f"\\n{'='*50}\\n  CONNECTOR {name}\\n{'='*50}")
        try:
            out = fn()
            print(out[:400] + ("…" if len(out) > 400 else ""))
        except Exception as e:
            print(f"  ERROR: {e}")
''').lstrip()

# ── FILE 2: backend/server.py  (only the connector block) ──────────
# We patch it in-place rather than replacing the whole file
SERVER_OLD = '''try:
    from backend.api_connectors import fetch_all_jobs, SOURCE_META, connector_status
    # Keys are managed per-connector inside api_connectors/api_keys.py
    CONNECTORS_READY = True
    print(f"  ✓ API Connectors loaded: {[k for k,v in SOURCE_META.items() if v['enabled']]}") 
except Exception as _ce:
    CONNECTORS_READY = False
    SOURCE_META = {}
    print(f"  ✗ API Connectors not loaded ({_ce})")

    def fetch_all_jobs(**kw):
        return {"jobs": [], "total": 0, "sources": {}, "errors": {"connectors": str(_ce)}}

    def connector_status():
        return {}'''

SERVER_NEW = '''try:
    from backend.api_connectors import fetch_all_jobs, SOURCE_META, connector_status
    CONNECTORS_READY = True
    enabled_list = [k for k, v in SOURCE_META.items() if v.get("enabled")]
    print(f"  ✓ API Connectors loaded: {enabled_list}")
except Exception as _ce:
    CONNECTORS_READY = False
    SOURCE_META = {}
    _ce_msg = str(_ce)   # IMPORTANT: capture before except block ends — Python deletes _ce after
    print(f"  ✗ API Connectors not loaded ({_ce_msg})")

    def fetch_all_jobs(**kw):
        return {"jobs": [], "total": 0, "sources": {}, "errors": {"connectors": _ce_msg}}

    def connector_status():
        return {}'''

def patch_server():
    path = os.path.join(BASE, "backend", "server.py")
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # Try exact match first
    if SERVER_OLD.strip() in src:
        src = src.replace(SERVER_OLD.strip(), SERVER_NEW.strip(), 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        print("  ✓ backend/server.py — connector block patched")
        return True

    # Already patched?
    if "_ce_msg" in src:
        print("  ✓ backend/server.py — already patched, skipping")
        return True

    # Fallback: line-by-line replacement of the _ce line
    lines = src.splitlines()
    changed = False
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Fix the str(_ce) bug line
        if 'str(_ce)' in line and 'errors' in line:
            new_lines.append(line.replace('str(_ce)', '_ce_msg'))
            changed = True
        # Capture _ce_msg right after except line
        elif line.strip().startswith('except Exception as _ce:') and '_ce_msg' not in lines[i+1] if i+1 < len(lines) else False:
            new_lines.append(line)
            # Insert _ce_msg capture on the very next line
            indent = len(line) - len(line.lstrip()) + 4
            new_lines.append(' ' * indent + '_ce_msg = str(_ce)')
            changed = True
        else:
            new_lines.append(line)
        i += 1

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write('\n'.join(new_lines))
        print("  ✓ backend/server.py — fallback patch applied")
    else:
        print("  ⚠ backend/server.py — could not find target block (may already be patched)")
    return changed


def patch_connectors():
    """Add json.JSONDecodeError and message-check to glassdoor, indeed, jobsapi connectors."""
    patches = {
        "backend/api_connectors/glassdoor_connector.py": (
            '    resp = json.loads(res.read().decode("utf-8"))\n'
            '    jobs = resp.get("jobs") or resp.get("data") or (resp if isinstance(resp, list) else [])\n'
            '    return [_normalize(j) for j in jobs if isinstance(j, dict)]',
            '    raw = res.read().decode("utf-8")\n'
            '    try:\n'
            '        resp = json.loads(raw)\n'
            '    except json.JSONDecodeError:\n'
            '        return []\n'
            '    if isinstance(resp, dict) and resp.get("message"):\n'
            '        return []\n'
            '    jobs = resp.get("jobs") or resp.get("data") or (resp if isinstance(resp, list) else [])\n'
            '    return [_normalize(j) for j in jobs if isinstance(j, dict)]'
        ),
        "backend/api_connectors/indeed_connector.py": (
            '    resp = json.loads(res.read().decode("utf-8"))\n'
            '    jobs = resp.get("jobs") or resp.get("data") or (resp if isinstance(resp, list) else [])\n'
            '    return [_normalize(j) for j in jobs if isinstance(j, dict)]',
            '    raw = res.read().decode("utf-8")\n'
            '    try:\n'
            '        resp = json.loads(raw)\n'
            '    except json.JSONDecodeError:\n'
            '        return []\n'
            '    if isinstance(resp, dict) and resp.get("message"):\n'
            '        return []\n'
            '    jobs = resp.get("jobs") or resp.get("data") or (resp if isinstance(resp, list) else [])\n'
            '    return [_normalize(j) for j in jobs if isinstance(j, dict)]'
        ),
        "backend/api_connectors/jobsapi_connector.py": (
            '    resp   = json.loads(res.read().decode("utf-8"))\n'
            '    jobs   = resp.get("jobs") or resp.get("hits") or resp.get("data") or (resp if isinstance(resp, list) else [])\n'
            '    return [_normalize(j) for j in jobs if isinstance(j, dict)]',
            '    raw    = res.read().decode("utf-8")\n'
            '    try:\n'
            '        resp = json.loads(raw)\n'
            '    except json.JSONDecodeError:\n'
            '        return []\n'
            '    if isinstance(resp, dict) and resp.get("message"):\n'
            '        return []\n'
            '    jobs   = resp.get("jobs") or resp.get("hits") or resp.get("data") or (resp if isinstance(resp, list) else [])\n'
            '    return [_normalize(j) for j in jobs if isinstance(j, dict)]'
        ),
    }
    for rel_path, (old, new) in patches.items():
        fpath = os.path.join(BASE, rel_path)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                src = f.read()
            if 'json.JSONDecodeError' in src:
                print(f"  ✓ {rel_path} — already patched")
                continue
            if old in src:
                src = src.replace(old, new, 1)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(src)
                print(f"  ✓ {rel_path} — patched")
            else:
                print(f"  ⚠ {rel_path} — target not found (may already be patched)")
        except FileNotFoundError:
            print(f"  ✗ {rel_path} — file not found")


def patch_frontend():
    fpath = os.path.join(BASE, "frontend", "index.html")
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            src = f.read()

        changed = False

        # Fix subtitle
        old_sub = 'Live jobs · LinkedIn · Active Jobs DB · Remotive · TheMuse · Adzuna'
        new_sub = 'Live jobs · JSearch · Glassdoor · Indeed · Remotive · WeWorkRemotely · Arbeitnow'
        if old_sub in src:
            src = src.replace(old_sub, new_sub)
            changed = True

        # Fix source tabs
        old_tabs = '''    <button class="src-tab active-tab" data-src="all" onclick="setApiSource(\'all\',this)">🌐 All Sources</button>
    <button class="src-tab" data-src="linkedin" onclick="setApiSource(\'linkedin\',this)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="#0A66C2" style="vertical-align:middle;margin-right:4px"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>LinkedIn
    </button>
    <button class="src-tab" data-src="activejobs" onclick="setApiSource(\'activejobs\',this)">📋 Active Jobs DB</button>
    <button class="src-tab" data-src="scraped" onclick="setApiSource(\'scraped\',this)">🕷 Scraped Jobs</button>'''

        new_tabs = '''    <button class="src-tab active-tab" data-src="all" onclick="setApiSource(\'all\',this)">🌐 All Sources</button>
    <button class="src-tab" data-src="jsearch" onclick="setApiSource(\'jsearch\',this)">🔍 JSearch</button>
    <button class="src-tab" data-src="glassdoor" onclick="setApiSource(\'glassdoor\',this)">🟢 Glassdoor</button>
    <button class="src-tab" data-src="indeed12" onclick="setApiSource(\'indeed12\',this)">🔵 Indeed</button>
    <button class="src-tab" data-src="scraped" onclick="setApiSource(\'scraped\',this)">🕷 Scraped Jobs</button>'''

        if old_tabs in src:
            src = src.replace(old_tabs, new_tabs)
            changed = True

        # Fix srcLabels
        old_lbl = "{'all':'LinkedIn + Active Jobs DB','linkedin':'LinkedIn','activejobs':'Active Jobs DB'}"
        new_lbl = "{'all':'JSearch + Glassdoor + Indeed','jsearch':'JSearch','glassdoor':'Glassdoor','indeed12':'Indeed','indeed':'Jobs API'}"
        if old_lbl in src:
            src = src.replace(old_lbl, new_lbl)
            changed = True

        # Fix no-jobs error message to show API error detail
        old_nj = "if(!allJobs.length) { showNoJobs('No live jobs found. Check your API key or try a different source.'); return; }"
        new_nj = """if(!allJobs.length) {
        const errDetail = data.errors ? Object.entries(data.errors).map(([k,v])=>k+': '+String(v).substring(0,80)).join('; ') : '';
        showNoJobs('No live jobs found.' + (errDetail ? ' API: ' + errDetail : ' Try a different source or check your RapidAPI key.'));
        return;
      }"""
        if old_nj in src:
            src = src.replace(old_nj, new_nj)
            changed = True

        if changed:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(src)
            print("  ✓ frontend/index.html — patched")
        else:
            print("  ✓ frontend/index.html — already patched or pattern not found")

    except FileNotFoundError:
        print("  ✗ frontend/index.html — file not found")


# ── MAIN ─────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  CareerAI Pro — Applying Bug Fixes")
print("="*55)

# Write __init__.py directly
init_path = os.path.join(BASE, "backend", "api_connectors", "__init__.py")
with open(init_path, "w", encoding="utf-8") as f:
    f.write(FILES["backend/api_connectors/__init__.py"])
print("  ✓ backend/api_connectors/__init__.py — rewritten")

patch_server()
patch_connectors()
patch_frontend()

print("\n" + "="*55)
print("  All patches applied!")
print("  Now run:  python backend/server.py")
print("  Open:     http://localhost:8000")
print("="*55 + "\n")
