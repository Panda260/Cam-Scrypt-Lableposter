import requests
import base64
import io
import os
from typing import Optional, List, Dict
from PIL import Image

JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "")
API_KEY = os.environ.get("API_KEY", "")
LIBRARY_ID = os.environ.get("LIBRARY_ID", "")  # Spezifische Library ID


def get_items_from_library() -> Optional[List[Dict]]:
    """
    Fetch ALL items from specific Jellyfin library (korrigierte Version)
    """
    headers = {'X-Emby-Token': API_KEY}
    url = f'{JELLYFIN_URL}/Items'

    # Korrigierte Parameter basierend auf getIDs.py
    params = {
        'ParentId': LIBRARY_ID,  # Library ID als ParentId Parameter!
        'Recursive': 'true',
        'IncludeItemTypes': 'Movie,Series,Season,Episode,BoxSet',  # Alle Item-Typen
        'Fields': 'Name,Id,Type',  # Minimal benötigte Felder
        'IsMissing': 'False',
        'SortBy': 'SortName',
        'SortOrder': 'Ascending'
    }

    try:
        response = requests.get(url, headers=headers,
                                params=params, timeout=30)
        response.raise_for_status()
        json_data = response.json()
        items = json_data.get('Items', [])
        print(f"✓ {len(items)} items found in library {LIBRARY_ID}")
        return items
    except requests.RequestException as e:
        print(f"Error fetching items from library: {e}")
        return None


def get_library_info() -> bool:
    """
    Get information about all libraries to verify our target library exists
    """
    headers = {'X-Emby-Token': API_KEY}
    # Korrekte URL für Libraries
    url = f'{JELLYFIN_URL}/Library/VirtualFolders'

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        libraries = response.json()

        print("Available Libraries:")
        print("-" * 50)

        target_found = False
        for library in libraries:
            lib_id = library.get('ItemId', 'Unknown')
            lib_name = library.get('Name', 'Unknown')
            lib_type = library.get('CollectionType', 'Unknown')

            print(f"Name: {lib_name}")
            print(f"Type: {lib_type}")
            print(f"ID: {lib_id}")

            if lib_id == LIBRARY_ID:
                print("★ TARGET LIBRARY FOUND ★")
                target_found = True

            print("-" * 30)

        if not target_found:
            print(
                f"⚠ Target library {LIBRARY_ID} not found in available libraries!")
            print("Please check the library ID.")

        return target_found

    except requests.RequestException as e:
        print(f"Error getting library info: {e}")
        return False


def download_item_image(item_id: str, image_type: str = "Primary") -> Optional[bytes]:
    """
    Download item image from Jellyfin
    """
    headers = {'X-Emby-Token': API_KEY}
    url = f'{JELLYFIN_URL}/Items/{item_id}/Images/{image_type}'

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"   ✗ Error downloading image for {item_id}: {e}")
        return None


