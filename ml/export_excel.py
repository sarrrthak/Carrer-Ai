"""
CareerAI — Excel / Power BI Market Report Generator
=====================================================
Generates a rich .xlsx workbook from job market data.
Open in Excel or connect to Power BI Desktop via "Get Data > Excel".

Usage: python ml/export_excel.py
Output: data/CareerAI_Market_Report.xlsx
"""

import pandas as pd
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "../data")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_FILE = os.path.join(OUT_DIR, "CareerAI_Market_Report.xlsx")

# ── Data ──────────────────────────────────────────────────────
salary_data = [
    {"Role":"AI Engineering","Avg Salary ($)":207982,"Min ($)":90000,"Max ($)":374400,"Demand Score":92.6,"YoY Growth (%)":40.2},
    {"Role":"Architecture","Avg Salary ($)":251577,"Min ($)":180000,"Max ($)":384000,"Demand Score":84.0,"YoY Growth (%)":18.0},
    {"Role":"Infrastructure","Avg Salary ($)":203527,"Min ($)":140000,"Max ($)":324000,"Demand Score":85.0,"YoY Growth (%)":18.4},
    {"Role":"ML Operations","Avg Salary ($)":199216,"Min ($)":130000,"Max ($)":312000,"Demand Score":93.0,"YoY Growth (%)":52.8},
    {"Role":"Security","Avg Salary ($)":200400,"Min ($)":140000,"Max ($)":312000,"Demand Score":80.0,"YoY Growth (%)":17.2},
    {"Role":"Product","Avg Salary ($)":194571,"Min ($)":140000,"Max ($)":312000,"Demand Score":85.0,"YoY Growth (%)":17.3},
    {"Role":"Research","Avg Salary ($)":192280,"Min ($)":115000,"max ($)":336000,"Demand Score":88.0,"YoY Growth (%)":17.5},
    {"Role":"Data Science","Avg Salary ($)":181276,"Min ($)":138000,"Max ($)":261600,"Demand Score":91.0,"YoY Growth (%)":31.5},
    {"Role":"Data Engineering","Avg Salary ($)":176157,"Min ($)":130000,"Max ($)":264000,"Demand Score":88.0,"YoY Growth (%)":19.7},
    {"Role":"Robotics","Avg Salary ($)":170851,"Min ($)":125000,"Max ($)":288000,"Demand Score":76.0,"YoY Growth (%)":18.1},
    {"Role":"Governance","Avg Salary ($)":152516,"Min ($)":100000,"Max ($)":252000,"Demand Score":69.8,"YoY Growth (%)":16.9},
    {"Role":"Business","Avg Salary ($)":134145,"Min ($)":95000,"Max ($)":216000,"Demand Score":78.0,"YoY Growth (%)":17.1},
]

skills_data = [
    {"Skill":"Python","Job Count":942,"Category":"Programming"},
    {"Skill":"SQL","Job Count":452,"Category":"Database"},
    {"Skill":"Cloud","Job Count":429,"Category":"Infrastructure"},
    {"Skill":"Statistics","Job Count":350,"Category":"Math/Analytics"},
    {"Skill":"Leadership","Job Count":380,"Category":"Soft Skills"},
    {"Skill":"PyTorch","Job Count":302,"Category":"Deep Learning"},
    {"Skill":"Git","Job Count":295,"Category":"DevOps"},
    {"Skill":"Communication","Job Count":378,"Category":"Soft Skills"},
    {"Skill":"Agile","Job Count":351,"Category":"Methodology"},
    {"Skill":"Linux","Job Count":320,"Category":"OS"},
    {"Skill":"Fine-tuning","Job Count":164,"Category":"LLM"},
    {"Skill":"Kubernetes","Job Count":123,"Category":"Infrastructure"},
    {"Skill":"LLMs","Job Count":125,"Category":"LLM"},
    {"Skill":"CUDA","Job Count":117,"Category":"GPU"},
    {"Skill":"Docker","Job Count":93,"Category":"Infrastructure"},
    {"Skill":"Deep Learning","Job Count":91,"Category":"ML"},
    {"Skill":"MLOps","Job Count":88,"Category":"ML Ops"},
    {"Skill":"TensorFlow","Job Count":86,"Category":"Deep Learning"},
    {"Skill":"LangChain","Job Count":77,"Category":"LLM"},
    {"Skill":"RAG","Job Count":63,"Category":"LLM"},
]

country_data = [
    {"Country":"USA","Avg Salary ($)":226190,"Region":"North America"},
    {"Country":"UAE","Avg Salary ($)":194226,"Region":"Middle East"},
    {"Country":"Switzerland","Avg Salary ($)":190592,"Region":"Europe"},
    {"Country":"Australia","Avg Salary ($)":188000,"Region":"APAC"},
    {"Country":"France","Avg Salary ($)":183152,"Region":"Europe"},
    {"Country":"Singapore","Avg Salary ($)":181831,"Region":"APAC"},
    {"Country":"Germany","Avg Salary ($)":181180,"Region":"Europe"},
    {"Country":"UK","Avg Salary ($)":180644,"Region":"Europe"},
    {"Country":"Canada","Avg Salary ($)":180588,"Region":"North America"},
    {"Country":"Netherlands","Avg Salary ($)":175257,"Region":"Europe"},
    {"Country":"Japan","Avg Salary ($)":170132,"Region":"APAC"},
    {"Country":"China","Avg Salary ($)":134287,"Region":"APAC"},
    {"Country":"India","Avg Salary ($)":133123,"Region":"South Asia"},
]

exp_data = [
    {"Experience Level":"Entry (0-2 yrs)","Avg Salary ($)":150039},
    {"Experience Level":"Mid (3-5 yrs)","Avg Salary ($)":175984},
    {"Experience Level":"Senior (6-9 yrs)","Avg Salary ($)":214280},
    {"Experience Level":"Lead (10+ yrs)","Avg Salary ($)":240055},
]

# ── Write to Excel ─────────────────────────────────────────────
with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
    pd.DataFrame(salary_data).to_excel(writer, sheet_name="Role Salaries & Demand",  index=False)
    pd.DataFrame(skills_data).to_excel(writer, sheet_name="Top Skills",              index=False)
    pd.DataFrame(country_data).to_excel(writer, sheet_name="Country Salaries",       index=False)
    pd.DataFrame(exp_data).to_excel(writer,    sheet_name="Salary by Experience",    index=False)

print(f"Excel report saved: {OUT_FILE}")
print("Connect to Power BI Desktop via: Get Data > Excel Workbook")
