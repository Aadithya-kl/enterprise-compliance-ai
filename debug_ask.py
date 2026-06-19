import sys
import os
import traceback
import asyncio
from dotenv import load_dotenv

backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))
sys.path.append(backend_dir)

from app.api.v1.documents import ask_question
from app.schemas.document import QuestionRequest

try:
    req = QuestionRequest(question="What is the policy?", selected_files=["Enterprise Security Policy"])
    class MockUser:
        id = "mock"
    ask_question(req, current_user=MockUser())
except Exception as e:
    print(traceback.format_exc())