def upload_image_to_jellyfin(item_id: str, image_data: bytes, image_type: str = "Primary") -> bool:
    """
    Upload image back to Jellyfin (Base64 encoded)
    """
    headers = {
        'X-Emby-Token': API_KEY,
        'Content-Type': 'image/jpeg',
        'Connection': 'keep-alive'
    }
    url = f'{JELLYFIN_URL}/Items/{item_id}/Images/{image_type}/0'

    try:
        encoded_data = base64.b64encode(image_data)
        response = requests.post(url, headers=headers,
                                 data=encoded_data, timeout=30)

        if response.status_code == 204:
            return True
        else:
            print(
                f"   ✗ Upload error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"   ✗ Error uploading to Jellyfin: {e}")
        return False


def add_badge(poster_data: bytes) -> Optional[bytes]:
    """
    Add 1080p badge to poster in memory (no file storage)
    """
    try:
        poster = Image.open(io.BytesIO(poster_data))
        badge_file = "cam.png"

        if not os.path.exists(badge_file):
            print(f"   ✗ Badge file not found: {badge_file}")
            return None

        badge = Image.open(badge_file)

        # Resize badge (15% of poster width)
        poster_width, poster_height = poster.size
        badge_width = int(poster_width * 1)  # 100% of poster width
        badge_height = int(badge.size[1] * (badge_width / badge.size[0]))
        badge_resized = badge.resize(
            (badge_width, badge_height), Image.Resampling.LANCZOS)

        # Position at very top edge of image
        position = (0, 0)  # Top-left corner, no offset

        # Paste badge onto poster
        if badge_resized.mode == 'RGBA':
            poster.paste(badge_resized, position, badge_resized)
        else:
            poster.paste(badge_resized, position)

        # Convert back to bytes
        output_buffer = io.BytesIO()
        poster.save(output_buffer, format='JPEG', quality=95)

        return output_buffer.getvalue()

    except Exception as e:
        print(f"   ✗ Error adding badge: {e}")
        return None


def process_library_items_with_1080p_badge(items: List[Dict]):
    """
    Process ALL items in library and add 1080p badge
    """
    if not items:
        print("No items found in library.")
        return

    # Filter for items that can have posters (Movies, Series, BoxSets)
    poster_items = [item for item in items if item.get(
        'Type') in ['Movie', 'Series', 'BoxSet']]

    if not poster_items:
        print("No items with posters found in library.")
        return

    print(
        f"Processing {len(poster_items)} items with posters in library {LIBRARY_ID}:")
    print("-" * 80)

    processed_count = 0
    uploaded_count = 0
    badge_added_count = 0
    error_count = 0

    for i, item in enumerate(poster_items, 1):
        name = item.get('Name', 'Unknown')
        item_id = item.get('Id', 'Unknown')
        item_type = item.get('Type', 'Unknown')

        print(f"{i}/{len(poster_items)}: {name} ({item_type})")
        print(f"   ID: {item_id}")

        # Download current image
        image_data = download_item_image(item_id)

        if image_data:
            # Add 1080p badge in memory
            badge_image_data = add_badge(image_data)

            if badge_image_data:
                badge_added_count += 1
                print(f"   ✓ badge added")

                # Upload badge image back to Jellyfin
                upload_success = upload_image_to_jellyfin(
                    item_id, badge_image_data)

                if upload_success:
                    uploaded_count += 1
                    print(f"   ✓ Uploaded to Jellyfin successfully")
                else:
                    error_count += 1
            else:
                error_count += 1

            processed_count += 1
        else:
            print(f"   ✗ Failed to download image")
            error_count += 1

        # Progress indicator every 10 items
        if i % 10 == 0:
            print(f"\n--- Progress Update ---")
            print(f"Processed: {i}/{len(poster_items)} items")
            print(f"Badges added: {badge_added_count}")
            print(f"Uploaded: {uploaded_count}")
            print(f"Errors: {error_count}")
            print(f"----------------------\n")

        print()  # Empty line for readability

    # Final statistics
    print("=" * 80)
    print("LIBRARY PROCESSING COMPLETED!")
    print("=" * 80)
    print(f"Library ID: {LIBRARY_ID}")
    print(f"Total items with posters: {len(poster_items)}")
    print(f"Processed: {processed_count}")
    print(f"Badges added: {badge_added_count}")
    print(f"Successfully uploaded: {uploaded_count}")
    print(f"Errors: {error_count}")
    print(
        f"Success rate: {(uploaded_count / len(poster_items) * 100):.1f}%" if poster_items else "0%")
    print("=" * 80)


def main():
    """
    Main program execution for library-specific 1080p badge processing
    """

    # Check badge file
    badge_file = "cam.png"
    if os.path.exists(badge_file):
        print(f"✓ Badge file found: {badge_file}")
    else:
        print(f"✗ Badge file missing: {badge_file}")
        print("Please place the 1080p.png file in the script directory.")
        return

    print()

    # Get library information and verify target library exists
    print("Checking available libraries...")
    library_exists = get_library_info()

    if not library_exists:
        print("✗ Target library not found or not accessible.")
        print("Please check the library ID and API permissions.")
        return

    print("\nStarting library processing...")
    print("-" * 70)

    # Fetch and process ALL items from the specific library
    items = get_items_from_library()
    if items:
        process_library_items_with_1080p_badge(items)
        print("\n✓ All done! Check your Jellyfin library for updated posters.")
    else:
        print("✗ No items could be fetched from the library.")
        print("Please verify the library ID and API access.")


if __name__ == "__main__":
    main()
