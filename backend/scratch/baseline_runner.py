import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import asyncio
from app.services.rag_service import retrieve_chunks, generate_answer

queries = [
    {
        "q": "Across all Annual Reports, what are the top recurring strategic priorities discussed by management?",
        "files": ["2020_Annual_Report.docx", "2021_Annual_Report.docx", "2022_Annual_Report.docx", "2023_Annual_Report.docx", "2024_Annual_Report.docx"]
    },
    {
        "q": "Compare security controls defined in the Security Policy against controls listed in the Compliance Controls dataset.",
        "files": ["enterprise_security_policy.pdf", "compliance_controls.csv"]
    },
    {
        "q": "Summarize all incident response obligations and identify any missing controls.",
        "files": ["incident_response_policy.txt", "Cybersecurity Incident Response Procedure"]
    },
    {
        "q": "Identify the highest-risk vendors and explain why they are classified as high risk.",
        "files": ["vendor_risk_register.xlsx"]
    },
    {
        "q": "Summarize all business continuity and disaster recovery strategies across the repository.",
        "files": ["business_continuity_plan.pptx", "Business Continuity Planning Policy", "Technology Disaster Recovery Procedure"]
    }
]

import time

async def run():
    results = []
    for idx, item in enumerate(queries):
        print(f"Running Query {idx+1}...")
        
        # 1. Retrieve chunks
        retrieval_res = retrieve_chunks(item["q"], selected_files=item["files"])
        context = "\n\n---\n\n".join(retrieval_res["documents"])
        
        # 2. Generate answer with retry for 429
        answer = None
        for attempt in range(5):
            try:
                answer = generate_answer(item["q"], context)
                break
            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit on query {idx+1}, sleeping 60s...")
                    time.sleep(60)
                else:
                    raise e
                    
        # Simulate endpoint dynamic suggestion logic
        suggested_questions = []
        if item["files"]:
            file_str = " ".join(item["files"]).lower()
            if "risk" in file_str or "register" in file_str:
                suggested_questions.extend(["Show high-risk vendors", "Summarize vendor risks"])
            if "security" in file_str:
                suggested_questions.extend(["Summarize security controls", "Show MFA requirements"])
            if "continuity" in file_str or "disaster" in file_str or "recovery" in file_str:
                suggested_questions.extend(["Summarize recovery strategies", "Show continuity testing requirements"])
            if len(item["files"]) > 1:
                suggested_questions.extend(["Summarize access controls", "Compare incident response obligations"])
        
        if not suggested_questions:
            suggested_questions = [
                "What are the primary compliance risks identified?",
                "Summarize the key takeaways from these documents.",
                "What actions are required for compliance?"
            ]
        
        results.append({
            "question": item["q"],
            "answer": answer,
            "sources_used": list(set([m.get("filename") for m in retrieval_res["metadata"] if m])),
            "chunks_retrieved": len(retrieval_res["documents"]),
            "retrieval_diagnostics": retrieval_res.get("retrieval_mode", "unknown"),
            "suggested_questions": list(set(suggested_questions))[:4]
        })
        time.sleep(15) # Standard delay to prevent 429s on next query
        
    with open("scratch/baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Baseline capture complete.")

if __name__ == "__main__":
    asyncio.run(run())
