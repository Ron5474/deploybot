import requests
import re
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

from db.db import setup_db

load_dotenv()

URL = "https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md"
GITHUB_ACCESS_TOKEN = os.environ["GITHUB_ACCESS_TOKEN"]

# Regex to match a list entry line like:
# - [Name](url) - Description. ([Source Code](github_url)) `License` `Language`
ENTRY_RE = re.compile(
    r"^- \[(?P<name>[^\]]+)\]\((?P<url>[^)]+)\)"  # - [Name](url)
    r"\s*(?:(?:[:—-]|`[^`]+`)\s*)*"               # optional demo/decorators
    r"- (?P<description>[^.([`]+)"                 # - Description
    r".*?\[Source Code\]\((?P<source_url>[^)]+)\)" # ([Source Code](url))
    r".*?`(?P<license>[^`]+)`"                     # `License`
    r"(?:.*?`(?P<language>[^`]+)`)?"               # `Language` (optional)
)

def extract_owner_repo_from_url(url):
    url = url.rstrip("/")
    
    if not url.startswith("https://github.com/"):
        return None, None

    parts = urlparse(url).path.strip("/").split("/")

    if len(parts) < 2:
        return None, None # for github.com only

    owner, repo = parts[0], parts[1]
    return owner, repo
    

def extract_source_url_readme_and_save(source_url):
    owner, repo = extract_owner_repo_from_url(source_url)
    
    if not owner or not repo:
        return None

    filename = repo.lower().replace(" ", "-")
    filepath = os.path.join("data/readme_cache", f"{filename}.md")
    
    if os.path.exists(filepath):
        return filepath

    api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {"Authorization": f"Bearer {GITHUB_ACCESS_TOKEN}"}
    api_response = requests.get(api_url, headers=headers)
    
    if api_response.status_code != 200:
        return None
    
    url_to_get_readme = api_response.json()["download_url"]
    readme_response = requests.get(url_to_get_readme, headers=headers)

    if readme_response.status_code != 200:
        return None
    
    readme_content = readme_response.text

    
    os.makedirs("data/readme_cache", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(readme_content)

    return filepath

def extract_app_info(match, category):
    name = match.group("name")
    url = match.group("url")
    description = match.group("description")
    source_url = match.group("source_url")
    license_ = match.group("license")
    language = match.group("language")
    if source_url:
        extract_source_url_readme_and_save(source_url)
    
    kvs = {
            "name": name,
            "category": category,
            "url": url,
            "description": description,
            "source_url": source_url,
            "license": license_,
            "language": language if language else None
           }
    return kvs

def fetch_page():
    page = requests.get(URL)

    if page.status_code != 200:
        print("Unable to fetch")
        return []

    current_category = None
    apps_data = []

    for line in page.text.splitlines():
        # Track Category of App
        if line.startswith("## "):
            current_category = line[3:].strip()
            continue
        
        match = ENTRY_RE.match(line)
        if match:
            data = extract_app_info(match, current_category)
            apps_data.append(data)

    return apps_data

def insert_data_to_db(apps_data):
    conn, cursor = setup_db()
    rows = [
            (
                app["name"],
                app["category"],
                app["description"],
                app["source_url"],
                None,
                app["license"],
                app["language"]
            )
            for app in apps_data
    ]
    cursor.executemany(
            "INSERT OR IGNORE INTO apps (name, category, description, github_url, docker_image, license, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows
    )
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM apps")
    print(f"Inserted {cursor.fetchone()[0]} rows")
    conn.close()


insertion_data = fetch_page()
insert_data_to_db(insertion_data)

