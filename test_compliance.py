import sys
import os
from dotenv import load_dotenv

backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))
sys.path.append(backend_dir)

import app.services.compliance_service as cs

def mock_call_llm(prompt):
    if 'Merge and deduplicate' in prompt:
        return '{"violation": false, "issues": ["Mock issue"], "recommendations": ["Mock rec"], "structured_violations": []}'
    return '{"issues": ["Mock issue"], "recommendations": ["Mock rec"]}'

cs._call_llm = mock_call_llm

from app.services.compliance_service import generate_compliance_report
from app.services.retrieval import get_all_chunks_for_files

print('Testing A...')
files_a = ['2020_Annual_Report.docx', '2021_Annual_Report.docx', '2023_Annual_Report.docx', '2024_Annual_Report.docx']
res_a = get_all_chunks_for_files(files_a)
chunks_a = res_a['documents']
print('Test A chunks length:', len(chunks_a))
report_a = generate_compliance_report(selected_files=files_a, pre_retrieved_chunks=chunks_a)
print('Test A passed, report keys:', report_a.keys() if isinstance(report_a, dict) else 'Not a dict')

print('\nTesting B...')
files_b = ['Enterprise Security Policy', 'GDPR Framework']
res_b = get_all_chunks_for_files(files_b)
chunks_b = res_b['documents']
print('Test B chunks length:', len(chunks_b))
report_b = generate_compliance_report(selected_files=files_b, pre_retrieved_chunks=chunks_b)
print('Test B passed, report keys:', report_b.keys() if isinstance(report_b, dict) else 'Not a dict')

print('\nTesting C...')
report_c = generate_compliance_report(selected_files=None, pre_retrieved_chunks=None)
print('Test C passed, report keys:', report_c.keys() if isinstance(report_c, dict) else 'Not a dict')

print('\nAll tests completed successfully.')
