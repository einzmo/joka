



# test_upload.py - UPDATED with working URL
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv()

print("Testing Cloudinary...")
print(f"Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME')}")

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

print("✅ Cloudinary configured")

# Test with a different working video URL
test_urls = [
    "https://res.cloudinary.com/dtrz5zglt/video/upload/VID-20250709-WA0005_xpipsu.mp4"
]

for test_url in test_urls:
    try:
        print(f"\n📤 Testing upload from: {test_url[:50]}...")
        result = cloudinary.uploader.upload(
            test_url,
            upload_preset='mymsce_private',
            resource_type='video'
        )
        print(f"✅ Upload successful!")
        print(f"   Public ID: {result['public_id']}")
        
        # Clean up
        cloudinary.uploader.destroy(result['public_id'], resource_type='video')
        print("✅ Test video cleaned up")
        break
    except Exception as e:
        print(f"❌ Failed: {e}")
        continue