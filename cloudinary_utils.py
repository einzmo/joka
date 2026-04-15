# cloudinary_utils.py
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

class CloudinaryService:
    def __init__(self, app=None):
        self.available = True
    
    def clean_public_id(self, public_id):
        """Extract just the public ID without folder or extension"""
        if not public_id:
            return None
        
        # Remove folder path if present
        if '/' in public_id:
            public_id = public_id.split('/')[-1]
        
        # Remove extension if present
        if '.' in public_id:
            public_id = public_id.rsplit('.', 1)[0]
        
        return public_id
    
    def upload_file(self, file, file_type='auto', folder='mymsce_lessons'):
        temp_path = None
        try:
            temp_path = f"temp_{datetime.utcnow().timestamp()}"
            file.save(temp_path)
            
            if file_type == 'video':
                resource_type = 'video'
            elif file_type == 'audio':
                resource_type = 'video'
            else:
                resource_type = 'raw'
            
            result = cloudinary.uploader.upload(
                temp_path,
                resource_type=resource_type,
                folder=folder,
                use_filename=True,
                unique_filename=True
            )
            
            # Store clean public ID without folder path
            clean_id = self.clean_public_id(result['public_id'])
            
            return {
                'success': True,
                'public_id': clean_id,
                'url': result['secure_url'],
                'bytes': result.get('bytes', 0),
                'duration': result.get('duration', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
    
    def get_media_url(self, public_id, resource_type='video', expires_in=3600):
        """Get signed URL for any media type"""
        if not public_id:
            return {'success': False, 'error': 'No public ID'}
        
        # Clean the public ID
        clean_id = self.clean_public_id(public_id)
        
        try:
            timestamp = int((datetime.utcnow() + timedelta(seconds=expires_in)).timestamp())
            
            url, options = cloudinary_url(
                clean_id,
                resource_type=resource_type,
                type='private',
                sign_url=True,
                expires_at=timestamp,
                secure=True
            )
            return {'success': True, 'url': url}
        except Exception as e:
            # Try public URL as fallback
            try:
                url, options = cloudinary_url(
                    clean_id,
                    resource_type=resource_type,
                    secure=True
                )
                return {'success': True, 'url': url}
            except Exception as e2:
                return {'success': False, 'error': str(e2)}
            
    def get_actual_url(self, public_id, resource_type='video'):
        """Get the actual Cloudinary URL for any file"""
        try:
            # Get resource info from Cloudinary
            import cloudinary.api
            result = cloudinary.api.resource(public_id, resource_type=resource_type)
            return {
                'success': True,
                'url': result['secure_url']
            }
        except Exception as e:
            print(f"Error getting resource: {e}")
            # Fallback to constructing URL
            cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME', 'dtrz5zglt')
            if resource_type == 'raw':
                url = f"https://res.cloudinary.com/{cloud_name}/raw/upload/{public_id}"
            else:
                url = f"https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/{public_id}"
            return {'success': True, 'url': url}    
            
        
    def get_signed_video_url(self, public_id, expires_in=3600):
        """Get signed video URL from Cloudinary"""
        try:
            # Clean the public ID first
            clean_id = public_id
            if '/' in clean_id:
                clean_id = clean_id.split('/')[-1]
            if '.' in clean_id:
                clean_id = clean_id.rsplit('.', 1)[0]
            
            # Generate signed URL
            timestamp = int((datetime.utcnow() + timedelta(seconds=expires_in)).timestamp())
            
            url, options = cloudinary_url(
                clean_id,
                resource_type='video',
                type='private',
                sign_url=True,
                expires_at=timestamp,
                secure=True
            )
            
            print(f"🔗 Generated URL for {clean_id}: {url}")
            return {'success': True, 'url': url}
        except Exception as e:
            print(f"❌ Signed URL error: {e}")
            # Fallback to public URL
            cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME', 'dtrz5zglt')
            url = f"https://res.cloudinary.com/{cloud_name}/video/upload/{clean_id}.mp4"
            print(f"🔗 Fallback URL: {url}")
            return {'success': True, 'url': url}