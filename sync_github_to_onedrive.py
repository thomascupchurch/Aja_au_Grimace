import requests
import os
import zipfile

# --- CONFIGURATION ---
GITHUB_REPO = "thomascupchurch/Aja_au_Grimace"
ONEDRIVE_FOLDER = r"\\app01\lsi\UT_App_Shared"  # Change to your shared folder path

def get_latest_release_zip_url():
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    resp = requests.get(api_url)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None, None
    # Sort releases by published date (descending)
    sorted_releases = sorted(
        [r for r in data if r.get("published_at")],
        key=lambda r: r["published_at"],
        reverse=True
    )
    for release in sorted_releases:
        for asset in release.get("assets", []):
            if asset["name"].endswith(".zip"):
                return asset["browser_download_url"], asset["name"]
    return None, None

def download_zip(url, dest_path):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

def extract_zip(zip_path, target_folder):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(target_folder)

def main():
    print("Checking for latest release...")
    zip_url, zip_name = get_latest_release_zip_url()
    if not zip_url:
        print("No release zip found.")
        return
    local_zip = os.path.join(ONEDRIVE_FOLDER, zip_name)
    print(f"Downloading {zip_name}...")
    download_zip(zip_url, local_zip)
    print("Extracting to OneDrive folder...")
    extract_zip(local_zip, ONEDRIVE_FOLDER)
    print("Update complete.")

if __name__ == "__main__":
    main()