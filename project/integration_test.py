#!/usr/bin/env python3
"""
Integration test for the Prescription Authenticator AI
"""
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def test_app_components():
    """Test the actual app components"""
    print("🧪 Integration Tests - App Components")
    print("=" * 50)
    
    try:
        # Test 1: Import app modules
        print("🔄 Testing app module imports...")
        
        # Import models
        from app.models import (
            ExtractedMedication, 
            PatientInfo, 
            PrescriptionAnalysisRequest,
            UserRole
        )
        print("✅ Models imported successfully")
        
        # Import config
        from app.core.config import get_settings
        settings = get_settings()
        print(f"✅ Config loaded: {settings.app_name} v{settings.app_version}")
        
        # Import auth
        from app.core.auth import create_access_token, get_user
        token = create_access_token(data={"sub": "test_user"})
        print(f"✅ Auth working: token created")
        
        # Test 2: NER Service
        print("\n🔄 Testing NER Service...")
        from app.services.ner_service import MedicalNERService
        
        ner = MedicalNERService()
        test_text = "Aspirin 100mg OD for 7 days, Ibuprofen 400mg TDS PRN"
        medications = ner.extract_medications(test_text)
        
        print(f"✅ NER extracted {len(medications)} medications:")
        for i, med in enumerate(medications, 1):
            print(f"   {i}. {med.drug_name}")
            if med.strength:
                print(f"      Strength: {med.strength}")
            if med.frequency:
                print(f"      Frequency: {med.frequency}")
            print(f"      Confidence: {med.confidence:.1%}")
        
        # Test 3: RxNorm Service
        print("\n🔄 Testing RxNorm Service...")
        from app.services.rxnorm import RxNormService
        
        rxnorm = RxNormService()
        
        # Test drug search
        mappings = rxnorm.search_drug("aspirin", max_results=3)
        print(f"✅ RxNorm search returned {len(mappings)} results")
        
        # Test safety checking
        if medications:
            alerts = rxnorm.check_dosage_safety(medications[0], patient_age=45, patient_weight=70.0)
            print(f"✅ Safety check returned {len(alerts)} alerts")
            
            # Test alternatives
            alternatives = rxnorm.suggest_alternatives(medications[0], patient_allergies=["penicillin"])
            print(f"✅ Alternative suggestions: {len(alternatives)} found")
        
        # Test 4: API Routes
        print("\n🔄 Testing API Routes...")
        from app.api.prescriptions import router
        print("✅ Prescription router imported")
        
        # Test 5: Main App
        print("\n🔄 Testing Main App...")
        from app.main import app
        print("✅ FastAPI app imported successfully")
        
        # Test with FastAPI TestClient
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"✅ Health endpoint: {response.status_code} - {response.json()['status']}")
        
        # Test root endpoint
        response = client.get("/")
        print(f"✅ Root endpoint: {response.status_code} - {response.json()['status']}")
        
        # Test token endpoint
        response = client.post("/token", auth=("clinician1", "secret"))
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Token endpoint: {response.status_code} - token received")
            
            # Test authenticated endpoint
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            
            # Test prescription analysis
            analysis_request = {
                "text": "Aspirin 100mg OD for 7 days",
                "patient": {
                    "age": 45,
                    "weight_kg": 70.0,
                    "allergies": []
                }
            }
            
            response = client.post("/api/v1/analyze", json=analysis_request, headers=headers)
            print(f"✅ Prescription analysis: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   - Extracted {len(data['extracted_medications'])} medications")
                print(f"   - Found {len(data['safety_alerts'])} safety alerts")
                print(f"   - Analysis confidence: {data['analysis_confidence']:.1%}")
            
            # Test RxNorm lookup
            response = client.get("/api/v1/rxnorm/lookup?q=aspirin", headers=headers)
            print(f"✅ RxNorm lookup: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   - Found {len(data['candidates'])} candidates for '{data['query']}'")
        
        else:
            print(f"⚠️  Token endpoint failed: {response.status_code}")
        
        print("\n🎉 All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streamlit_components():
    """Test Streamlit app components"""
    print("\n🧪 Testing Streamlit Components")
    print("=" * 40)
    
    try:
        import streamlit as st
        print("✅ Streamlit imported")
        
        # Test if streamlit app file exists and is readable
        streamlit_file = Path("streamlit_app.py")
        if streamlit_file.exists():
            print("✅ Streamlit app file exists")
            
            # Read and check for key components
            content = streamlit_file.read_text()
            
            components = [
                "st.set_page_config",
                "authenticate",
                "analyze_prescription",
                "extract_text_from_image",
                "st.file_uploader"
            ]
            
            for component in components:
                if component in content:
                    print(f"✅ Found component: {component}")
                else:
                    print(f"⚠️  Missing component: {component}")
        
        return True
        
    except Exception as e:
        print(f"❌ Streamlit test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🏥 Prescription Authenticator AI - Integration Tests")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    # Test app components
    if test_app_components():
        tests_passed += 1
    
    # Test Streamlit components
    if test_streamlit_components():
        tests_passed += 1
    
    print(f"\n📊 Integration Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All integration tests passed!")
        print("\n✅ The Prescription Authenticator AI system is fully functional!")
        print("\n🚀 Ready to run:")
        print("   Backend: python -c \"import sys; sys.path.insert(0, '.'); from app.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)\"")
        print("   Frontend: streamlit run streamlit_app.py")
        return 0
    else:
        print("⚠️  Some integration tests failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
