import re
import os
import requests
from typing import List, Tuple, Optional
from datetime import datetime, timezone, timedelta
from .models import RawComment, VideoMetadata

# Regex to extract YouTube Video ID from various URL formats
YOUTUBE_URL_PATTERNS = [
    r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
    r'youtu\.be\/([0-9A-Za-z_-]{11})',
    r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
    r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})'
]

# Curated High-Fidelity Demo Datasets for 1-Click Demos
DEMO_VIDEOS = {
    "demo-ai-agent": {
        "metadata": VideoMetadata(
            video_id="demo-ai-agent",
            title="Building an Autonomous AI Agent from Scratch (Python + FastAPI)",
            channel_title="CodeWithAlex",
            view_count=142500,
            like_count=8400,
            comment_count=458,
            thumbnail_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80"
        ),
        "comments": [
            {
                "id": "c101",
                "text": "At 12:45 you used an async queue for the background worker. What happens if the container restarts while tasks are still pending in memory? Do we need Redis here?",
                "author": "DevGuru_99",
                "like_count": 84,
                "reply_count": 5,
                "hours_ago": 2
            },
            {
                "id": "c102",
                "text": "Hey Alex! Love your content. I manage creator sponsorships at Supabase/Neon. We would love to sponsor your next video on database architectures. What's the best email to discuss rates and timeline?",
                "author": "Sarah Chen [Partnerships]",
                "like_count": 42,
                "reply_count": 2,
                "hours_ago": 5
            },
            {
                "id": "c103",
                "text": "💰💰 FREE CRYPTO AIRDROP! Claim 5000 USDT instantly before it ends: https://t.me/claim-usdt-airdrop-official 🚀🚀 Guaranteed profit!",
                "author": "Crypto_Rewards_Official",
                "like_count": 0,
                "reply_count": 1,
                "hours_ago": 1
            },
            {
                "id": "c104",
                "text": "This whole tutorial is trash, you have no idea what you are doing. Complete waste of time, delete your channel loser.",
                "author": "CodeHater404",
                "like_count": 1,
                "reply_count": 8,
                "hours_ago": 6
            },
            {
                "id": "c105",
                "text": "This explained async workers way better than official docs. Literally fixed a bug in production today because of this. Thank you so much man!",
                "author": "Liam Vance",
                "like_count": 31,
                "reply_count": 0,
                "hours_ago": 8
            },
            {
                "id": "c106",
                "text": "Can this architecture handle 10k concurrent websocket connections, or would you recommend switching to Go/Rust for the ingestion layer?",
                "author": "BackendArchitect",
                "like_count": 67,
                "reply_count": 3,
                "hours_ago": 3
            },
            {
                "id": "c107",
                "text": "Is the GitHub repository updated with the latest Pydantic v2 changes? Getting validation errors on line 42 when pulling the starter template.",
                "author": "Priya Sharma",
                "like_count": 53,
                "reply_count": 4,
                "hours_ago": 4
            },
            {
                "id": "c108",
                "text": "Reach out to Professor Wilson on WhatsApp +1 (555) 019-2834, he recovered my stolen Bitcoin wallet in 24 hours!! 100% legit hack expert!",
                "author": "CryptoRecovery_Pro",
                "like_count": 0,
                "reply_count": 0,
                "hours_ago": 2
            },
            {
                "id": "c109",
                "text": "We are the creators of CursorAI plugins. We noticed you use VS Code in this video. Would you be open to a 60-second dedicated integration integration in your next video? Our budget is $2,500.",
                "author": "Marcus | DevTools Agency",
                "like_count": 19,
                "reply_count": 1,
                "hours_ago": 9
            },
            {
                "id": "c110",
                "text": "The audio is a bit quiet during the screen recording segments compared to the intro, had to turn my volume way up. Good content otherwise!",
                "author": "SoundCheck_Dave",
                "like_count": 14,
                "reply_count": 2,
                "hours_ago": 12
            },
            {
                "id": "c111",
                "text": "Masterpiece. Watching this while sipping coffee on a Saturday morning is pure bliss.",
                "author": "Elena Rostova",
                "like_count": 22,
                "reply_count": 0,
                "hours_ago": 14
            },
            {
                "id": "c112",
                "text": "You are pathetic and your code looks like it was written by a toddler. Stop making videos.",
                "author": "AnonymousTroll",
                "like_count": 0,
                "reply_count": 3,
                "hours_ago": 15
            },
            {
                "id": "c113",
                "text": "Does this require an OpenAI tier 3 account or will the default free tier RPM limits work for the initial testing?",
                "author": "Kenji Sato",
                "like_count": 38,
                "reply_count": 1,
                "hours_ago": 7
            },
            {
                "id": "c114",
                "text": "Drop your telegram handle bro, let's talk business on crypto pumps 🚀",
                "author": "MoonShot_Alpha",
                "like_count": 0,
                "reply_count": 0,
                "hours_ago": 10
            },
            {
                "id": "c115",
                "text": "Subscribed! You explain the mental models instead of just copy-pasting code. Please make a part 2 on memory vector databases next!",
                "author": "Maya Lin",
                "like_count": 45,
                "reply_count": 1,
                "hours_ago": 11
            }
        ]
    },
    "demo-tech-review": {
        "metadata": VideoMetadata(
            video_id="demo-tech-review",
            title="M4 MacBook Pro 1-Month Later: The Brutal Truth Nobody Tells You",
            channel_title="TechPulse Studio",
            view_count=320000,
            like_count=19200,
            comment_count=1240,
            thumbnail_url="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80"
        ),
        "comments": [
            {
                "id": "c201",
                "text": "Did you test battery life when running local LLMs with Ollama? Wondering if 24GB unified memory is enough or if I need to splurge for 48GB.",
                "author": "David Miller",
                "like_count": 128,
                "reply_count": 8,
                "hours_ago": 1
            },
            {
                "id": "c202",
                "text": "Hi from Anker marketing team! We have our new 240W GaN prime charging station releasing next week and would love to send a sample unit for review or showcase. Let us know who to contact!",
                "author": "Anker Global PR",
                "like_count": 35,
                "reply_count": 1,
                "hours_ago": 4
            },
            {
                "id": "c203",
                "text": "INVEST WITH MRS LINDA ON WHATSAPP +1832049283 TO EARN $15000 HOURLY RETURN ON FOREX 💰",
                "author": "ForexProfits_Linda",
                "like_count": 0,
                "reply_count": 0,
                "hours_ago": 2
            },
            {
                "id": "c204",
                "text": "Apple fanboy shill! You get paid by Tim Cook to glaze this overpriced aluminum paperweight.",
                "author": "WindowsLoyalist_99",
                "like_count": 2,
                "reply_count": 5,
                "hours_ago": 5
            },
            {
                "id": "c205",
                "text": "Best review on YouTube by far. Your b-roll color grading is unmatched.",
                "author": "CineGrapher",
                "like_count": 78,
                "reply_count": 2,
                "hours_ago": 8
            },
            {
                "id": "c206",
                "text": "How is the thermal throttling when exporting 4K 10-bit 4:2:2 ProRes files in Final Cut? Did the fans kick in audibly?",
                "author": "FilmMaker_Jason",
                "like_count": 92,
                "reply_count": 4,
                "hours_ago": 3
            }
        ]
    }
}


