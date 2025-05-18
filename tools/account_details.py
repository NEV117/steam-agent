import os
from typing import Optional
from steam_web_api import Steam
from datetime import datetime
import json

def format_timestamp(timestamp):
    """Convert Unix timestamp to DD/MM/YYYY format, or return 'N/A' if timestamp is missing."""
    return datetime.utcfromtimestamp(timestamp).strftime('%d/%m/%Y') if timestamp else "N/A"

def get_user_games(user_id: Optional[str] = "76561198447564163", count: Optional[int] = 10) -> str:
    """
    Fetches and returns the top 'count' most played games of a Steam user as a JSON string.
    
    :param user_id: Steam ID of the user.
    :param count: Number of top-played games to retrieve.
    :prints: JSON string containing game details.
    """
    print(f"Fetching top {count} games for user ID: {user_id}")
    API_KEY = os.getenv("STEAM_API_KEY")
    steam = Steam(API_KEY)
    
    # Fetch user's owned games
    user_games = steam.users.get_owned_games(user_id)
    
    if not user_games or "games" not in user_games:
        print("Error obtaining Steam game list.")
        return json.dumps([])  # Return empty JSON array in case of an error
    
    # Sort games by playtime (descending) and select the top 'count'
    sorted_games = sorted(user_games["games"], key=lambda x: x["playtime_forever"], reverse=True)[:count]
    
    # Format game details
    games_list = [{
        "name": game["name"],
        "appid": game["appid"],
        "playtime_forever": game["playtime_forever"],
        "playtime_2weeks": game.get("playtime_2weeks", 0),
        "has_community_visible_stats": game.get("has_community_visible_stats", 0),
        "last_played": format_timestamp(game.get("rtime_last_played", 0)),
        "img_icon_url": f"https://media.steampowered.com/steamcommunity/public/images/apps/{game['appid']}/{game.get('img_icon_url', '')}.jpg"
    } for game in sorted_games]

    return games_list
    # Convert to JSON and print
    #print(json.dumps(games_list, indent=2, ensure_ascii=False))

