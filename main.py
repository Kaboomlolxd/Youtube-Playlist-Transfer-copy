import requests
import time
import os
import json

# --- USER INPUT ---
# You need to fill in these values from your Google Cloud Console.
# Your Google Cloud API Key
API_KEY = "YOUR_API_KEY"

# The ID of the playlist you want to copy FROM.
SOURCE_PLAYLIST_ID = "YOUR_SOURCE_PLAYLIST_ID"

# The ID of the playlist you want to copy TO.
DESTINATION_PLAYLIST_ID = "YOUR_DESTINATION_PLAYLIST_ID"

# You will need an OAuth 2.0 access token to modify a playlist.
# To get this, you can use a tool like Google's OAuth 2.0 Playground:
# 1. Go to https://developers.google.com/oauthplayground/
# 2. Select the YouTube Data API v3 scope: https://www.googleapis.com/auth/youtube
# 3. Click "Authorize APIs" and grant access to your account.
# 4. Exchange the authorization code for a token and copy the Access Token.
#    Note: This token will expire after a short time.
ACCESS_TOKEN = "YOUR_OAUTH_ACCESS_TOKEN"
# --- END USER INPUT ---

PROGRESS_FILE = "progress.txt"

def get_all_videos_from_playlist(playlist_id, api_key):
    """Fetches all video IDs from a given playlist, handling pagination."""
    print("Fetching videos from the source playlist...")
    videos = []
    next_page_token = None
    
    while True:
        url = "https://www.googleapis.com/youtube/v3/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "key": api_key,
            "maxResults": 50,
            "pageToken": next_page_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            
            for item in data.get("items", []):
                video_id = item.get("snippet", {}).get("resourceId", {}).get("videoId")
                if video_id:
                    videos.append(video_id)
            
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching playlist items: {e}")
            return []
    
    print(f"Found {len(videos)} videos.")
    return videos

def add_video_to_playlist(playlist_id, access_token, video_id):
    """Adds a single video to a playlist."""
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": video_id
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        print(f"Failed to add video {video_id} to playlist: {e}")
        try:
            error_data = response.json()
            if "error" in error_data:
                print(f"API Error Message: {error_data['error'].get('message')}")
                print(f"API Error Reason: {error_data['error'].get('errors')[0].get('reason')}")
        except json.JSONDecodeError:
            print("Could not parse detailed error message from API response.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"An unexpected error occurred: {e}")
        return False

def get_last_video_id():
    """Reads the last successfully added video ID from the progress file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_video_id(video_id):
    """Saves the last successfully added video ID to the progress file."""
    with open(PROGRESS_FILE, "w") as f:
        f.write(video_id)

def main():
    """Main function to perform the transfer."""
    if not all([API_KEY, SOURCE_PLAYLIST_ID, DESTINATION_PLAYLIST_ID, ACCESS_TOKEN]):
        print("Please fill in all the required variables at the top of the script.")
        return

    video_ids = get_all_videos_from_playlist(SOURCE_PLAYLIST_ID, API_KEY)
    
    if not video_ids:
        print("No videos to transfer.")
        return
        
    last_video_id = get_last_video_id()
    if last_video_id:
        print(f"Resuming transfer from video ID: {last_video_id}")
        try:
            start_index = video_ids.index(last_video_id) + 1
            videos_to_add = video_ids[start_index:]
        except ValueError:
            print("Progress file contains an invalid video ID. Starting from the beginning.")
            videos_to_add = video_ids
    else:
        videos_to_add = video_ids

    print(f"Starting transfer of {len(videos_to_add)} videos to destination playlist...")
    
    successful_additions = 0
    for i, video_id in enumerate(videos_to_add):
        print(f"Adding video {i + 1}/{len(videos_to_add)}: {video_id}")
        if add_video_to_playlist(DESTINATION_PLAYLIST_ID, ACCESS_TOKEN, video_id):
            successful_additions += 1
            save_last_video_id(video_id) # Save progress after each successful addition
            # Add a small delay to avoid hitting rate limits too quickly.
            time.sleep(0.5)
        else:
            print(f"Stopping transfer due to API error.")
            break
            
    print("-" * 20)
    print(f"Transfer complete. Successfully added {successful_additions} of {len(videos_to_add)} videos.")
    if successful_additions == len(videos_to_add):
        print("All videos have been transferred. Deleting progress file.")
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)

if __name__ == "__main__":
    main()
