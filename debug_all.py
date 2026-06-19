import sys
import os
import traceback
import asyncio
from dotenv import load_dotenv

backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))
sys.path.append(backend_dir)

from app.core.config import settings

print("=== GEMINI CONFIG ===")
print("Model:", settings.GEMINI_MODEL)
print("Key Loaded:", bool(settings.GEMINI_API_KEY))
print("=====================\n")

print("=== ISSUE 1: COMPLIANCE REPORT ===")
try:
    from app.api.v1.compliance import create_compliance_report
    print("Found manually: UnboundLocalError at line 118 in compliance.py")
except Exception as e:
    print(traceback.format_exc())

print("\n=== ISSUE 2: ASK QUESTIONS ===")
try:
    from app.services.retrieval import retrieve_chunks
    from app.services.generation import generate_answer
    
    question = "What is the policy?"
    selected_files = ["Enterprise Security Policy"]
    results = retrieve_chunks(query=question, n_results=10, selected_files=selected_files)
    formatted_chunks = results.get("documents", [])
    
    answer = generate_answer(
        question=question,
        context_chunks=formatted_chunks,
        comparison_mode=False
    )
    print("Ask Question returned:", answer)
except Exception as e:
    print(traceback.format_exc())

print("\n=== ISSUE 3: TREND INTELLIGENCE ===")
try:
    from app.services.analytics_service import generate_trend_summary
    summary = generate_trend_summary()
    print("Trend summary:", summary)
except Exception as e:
    print(traceback.format_exc())

print("\n=== ISSUE 4: RISK ANALYTICS ===")
try:
    from app.services.compliance_service import assess_risk
    risk = assess_risk(["Enterprise Security Policy"])
    print("Risk Assessment:", risk)
except Exception as e:
    print(traceback.format_exc())
