#!/usr/bin/env python3
"""
Movie Download Helper for Telegram Bot
Provides movie file handling and download capabilities
"""

import os
import requests
from typing import Dict, List, Optional

class MovieDownloader:
    """Handle movie downloads and file management"""
    
    def __init__(self):
        self.movie_directory = "movies"
        self.ensure_movie_directory()
    
    def ensure_movie_directory(self):
        """Create movies directory if it doesn't exist"""
        if not os.path.exists(self.movie_directory):
            os.makedirs(self.movie_directory)
    
    def get_sample_movies(self) -> List[Dict]:
        """Get list of sample movies with download info"""
        return [
            {
                "title": "Big Buck Bunny",
                "description": "Open source animated short film",
                "file_path": "big_buck_bunny_480p.mp4",
                "size": "64 MB",
                "duration": "10 min",
                "download_url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            },
            {
                "title": "Sintel",
                "description": "Open source fantasy short film",
                "file_path": "sintel_480p.mp4", 
                "size": "31 MB",
                "duration": "15 min",
                "download_url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4"
            },
            {
                "title": "Tears of Steel",
                "description": "Open source sci-fi short film",
                "file_path": "tears_of_steel_480p.mp4",
                "size": "45 MB", 
                "duration": "12 min",
                "download_url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4"
            }
        ]
    
    def download_movie(self, movie_info: Dict) -> Optional[str]:
        """Download a movie file"""
        try:
            file_path = os.path.join(self.movie_directory, movie_info["file_path"])
            
            # Check if file already exists
            if os.path.exists(file_path):
                return file_path
            
            # Download the file
            response = requests.get(movie_info["download_url"], stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return file_path
        except Exception as e:
            print(f"Error downloading movie: {e}")
            return None
    
    def get_movie_info(self, movie_name: str) -> Optional[Dict]:
        """Get movie info by name"""
        movies = self.get_sample_movies()
        
        for movie in movies:
            if movie_name.lower() in movie["title"].lower():
                return movie
        
        return None
    
    def send_movie_download_options(self, movie_name: str) -> str:
        """Generate download options message for a movie"""
        movie_info = self.get_movie_info(movie_name)
        
        if movie_info:
            return f"""
🎬 **{movie_info['title']}**

📝 **Tavsif:** {movie_info['description']}
📏 **Davomiyligi:** {movie_info['duration']}
💾 **Hajmi:** {movie_info['size']}

✅ **Bu kinoni to'g'ridan-to'g'ri yuklab olishingiz mumkin!**

Yuklab olish uchun "📥 Yuklab olish" tugmasini bosing.
"""
        else:
            return f"""
🎬 **{movie_name}** kinosi uchun qidiruv...

📱 **Telegram kanallar:**
• @MoviesChannelUz
• @KinoDownloadUz  
• @FilmCollectionUz

💾 **Fayl saqlash xizmatlari:**
• Google Drive
• Mega.nz
• MediaFire

🔍 **Qidiruv maslahatlar:**
• Kino nomini ingliz tilida ham sinab ko'ring
• Yil qo'shib qidiring (masalan: "{movie_name} 2023")
• HD, 1080p, 720p so'zlarini qo'shing

⚠️ **Eslatma:** Faqat ochiq manbali yoki egalik huquqi tugagan kinolarni yuklab oling.
"""

def get_movie_downloader():
    """Get movie downloader instance"""
    return MovieDownloader()