#!/usr/bin/env python3
"""
Complete system test for prescription image upload and text extraction
"""
import sys
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
import pytest

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))


def test_imports():
    """Test all required imports"""
    print("🔍 Testing Required Imports...")

    try:
        import streamlit as st

        print("   ✅ Streamlit imported successfully")
    except ImportError as e:
        print(f"   ❌ Streamlit import failed: {e}")
        return False

    try:
        import pytesseract

        print("   ✅ pytesseract imported successfully")
    except ImportError as e:
        print(f"   ❌ pytesseract import failed: {e}")
        return False

    try:
        from PIL import Image

        print("   ✅ PIL imported successfully")
    except ImportError as e:
        print(f"   ❌ PIL import failed: {e}")
        return False

    try:
        import pandas as pd

        print("   ✅ pandas imported successfully")
    except ImportError as e:
        print(f"   ❌ pandas import failed: {e}")
        return False

    return True


def test_ocr_system():
    """Test OCR system functionality"""
    print("\n🔍 Testing OCR System...")

    try:
        from streamlit_app import (
            find_tesseract_executable,
            TESSERACT_AVAILABLE,
            EASYOCR_AVAILABLE,
            extract_text_from_image,
        )

        print(f"   📊 Tesseract Available: {TESSERACT_AVAILABLE}")
        print(f"   📊 EasyOCR Available: {EASYOCR_AVAILABLE}")

        tesseract_path = find_tesseract_executable()
        print(f"   📂 Tesseract Path: {tesseract_path or 'Not found'}")

        if tesseract_path:
            print("   ✅ OCR system is ready")
            return True
        else:
            print("   ⚠️  Tesseract not found - will show setup instructions")
            return False

    except Exception as e:
        print(f"   ❌ OCR system test failed: {e}")
        return False


def create_test_prescription():
    """Create a test prescription image"""
    print("\n📝 Creating Test Prescription Image...")

    try:
        # Create a prescription image
        width, height = 600, 500
        image = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(image)

        # Use default font
        try:
            font = ImageFont.truetype("arial.ttf", 18)
            title_font = ImageFont.truetype("arial.ttf", 22)
        except:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()

        # Draw prescription content
        y = 30

        # Header
        draw.text((50, y), "MEDICAL PRESCRIPTION", font=title_font, fill="black")
        y += 50

        # Doctor info
        draw.text((50, y), "Dr. Sarah Johnson, MD", font=font, fill="black")
        y += 25
        draw.text((50, y), "Family Medicine Clinic", font=font, fill="black")
        y += 25
        draw.text((50, y), "License: MD123456", font=font, fill="black")
        y += 40

        # Patient info
        draw.text((50, y), "Patient: John Smith", font=font, fill="black")
        y += 25
        draw.text((50, y), "DOB: 03/15/1985", font=font, fill="black")
        y += 25
        draw.text((50, y), "Address: 123 Main St, City, State", font=font, fill="black")
        y += 40

        # Prescription
        draw.text((50, y), "Rx:", font=title_font, fill="black")
        y += 35
        draw.text((70, y), "Amoxicillin 500mg", font=font, fill="black")
        y += 25
        draw.text((70, y), "Take 1 capsule three times daily", font=font, fill="black")
        y += 25
        draw.text((70, y), "with food for 10 days", font=font, fill="black")
        y += 30
        draw.text((70, y), "Quantity: 30 capsules", font=font, fill="black")
        y += 25
        draw.text((70, y), "Refills: 0", font=font, fill="black")
        y += 40

        # Footer
        draw.text((50, y), "Date: August 13, 2025", font=font, fill="black")
        y += 25
        draw.text(
            (50, y), "Prescriber Signature: Dr. S. Johnson", font=font, fill="black"
        )
        y += 25
        draw.text((50, y), "DEA#: BJ1234567", font=font, fill="black")

        # Save the image
        image.save("test_prescription.png")
        print("   ✅ Test prescription image created: test_prescription.png")

        return image

    except Exception as e:
        print(f"   ❌ Failed to create test prescription: {e}")
        return None


@pytest.fixture
def image():
    """Fixture that creates and returns a test prescription image"""
    return create_test_prescription()


