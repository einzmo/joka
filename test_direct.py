# test_direct.py
import os
from dotenv import load_dotenv
load_dotenv()

print("Testing Cloudinary directly...")
print(f"Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
print(f"API Key: {os.getenv('CLOUDINARY_API_KEY')[:10]}...")

try:
    import cloudinary
    import cloudinary.uploader
    print("✅ Cloudinary imported successfully")
    
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True
    )
    print("✅ Cloudinary configured")
    
    # Test connection
    print("✅ Cloudinary is ready")
    
except Exception as e:
    print(f"❌ Error: {e}")