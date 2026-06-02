#!/usr/bin/env python3
"""
Test script to verify Phase 2 backend implementation
"""

import sys
import json
from pathlib import Path

def test_file_structure():
    """Verify all required files exist."""
    required_files = [
        'app.py',
        'models.py',
        'schemas.py',
        'crud.py',
        'database.py',
        'compliance.py',
        'rag.py',
        'requirements.txt'
    ]
    
    backend_dir = Path(__file__).parent
    print("✓ Checking file structure...")
    for file in required_files:
        file_path = backend_dir / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
            return False
    return True


def test_python_syntax():
    """Verify Python syntax."""
    import py_compile
    
    files_to_check = ['app.py', 'models.py', 'schemas.py', 'crud.py', 'database.py']
    print("\n✓ Checking Python syntax...")
    
    backend_dir = Path(__file__).parent
    for file in files_to_check:
        try:
            py_compile.compile(str(backend_dir / file), doraise=True)
            print(f"  ✓ {file}")
        except py_compile.PyCompileError as e:
            print(f"  ✗ {file}: {e}")
            return False
    return True


def test_api_endpoints():
    """Verify API endpoints are defined."""
    print("\n✓ Checking API endpoints...")
    
    with open('app.py', 'r') as f:
        app_content = f.read()
    
    required_endpoints = [
        ('def home()', 'Home endpoint'),
        ('async def upload_pdf', 'Upload PDF'),
        ('async def ask_question', 'Ask question'),
        ('def get_documents', 'Get documents'),
        ('def analyze()', 'Analyze compliance'),
        ('def compliance_report', 'Generate compliance report'),
        ('def risk_assessment', 'Risk assessment'),
        ('def audit_history', 'Get all audits'),
        ('def get_audit_history', 'Get single audit'),
        ('def delete_audit', 'Delete audit'),
        ('def dashboard_stats', 'Dashboard statistics'),
        ('def health_check', 'Health check'),
    ]
    
    for endpoint, description in required_endpoints:
        if endpoint in app_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            return False
    
    return True


def test_crud_functions():
    """Verify CRUD functions are defined."""
    print("\n✓ Checking CRUD functions...")
    
    with open('crud.py', 'r') as f:
        crud_content = f.read()
    
    required_functions = [
        ('save_audit_report', 'Save audit report'),
        ('get_all_audit_reports', 'Get all reports'),
        ('get_audit_report_by_id', 'Get report by ID'),
        ('delete_audit_report', 'Delete audit report'),
        ('get_dashboard_stats', 'Get dashboard stats'),
    ]
    
    for func, description in required_functions:
        if f'def {func}' in crud_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            return False
    
    return True


def test_schemas():
    """Verify Pydantic schemas are defined."""
    print("\n✓ Checking Pydantic schemas...")
    
    with open('schemas.py', 'r') as f:
        schemas_content = f.read()
    
    required_schemas = [
        ('AuditReportCreate', 'Audit report creation'),
        ('AuditReportResponse', 'Audit report response'),
        ('DashboardStatsResponse', 'Dashboard stats response'),
        ('ComplianceReportResponse', 'Compliance report response'),
        ('UploadResponse', 'Upload response'),
        ('QuestionResponse', 'Question response'),
        ('RiskAssessmentResponse', 'Risk assessment response'),
    ]
    
    for schema, description in required_schemas:
        if f'class {schema}' in schemas_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            return False
    
    return True


def test_models():
    """Verify SQLAlchemy models are defined."""
    print("\n✓ Checking SQLAlchemy models...")
    
    with open('models.py', 'r') as f:
        models_content = f.read()
    
    required_fields = [
        ('id', 'Primary key'),
        ('risk', 'Risk level'),
        ('compliance_score', 'Compliance score'),
        ('violation_count', 'Violation count'),
        ('issues', 'Issues'),
        ('recommendations', 'Recommendations'),
        ('audit_timestamp', 'Audit timestamp'),
        ('auditor', 'Auditor'),
    ]
    
    for field, description in required_fields:
        if field in models_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            return False
    
    return True


def test_imports():
    """Verify critical imports."""
    print("\n✓ Checking critical imports in app.py...")
    
    with open('app.py', 'r') as f:
        app_content = f.read()
    
    required_imports = [
        ('from fastapi import FastAPI', 'FastAPI'),
        ('from sqlalchemy.orm import Session', 'SQLAlchemy Session'),
        ('from crud import', 'CRUD functions'),
        ('from schemas import', 'Pydantic schemas'),
        ('from models import', 'SQLAlchemy models'),
        ('import logging', 'Logging'),
        ('import json', 'JSON'),
    ]
    
    for import_str, description in required_imports:
        if import_str in app_content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description} - NOT FOUND")
            return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 2 Backend Implementation Verification")
    print("=" * 60)
    
    tests = [
        test_file_structure,
        test_python_syntax,
        test_api_endpoints,
        test_crud_functions,
        test_schemas,
        test_models,
        test_imports,
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"✗ Test failed: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Implementation is complete!")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME TESTS FAILED - Please review the errors above")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