def test_ocr_extraction(image):
    """Test OCR text extraction"""
    print("\n🔍 Testing OCR Text Extraction...")

    try:
        # Mock streamlit for testing
        class MockStreamlit:
            def info(self, msg):
                print(f"      ℹ️  {msg}")

            def success(self, msg):
                print(f"      ✅ {msg}")

            def warning(self, msg):
                print(f"      ⚠️  {msg}")

            def error(self, msg):
                print(f"      ❌ {msg}")

            def expander(self, title, expanded=False):
                return MockExpander()

            def markdown(self, text):
                pass

            def code(self, text):
                pass

        class MockExpander:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def markdown(self, text):
                pass

            def code(self, text):
                pass

        # Import and test extraction
        from streamlit_app import extract_text_from_image
        import streamlit_app

        # Temporarily replace streamlit
        original_st = streamlit_app.st
        streamlit_app.st = MockStreamlit()

        try:
            extracted_text = extract_text_from_image(image)

            if extracted_text and len(extracted_text.strip()) > 0:
                print("   ✅ OCR extraction successful!")
                print("   📄 Extracted Text:")
                print("   " + "-" * 50)
                for line in extracted_text.split("\n")[:10]:  # Show first 10 lines
                    if line.strip():
                        print(f"   {line.strip()}")
                print("   " + "-" * 50)

                # Check for key elements
                text_lower = extracted_text.lower()
                elements_found = []

                if any(
                    word in text_lower for word in ["prescription", "medical", "rx"]
                ):
                    elements_found.append("Prescription header")
                if any(word in text_lower for word in ["dr.", "doctor", "md"]):
                    elements_found.append("Doctor information")
                if "patient" in text_lower:
                    elements_found.append("Patient information")
                if any(word in text_lower for word in ["amoxicillin", "mg", "capsule"]):
                    elements_found.append("Medication details")
                if any(word in text_lower for word in ["take", "daily", "times"]):
                    elements_found.append("Dosage instructions")
                if any(word in text_lower for word in ["quantity", "refill"]):
                    elements_found.append("Quantity/Refills")

                print(f"   📋 Key Elements Detected ({len(elements_found)}):")
                for element in elements_found:
                    print(f"      ✅ {element}")

                return len(elements_found) >= 3

            else:
                print("   ⚠️  No text extracted")
                return False

        finally:
            streamlit_app.st = original_st

    except Exception as e:
        print(f"   ❌ OCR extraction test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_streamlit_app():
    """Test Streamlit app functionality"""
    print("\n🔍 Testing Streamlit App...")

    try:
        # Test app import
        import streamlit_app

        print("   ✅ streamlit_app.py imports successfully")

        # Test main function exists
        if hasattr(streamlit_app, "main"):
            print("   ✅ main() function found")
        else:
            print("   ❌ main() function not found")
            return False

        # Test key functions exist
        required_functions = [
            "extract_text_from_image",
            "find_tesseract_executable",
            "analyze_prescription",
        ]

        for func_name in required_functions:
            if hasattr(streamlit_app, func_name):
                print(f"   ✅ {func_name}() function found")
            else:
                print(f"   ❌ {func_name}() function not found")
                return False

        return True

    except Exception as e:
        print(f"   ❌ Streamlit app test failed: {e}")
        return False


def run_complete_test():
    """Run complete system test"""
    print("🧪 COMPLETE PRESCRIPTION IMAGE EXTRACTION SYSTEM TEST")
    print("=" * 70)

    # Test 1: Imports
    imports_ok = test_imports()

    # Test 2: OCR System
    ocr_ok = test_ocr_system()

    # Test 3: Streamlit App
    app_ok = test_streamlit_app()

    # Test 4: Create test prescription
    test_image = create_test_prescription()

    # Test 5: OCR Extraction
    extraction_ok = False
    if test_image and ocr_ok:
        extraction_ok = test_ocr_extraction(test_image)

    # Results Summary
    print("\n" + "=" * 70)
    print("🎯 SYSTEM TEST RESULTS")
    print("=" * 70)

    print(f"✅ Required Imports: {'PASS' if imports_ok else 'FAIL'}")
    print(f"✅ OCR System: {'PASS' if ocr_ok else 'FAIL'}")
    print(f"✅ Streamlit App: {'PASS' if app_ok else 'FAIL'}")
    print(f"✅ Test Image Creation: {'PASS' if test_image else 'FAIL'}")
    print(f"✅ OCR Text Extraction: {'PASS' if extraction_ok else 'FAIL'}")

    overall_status = all(
        [imports_ok, ocr_ok, app_ok, test_image is not None, extraction_ok]
    )

    print(
        f"\n🎉 OVERALL STATUS: {'✅ FULLY WORKING' if overall_status else '❌ NEEDS ATTENTION'}"
    )

    if overall_status:
        print("\n🚀 SYSTEM IS READY FOR USE!")
        print("   ✅ All components are working")
        print("   ✅ OCR text extraction is functional")
        print("   ✅ Prescription images can be processed")
        print("   ✅ Users can upload images and get text")

        print("\n📋 HOW TO USE:")
        print("   1. Run: streamlit run streamlit_app.py")
        print("   2. Open: http://localhost:8501")
        print("   3. Click: 'Image Upload (OCR)' tab")
        print("   4. Upload: A prescription image")
        print("   5. Watch: Automatic text extraction!")

    else:
        print("\n⚠️  SYSTEM NEEDS ATTENTION:")
        if not imports_ok:
            print("   - Install missing Python packages")
        if not ocr_ok:
            print("   - Install Tesseract OCR")
        if not app_ok:
            print("   - Fix Streamlit app issues")
        if not extraction_ok:
            print("   - Debug OCR extraction")

    return overall_status


if __name__ == "__main__":
    run_complete_test()
