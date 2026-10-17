import os
import urllib.parse
import random
import string
import http.client
from urllib.parse import urlparse

if os.name == "nt":
    print("not made for windows")
else:
    # Get web address
    http_url = input("https address > ").strip()

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Inspect the URL path to determine if it's likely a file or a webpage
    parsed_url = urlparse(http_url)
    path = parsed_url.path
    base_name = os.path.basename(path)

    # Check file extension or URL patterns
    file_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.tar', '.gz', '.mp3', '.mp4', '.txt', '.webp')
    
    is_file = False
    if base_name.lower().endswith(file_extensions):
        is_file = True

    if not is_file:
        # Check headers via HTTP HEAD/GET request to see the Content-Type
        try:
            conn = http.client.HTTPSConnection(parsed_url.netloc, timeout=5) if parsed_url.scheme == 'https' else http.client.HTTPConnection(parsed_url.netloc, timeout=5)
            conn.request("HEAD", parsed_url.path if parsed_url.path else "/", headers={"User-Agent": user_agent})
            res = conn.getresponse()
            content_type = res.getheader("Content-Type", "").lower()
            
            # If it's not text/html, treat it as a downloadable file
            if "text/html" not in content_type and content_type != "":
                is_file = True
        except Exception:
            # Fallback if connection check fails
            if any(ext in http_url.lower() for ext in file_extensions):
                is_file = True

    if not is_file:
        # Handle as Webpage (cache.html)
        if os.path.exists("cache.html"):
            os.system("rm cache.html")

        os.system(f"curl -s -L -A '{user_agent}' '{http_url}' -o cache.html")
        print("Downloaded webpage to cache.html")
    else:
        # Handle as Downloadable File (/downloads/)
        os.makedirs("downloads", exist_ok=True)

        # Extract filename or generate random string with correct extension
        if base_name and '.' in base_name:
            save_filename = base_name
        else:
            # Try guessing extension from URL or default to .jpg
            ext = ".jpg"
            for ext_candidate in file_extensions:
                if ext_candidate in http_url.lower():
                    ext = ext_candidate
                    break
            
            rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            save_filename = f"{rand_str}{ext}"

        filepath = os.path.join("downloads", save_filename)
        
        print(f"Downloading file to {filepath}...")
        os.system(f"curl -s -L -A '{user_agent}' '{http_url}' -o '{filepath}'")
        print(f"Downloaded successfully: {filepath}")