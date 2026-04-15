# test_cloudinary_import.py
try:
    import cloudinary
    import cloudinary.uploader
    print("✅ cloudinary imported successfully")
    print(f"Version: {cloudinary.__version__ if hasattr(cloudinary, '__version__') else 'unknown'}")
except Exception as e:
    print(f"❌ Error: {e}")