"""
CareerAI Pro — API Connectors
Unified entry point — delegates to job_service.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_service import search_jobs, SOURCE_META, _cache_key, _CACHE
