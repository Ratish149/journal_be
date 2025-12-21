import os
import sys
from io import BytesIO

import django
from PIL import Image

# Setup Django environment
sys.path.append(r"e:\Frontend practice\journal\backend\journal")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "journal.settings")
django.setup()

from core.ai_service import analyze_trade_images


def test_file_analysis():
    print("Testing AI analysis with local files...")

    # Create a small dummy image for testing
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # In Django, a FileField value in an instance is a FieldFile, which behaves like a file object
    # For testing, we can just pass the BytesIO object

    try:
        bias, analysis = analyze_trade_images(
            ltf_file=img_byte_arr, htf_file=img_byte_arr
        )
        print(f"Bias: {bias}")
        print(f"Analysis: {analysis}")
    except Exception as e:
        print(f"Analysis failed: {e}")


if __name__ == "__main__":
    test_file_analysis()
