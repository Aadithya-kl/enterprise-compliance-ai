import sys
import os
import traceback
from dotenv import load_dotenv

backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))
sys.path.append(backend_dir)

from app.api.v1.compliance import assess_compliance_risk
from app.schemas.document import ComplianceReportRequest

class MockUser:
    id = "mock"

try:
    req = ComplianceReportRequest(selected_files=["Enterprise Security Policy"])
    res = assess_compliance_risk(req, current_user=MockUser())
    print("Risk:", res)
except Exception as e:
    print(traceback.format_exc())
