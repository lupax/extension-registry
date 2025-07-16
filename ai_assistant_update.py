import json
import sys
import argparse
import requests
import subprocess
import os

# This script automates the creation of a new extension entry, fixes it, updates asset IDs, and fixes hashes.
# Usage: python update_extension.py --version 0.9.4 --release_name v0.9.4_qtc17 --api_key YOUR_API_KEY --json_path registry/theqtcompany.aiassistant/extension.json --lua_path ~/repos/QtAIAssistant/plugin/ai_assistant/ai_assistant.lua

def main():
    parser = argparse.ArgumentParser(description="Automate new extension entry creation, update asset IDs from GitHub releases, and fix hashes.")
    parser.add_argument('--version', required=True, help='The version to add/update, e.g., 0.9.4')
    parser.add_argument('--release_name', required=True, help='The GitHub release name, e.g., v0.9.4_qtc17')
    parser.add_argument('--api_key', required=True, help='GitHub API key (Bearer token)')
    parser.add_argument('--json_path', required=True, help='Path to the extension.json file')
    parser.add_argument('--lua_path', required=True, help='Path to the ai_assistant.lua file')

    args = parser.parse_args()

    # Step 1: Run new.js to create new entry
    print("Running new.js to create new entry...")
    try:
        result = subprocess.run(['node', 'scripts/new.js', args.json_path, args.lua_path], capture_output=True, text=True, check=True)
        print(f"new.js output: {result.stdout}")
        if result.stderr:
            print(f"new.js stderr: {result.stderr}")
        print("New entry created.")
    except subprocess.CalledProcessError as e:
        print(f"Error running new.js: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

    with open(args.json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if args.version not in data['versions']:
        print(f"Version '{args.version}' not found after running new.js.")
        sys.exit(1)

    # Step 2: Fix the new entry - remove hooks and add sources template
    version_data = data['versions'][args.version]
    if 'hooks' in version_data['metadata']:
        del version_data['metadata']['hooks']
        print("Removed 'hooks' from metadata.")

    sources_template = [
        {
            "url": "https://qtccache.qt.io/QtAIAssistant/Asset?assetId=",
            "platform": {
                "name": "Windows",
                "architecture": "x86_64"
            },
            "sha256": ""
        },
        {
            "url": "https://qtccache.qt.io/QtAIAssistant/Asset?assetId=",
            "platform": {
                "name": "Windows",
                "architecture": "arm64"
            },
            "sha256": ""
        },
        {
            "url": "https://qtccache.qt.io/QtAIAssistant/Asset?assetId=",
            "platform": {
                "name": "Linux",
                "architecture": "x86_64"
            },
            "sha256": ""
        },
        {
            "url": "https://qtccache.qt.io/QtAIAssistant/Asset?assetId=",
            "platform": {
                "name": "Linux",
                "architecture": "arm64"
            },
            "sha256": ""
        },
        {
            "url": "https://qtccache.qt.io/QtAIAssistant/Asset?assetId=",
            "platform": {
                "name": "macOS",
                "architecture": "x86_64"
            },
            "sha256": ""
        },
        {
            "url": "https://qtccache.qt.io/QtAIAssistant/Asset?assetId=",
            "platform": {
                "name": "macOS",
                "architecture": "arm64"
            },
            "sha256": ""
        }
    ]
    version_data['sources'] = sources_template
    print("Added sources template to the new version.")

    with open(args.json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Fixed new entry in {args.json_path}.")

    # Step 3: Fetch releases from GitHub API
    url = "https://api.github.com/repositories/845034355/releases"
    headers = {
        "Authorization": f"Bearer {args.api_key}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching releases: {response.status_code} - {response.text}")
        sys.exit(1)

    releases = response.json()

    # Find the specific release
    target_release = next((r for r in releases if r['name'] == args.release_name), None)
    if not target_release:
        print(f"Release '{args.release_name}' not found.")
        sys.exit(1)

    # Get assets: map name to id
    assets = {asset['name']: asset['id'] for asset in target_release['assets']}

    # Function to find asset ID by pattern (startswith)
    def find_asset_id(pattern):
        for name in assets:
            if name.startswith(pattern):
                return assets[name]
        return None

    # Update the sources for the given version, since now they are empty
    sources = data['versions'][args.version]['sources']
    updated = False
    for source in sources:
        if source['url'].endswith('assetId='):  # Should be true now
            platform = source['platform']['name']
            arch = source['platform']['architecture']
            
            pattern = None
            if platform == 'Windows':
                if arch == 'x86_64':
                    pattern = 'win-x64-'
                elif arch == 'arm64':
                    pattern = 'win-arm64-'
            elif platform == 'Linux':
                if arch == 'x86_64':
                    pattern = 'linux-x64-'
                elif arch == 'arm64':
                    pattern = 'linux-arm64-'
            elif platform == 'macOS':
                pattern = 'macos-universal-'
            
            if pattern:
                asset_id = find_asset_id(pattern)
                if asset_id:
                    source['url'] = f"https://qtccache.qt.io/QtAIAssistant/Asset?assetId={asset_id}"
                    updated = True
                else:
                    print(f"Warning: No matching asset found for pattern '{pattern}' (platform: {platform}, arch: {arch})")
            else:
                print(f"Warning: No pattern defined for platform: {platform}, arch: {arch}")

    if updated:
        with open(args.json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Updated asset IDs in {args.json_path}.")
    else:
        print("No asset IDs updated.")

    # Step 4: Run fixhashes.js
    print("Running fixhashes.js...")
    env = os.environ.copy()
    env['FORCE_COLOR'] = '1'
    try:
        result = subprocess.run(['node', 'scripts/fixhashes.js', args.json_path], capture_output=True, text=True, check=True, env=env)
        print(f"fixhashes.js output: {result.stdout}")
        if result.stderr:
            print(f"fixhashes.js stderr: {result.stderr}")
        print(f"Hashes fixed in {args.json_path}.")
    except subprocess.CalledProcessError as e:
        print(f"Error running fixhashes.js: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()

