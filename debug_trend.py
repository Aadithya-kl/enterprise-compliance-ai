import sys
import os
import traceback
from dotenv import load_dotenv

backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))
sys.path.append(backend_dir)

from app.db.session import SessionLocal
from app.services.analytics_service import generate_ai_trend_summary

try:
    db = SessionLocal()
    summary = generate_ai_trend_summary(db)
    print("Success:", summary)
except Exception as e:
    print(traceback.format_exc())
