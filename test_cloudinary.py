# test_cloudinary.py
import os
from dotenv import load_dotenv

load_dotenv()

print("Testing Cloudinary Setup...")
print("=" * 50)

# Test 1: Check imports
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    from cloudinary.utils import cloudinary_url
    print("✅ Cloudinary packages imported successfully")
    print(f"   Package location: {cloudinary.__file__}")
except ImportError as e:
    print(f"❌ Failed to import Cloudinary: {e}")
    exit(1)

# Test 2: Check credentials
cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
api_key = os.getenv('CLOUDINARY_API_KEY')
api_secret = os.getenv('CLOUDINARY_API_SECRET')

if not all([cloud_name, api_key, api_secret]):
    print("\n⚠️ Missing Cloudinary credentials in .env")
    print("\nTo use Cloudinary, add these to your .env file:")
    print("CLOUDINARY_CLOUD_NAME=your_cloud_name")
    print("CLOUDINARY_API_KEY=your_api_key")
    print("CLOUDINARY_API_SECRET=your_api_secret")
    print("\nGet them from: https://cloudinary.com/console")
    print("\nFor now, the app will run without Cloudinary features.")
else:
    print("✅ Cloudinary credentials found")
    print(f"   Cloud Name: {cloud_name}")
    print(f"   API Key: {api_key[:8]}...")
    
    # Test 3: Configure and test connection
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )
    print("✅ Cloudinary configured successfully")
    
    # Test 4: Try to list existing resources (optional)
    try:
        result = cloudinary.api.resources(resource_type='video', max_results=1)
        print("✅ Cloudinary API connection successful")
        print(f"   Found {result.get('total_count', 0)} videos in library")
    except Exception as e:
        print(f"⚠️ Could not list resources: {str(e)[:100]}")

print("\n" + "=" * 50)