import os
import urllib.parse
import random
import string
import http.client
import sys
import re
from urllib.parse import urlparse

def fix_relative_links(html_content, base_dir):
    def replace_href(match):
        quote = match.group(1)
        url = match.group(2)
        if url.startswith(("http://", "https://", "/", "#", "mailto:")):
            return f'href={quote}{url}{quote}'
        else:
            new_url = os.path.normpath(os.path.join(base_dir, url))
            # Normalize path separators for Windows (convert backslashes to forward slashes for HTML)
            new_url = new_url.replace(os.sep, "/")
            return f'href={quote}{new_url}{quote}'
    
    pattern = r'href=(["\'])(.*?)\1'
    return re.sub(pattern, replace_href, html_content)

# Get web address or search query
http_url = input("https address > ").strip()

# --- RECURSIVE LOCAL DATABASE INTERCEPTOR FOR '@' ---
if http_url.startswith("@"):
    query = http_url[1:].lower()
    local_docs_dir = "local"
    os.makedirs(local_docs_dir, exist_ok=True)
    
    matching_results = []
    if os.path.exists(local_docs_dir):
        for root, dirs, files in os.walk(local_docs_dir):
            for filename in files:
                if filename.endswith(".html"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Normalize path separators for cross-platform path matching
                            norm_filepath = filepath.replace(os.sep, "/").lower()
                            
                            # Check if query matches the path, filename, or content
                            if query in norm_filepath or query in filename.lower() or query in content.lower():
                                matching_results.append(filepath)
                    except Exception:
                        pass

    html_output = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>Search: @{query}</title>
    </head>
    <body>
        <center>
            <h1>Local Search Results for: @{query}</h1>
        </center>
        <p>Found {len(matching_results)} matching local page(s):</p>
        <hr>
    """
    
    if matching_results:
        for path_to_file in matching_results:
            display_name = os.path.basename(path_to_file)
            # Fix slash format for Windows links
            href_path = path_to_file.replace(os.sep, "/")
            html_output += f'<p><a href="{href_path}">{display_name} ({href_path})</a></p>\n'
    else:
        html_output += "<p>No matching local documents found.</p>"
        
    html_output += """
        <br>
        <center>
            <a href="home.html">Back to Home</a>
        </center>
    </body>
    </html>
    """

    with open("cache.html", "w", encoding="utf-8") as cache_file:
        cache_file.write(html_output)
        
    print(f"Generated recursive local search results for '@{query}'")
    sys.exit(0)

# --- LOCAL FILE HANDLING WITH RELATIVE PATH FIXER ---
if not http_url.startswith(("http://", "https://")) or os.path.exists(http_url):
    local_path = http_url
    if os.path.exists(local_path):
        base_dir = os.path.dirname(local_path)
        with open(local_path, "r", encoding="utf-8") as f:
            local_content = f.read()
        
        if base_dir:
            local_content = fix_relative_links(local_content, base_dir)

        with open("cache.html", "w", encoding="utf-8") as f:
            f.write(local_content)
        print(f"Loaded local file: {local_path}")
    else:
        print(f"Error: Local file '{local_path}' not found.")
    sys.exit(0)

# --- WEB DOWNLOADING LOGIC ---
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

parsed_url = urlparse(http_url)
path = parsed_url.path
base_name = os.path.basename(path)

file_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.tar', '.gz', '.mp3', '.mp4', '.txt', '.webp')

is_file = False
if base_name.lower().endswith(file_extensions):
    is_file = True

if not is_file:
    try:
        conn = http.client.HTTPSConnection(parsed_url.netloc, timeout=5) if parsed_url.scheme == 'https' else http.client.HTTPConnection(parsed_url.netloc, timeout=5)
        conn.request("HEAD", parsed_url.path if parsed_url.path else "/", headers={"User-Agent": user_agent})
        res = conn.getresponse()
        content_type = res.getheader("Content-Type", "").lower()
        
        if "text/html" not in content_type and content_type != "":
            is_file = True
    except Exception:
        if any(ext in http_url.lower() for ext in file_extensions):
            is_file = True

if not is_file:
    # Use cross-platform Python file removal instead of Linux 'rm'
    if os.path.exists("cache.html"):
        os.remove("cache.html")

    os.system(f"curl -s -L -A '{user_agent}' '{http_url}' -o cache.html")
    print("Downloaded webpage to cache.html")
else:
    os.makedirs("downloads", exist_ok=True)

    if base_name and '.' in base_name:
        save_filename = base_name
    else:
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
