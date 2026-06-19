import sys
import os
from dotenv import load_dotenv

backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))
sys.path.append(backend_dir)

from app.services.compliance_service import generate_compliance_report
from app.services.retrieval import get_all_chunks_for_files

print('Testing Report Generation with Real Gemini API Key...')
try:
    report = generate_compliance_report(selected_files=None, pre_retrieved_chunks=['This is a test regulation chunk about password lengths.'])
    print('Test passed! Report generated.')
    print('Report preview:')
    print(report)
except Exception as e:
    print('Test failed with error:', e)
