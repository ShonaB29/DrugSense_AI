#!/usr/bin/env python3
"""
Demo script to test the Prescription Authenticator AI API
"""
import requests
import json
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def get_access_token():
    """Get access token for API calls"""
    print("🔐 Getting access token...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/token",
            auth=("clinician1", "secret"),
            timeout=10
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"✅ Token obtained: {token[:20]}...")
            return token
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def test_prescription_analysis(token):
    """Test prescription analysis endpoint"""
    print("💊 Testing prescription analysis...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test data
    prescription_data = {
        "text": "Aspirin 100mg OD for 7 days and Ibuprofen 400mg BID for 5 days",
        "patient": {
            "age": 45,
            "weight_kg": 70.0,
            "allergies": ["penicillin"],
            "medical_conditions": ["hypertension"]
        },
        "include_alternatives": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/analyze",
            json=prescription_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analysis successful!")
            print(f"   📋 Extracted {len(data['extracted_medications'])} medications:")
            
            for med in data['extracted_medications']:
                print(f"      - {med['drug_name']} {med.get('strength', '')} {med.get('frequency', '')}")
                print(f"        Confidence: {med['confidence']:.1%}")
            
            print(f"   🔍 RxNorm mappings: {len(data['rxnorm_mappings'])}")
            for mapping in data['rxnorm_mappings'][:3]:  # Show first 3
                print(f"      - {mapping['name']} (RxCUI: {mapping['rxcui']})")
            
            print(f"   ⚠️  Safety alerts: {len(data['safety_alerts'])}")
            for alert in data['safety_alerts']:
                print(f"      - {alert['severity'].upper()}: {alert['message']}")
            
            print(f"   🔄 Drug interactions: {len(data['drug_interactions'])}")
            for interaction in data['drug_interactions']:
                print(f"      - {interaction['drug1']} + {interaction['drug2']}: {interaction['severity']}")
            
            print(f"   💡 Alternatives: {len(data['suggested_alternatives'])}")
            for alt in data['suggested_alternatives'][:2]:  # Show first 2
                print(f"      - {alt['drug_name']}: {alt['reason']}")
            
            print(f"   📊 Overall confidence: {data['analysis_confidence']:.1%}")
            
            return True
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return False

def test_rxnorm_lookup(token):
    """Test RxNorm lookup endpoint"""
    print("🔍 Testing RxNorm lookup...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/rxnorm/lookup?q=aspirin",
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ RxNorm lookup successful!")
            print(f"   Query: '{data['query']}'")
            print(f"   Found {data['total_results']} candidates:")
            
            for candidate in data['candidates'][:3]:  # Show first 3
                print(f"      - {candidate['name']} (RxCUI: {candidate['rxcui']}, Confidence: {candidate['confidence']:.1%})")
            
            return True
        else:
            print(f"❌ RxNorm lookup failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ RxNorm lookup error: {e}")
        return False

def main():
    """Run the API demo"""
    print("🏥 Prescription Authenticator AI - API Demo")
    print("=" * 50)
    
    # Test health check
    if not test_health_check():
        print("❌ Server is not running. Please start it with: python start_system.py")
        return
    
    print()
    
    # Get access token
    token = get_access_token()
    if not token:
        print("❌ Could not authenticate. Please check the server.")
        return
    
    print()
    
    # Test prescription analysis
    if test_prescription_analysis(token):
        print()
        
        # Test RxNorm lookup
        test_rxnorm_lookup(token)
    
    print("\n🎉 Demo completed!")
    print("\n💡 Try the full interface at: http://localhost:8501")
    print("📖 API Documentation: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