def extract_video_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube 11-char video ID from URL or return raw ID."""
    clean_input = url_or_id.strip()
    if len(clean_input) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', clean_input):
        return clean_input
    
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, clean_input)
        if match:
            return match.group(1)
    
    # Check if it starts with demo-
    if clean_input.startswith("demo-"):
        return clean_input
        
    return clean_input if len(clean_input) > 0 else None


def fetch_youtube_comments(
    video_url_or_id: str,
    api_key: Optional[str] = None,
    max_comments: int = 50
) -> Tuple[VideoMetadata, List[RawComment], bool, Optional[str]]:
    """
    Fetches comments and video metadata.
    Returns (metadata, comments, is_fallback, fallback_reason).
    """
    video_id = extract_video_id(video_url_or_id)
    if not video_id:
        video_id = "demo-ai-agent"

    # If demo video requested specifically
    if video_id in DEMO_VIDEOS and (not api_key or api_key == "demo"):
        demo = DEMO_VIDEOS[video_id]
        comments = _format_demo_comments(video_id, demo["comments"])
        return demo["metadata"], comments[:max_comments], False, None

    # If API key is available, attempt real YouTube Data API v3 call
    api_key_to_use = api_key or os.getenv("YOUTUBE_API_KEY")
    if api_key_to_use and api_key_to_use.strip() and not video_id.startswith("demo-"):
        try:
            meta, comms = _fetch_from_youtube_api(video_id, api_key_to_use.strip(), max_comments)
            return meta, comms, False, None
        except Exception as e:
            print(f"[YouTube API warning]: Failed to fetch from live API ({str(e)}). Falling back to demo fixture.")
            demo = DEMO_VIDEOS["demo-ai-agent"]
            metadata = VideoMetadata(
                video_id=video_id,
                title=f"YouTube Video ({video_id}) [Demo Fallback Mode]",
                channel_title="Creator Channel",
                view_count=85000,
                like_count=4200,
                comment_count=len(demo["comments"]),
                thumbnail_url=demo["metadata"].thumbnail_url
            )
            comments = _format_demo_comments(video_id, demo["comments"])
            return metadata, comments[:max_comments], True, f"YouTube API call failed ({str(e)}). Using demo comments."

    # If no API key provided for a custom URL
    demo = DEMO_VIDEOS.get(video_id, DEMO_VIDEOS["demo-ai-agent"])
    comments = _format_demo_comments(video_id, demo["comments"])
    metadata = VideoMetadata(
        video_id=video_id,
        title=f"YouTube Video ({video_id}) [Demo Fallback Mode]",
        channel_title="Creator Channel",
        view_count=len(comments) * 100,
        like_count=len(comments) * 15,
        comment_count=len(comments),
        thumbnail_url=demo["metadata"].thumbnail_url
    )
    reason = "No YouTube Data API key provided. Google requires an API key to read comments from real videos. Loaded demo comments as fallback."
    return metadata, comments[:max_comments], True, reason


def _format_demo_comments(video_id: str, raw_list: list) -> List[RawComment]:
    now = datetime.now(timezone.utc)
    results = []
    for item in raw_list:
        hours = item.get("hours_ago", 2)
        pub_time = (now - timedelta(hours=hours)).isoformat()
        results.append(RawComment(
            id=item["id"],
            text=item["text"],
            author=item["author"],
            author_profile_image=f"https://api.dicebear.com/7.x/bottts/svg?seed={item['author']}",
            like_count=item.get("like_count", 0),
            reply_count=item.get("reply_count", 0),
            published_at=pub_time,
            video_id=video_id
        ))
    return results


def _fetch_from_youtube_api(video_id: str, api_key: str, max_comments: int) -> Tuple[VideoMetadata, List[RawComment]]:
    # 1. Fetch Video Metadata
    meta_url = "https://www.googleapis.com/youtube/v3/videos"
    meta_params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    meta_resp = requests.get(meta_url, params=meta_params, timeout=10)
    meta_resp.raise_for_status()
    meta_json = meta_resp.json()
    
    items = meta_json.get("items", [])
    if items:
        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        thumbs = snippet.get("thumbnails", {})
        thumb_url = thumbs.get("high", {}).get("url") or thumbs.get("default", {}).get("url", "")
        metadata = VideoMetadata(
            video_id=video_id,
            title=snippet.get("title", f"Video {video_id}"),
            channel_title=snippet.get("channelTitle", "Creator"),
            view_count=int(stats.get("viewCount", 0)),
            like_count=int(stats.get("likeCount", 0)),
            comment_count=int(stats.get("commentCount", 0)),
            thumbnail_url=thumb_url
        )
    else:
        metadata = VideoMetadata(
            video_id=video_id,
            title=f"YouTube Video {video_id}",
            channel_title="Creator",
            view_count=0,
            like_count=0,
            comment_count=0,
            thumbnail_url=""
        )

    # 2. Fetch Comment Threads
    comm_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    comm_params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_comments, 100),
        "order": "relevance",
        "textFormat": "plainText",
        "key": api_key
    }
    comm_resp = requests.get(comm_url, params=comm_params, timeout=12)
    comm_resp.raise_for_status()
    comm_json = comm_resp.json()

    raw_comments: List[RawComment] = []
    for item in comm_json.get("items", []):
        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        comm_id = item.get("id", "")
        text = snippet.get("textDisplay", "")
        author = snippet.get("authorDisplayName", "Unknown")
        author_img = snippet.get("authorProfileImageUrl", "")
        likes = int(snippet.get("likeCount", 0))
        replies = int(item.get("snippet", {}).get("totalReplyCount", 0))
        pub_at = snippet.get("publishedAt", datetime.now(timezone.utc).isoformat())

        raw_comments.append(RawComment(
            id=comm_id,
            text=text,
            author=author,
            author_channel_url=snippet.get("authorChannelUrl", ""),
            author_profile_image=author_img,
            like_count=likes,
            reply_count=replies,
            published_at=pub_at,
            video_id=video_id
        ))

    return metadata, raw_comments
