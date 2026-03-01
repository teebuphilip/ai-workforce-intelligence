"""
posting.py - Core Posting Engine

WHY: Generic infrastructure to post content to social platforms.
     Business logic generates content, this module publishes it.

SUPPORTS:
  - Reddit (via PRAW)
  - Twitter/X (via tweepy)
  - LinkedIn (via linkedin-api-client)
  - Facebook (via facebook-sdk)

CONFIGURATION:
  Read from business_config.json per business:
  {
    "social_media": {
      "reddit": {
        "client_id": "...",
        "client_secret": "...",
        "username": "...",
        "password": "..."
      },
      "twitter": {
        "api_key": "...",
        "api_secret": "...",
        "access_token": "...",
        "access_token_secret": "..."
      }
    }
  }

USAGE:
  from core.posting import post_to_reddit, post_to_twitter
  
  result = post_to_reddit(
      title="Daily Fantasy Tips",
      content="Here are today's picks...",
      subreddit="fantasybball"
  )
  
  if result.success:
      print(f"Posted: {result.url}")
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)


# ============================================================
# RESULT DATACLASS
# WHY: Standardized response across all platforms
# ============================================================

@dataclass
class PostResult:
    """
    Standard result object returned by all posting functions.
    
    WHY: Every platform returns different data. This normalizes it.
    """
    success: bool
    platform: str
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[Dict] = None
    
    def __repr__(self):
        if self.success:
            return f"PostResult(✓ {self.platform}, id={self.post_id}, url={self.url})"
        else:
            return f"PostResult(✗ {self.platform}, error={self.error})"


# ============================================================
# CONFIG LOADER
# ============================================================

def _load_social_config() -> Dict[str, Any]:
    """
    Load social_media section from business_config.json.
    
    WHY: Credentials are per-business, not hardcoded.
    
    Returns empty dict if:
    - Config file doesn't exist
    - marketing.enabled = false
    - social_media section missing
    
    This allows the boilerplate to work WITHOUT Tier 3 configured.
    """
    config_path = Path(__file__).parent.parent / "config" / "business_config.json"
    
    if not config_path.exists():
        logger.warning("business_config.json not found - social posting will fail")
        return {}
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        # Check if marketing is enabled
        marketing = config.get("marketing", {})
        if not marketing.get("enabled", False):
            logger.info("Marketing disabled in config - social posting not available")
            return {}
        
        # Return social_media section (may be empty)
        social_config = config.get("social_media", {})
        
        if not social_config:
            logger.warning("social_media section missing in config - add credentials to enable posting")
        
        return social_config
        
    except Exception as e:
        logger.error(f"Failed to load social config: {e}")
        return {}


# ============================================================
# REDDIT POSTING
# ============================================================

def post_to_reddit(
    title: str,
    content: str,
    subreddit: str,
    flair_id: Optional[str] = None,
    config_override: Optional[Dict] = None
) -> PostResult:
    """
    Post to Reddit using PRAW.
    
    Args:
        title: Post title (max 300 chars)
        content: Post body (markdown supported)
        subreddit: Subreddit name (no r/ prefix)
        flair_id: Optional flair ID for the post
        config_override: Optional dict with credentials (for testing)
    
    Returns:
        PostResult with success status and post URL
    
    Example:
        result = post_to_reddit(
            title="Daily Fantasy Basketball Tips",
            content="Here are today's waiver wire picks...",
            subreddit="fantasybball"
        )
    """
    try:
        import praw
    except ImportError:
        return PostResult(
            success=False,
            platform="reddit",
            error="praw library not installed. Run: pip install praw"
        )
    
    # Load credentials
    config = config_override or _load_social_config().get("reddit", {})
    
    if not all(k in config for k in ["client_id", "client_secret", "username", "password"]):
        return PostResult(
            success=False,
            platform="reddit",
            error="Missing Reddit credentials in business_config.json"
        )
    
    try:
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            username=config["username"],
            password=config["password"],
            user_agent=config.get("user_agent", "CourtDominion/1.0")
        )
        
        # Submit post
        subreddit_obj = reddit.subreddit(subreddit)
        submission = subreddit_obj.submit(
            title=title,
            selftext=content,
            flair_id=flair_id
        )
        
        logger.info(f"Posted to r/{subreddit}: {submission.id}")
        
        return PostResult(
            success=True,
            platform="reddit",
            post_id=submission.id,
            url=f"https://reddit.com{submission.permalink}",
            raw_response={"id": submission.id, "permalink": submission.permalink}
        )
        
    except Exception as e:
        logger.error(f"Reddit posting error: {e}")
        return PostResult(
            success=False,
            platform="reddit",
            error=str(e)
        )


# ============================================================
# TWITTER/X POSTING
# ============================================================

def post_to_twitter(
    content: str,
    media_paths: Optional[List[str]] = None,
    config_override: Optional[Dict] = None
) -> PostResult:
    """
    Post to Twitter/X using tweepy.
    
    Args:
        content: Tweet text (max 280 chars per tweet)
        media_paths: Optional list of image file paths to attach
        config_override: Optional dict with credentials (for testing)
    
    Returns:
        PostResult with success status and tweet URL
    
    Example:
        result = post_to_twitter(
            content="Today's #NBA fantasy picks are 🔥\n\nTop waiver targets:\n1. Player A\n2. Player B",
            media_paths=["/path/to/chart.png"]
        )
    """
    try:
        import tweepy
    except ImportError:
        return PostResult(
            success=False,
            platform="twitter",
            error="tweepy library not installed. Run: pip install tweepy"
        )
    
    # Load credentials
    config = config_override or _load_social_config().get("twitter", {})
    
    required_keys = ["api_key", "api_secret", "access_token", "access_token_secret"]
    if not all(k in config for k in required_keys):
        return PostResult(
            success=False,
            platform="twitter",
            error="Missing Twitter credentials in business_config.json"
        )
    
    try:
        # Initialize Twitter client (API v2)
        client = tweepy.Client(
            consumer_key=config["api_key"],
            consumer_secret=config["api_secret"],
            access_token=config["access_token"],
            access_token_secret=config["access_token_secret"]
        )
        
        # Upload media if provided
        media_ids = None
        if media_paths:
            # Need v1.1 API for media upload
            auth = tweepy.OAuth1UserHandler(
                config["api_key"],
                config["api_secret"],
                config["access_token"],
                config["access_token_secret"]
            )
            api_v1 = tweepy.API(auth)
            
            media_ids = []
            for path in media_paths:
                media = api_v1.media_upload(path)
                media_ids.append(media.media_id)
        
        # Post tweet
        response = client.create_tweet(
            text=content,
            media_ids=media_ids
        )
        
        tweet_id = response.data["id"]
        username = config.get("username", "user")  # Hero should add this to config
        tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
        
        logger.info(f"Posted tweet: {tweet_id}")
        
        return PostResult(
            success=True,
            platform="twitter",
            post_id=tweet_id,
            url=tweet_url,
            raw_response=response.data
        )
        
    except Exception as e:
        logger.error(f"Twitter posting error: {e}")
        return PostResult(
            success=False,
            platform="twitter",
            error=str(e)
        )


def post_twitter_thread(
    tweets: List[str],
    media_paths: Optional[List[str]] = None,
    config_override: Optional[Dict] = None
) -> List[PostResult]:
    """
    Post a Twitter thread (multiple tweets in reply chain).
    
    Args:
        tweets: List of tweet texts (each max 280 chars)
        media_paths: Optional images for first tweet only
        config_override: Optional credentials dict
    
    Returns:
        List of PostResults, one per tweet
    
    Example:
        results = post_twitter_thread([
            "🏀 Daily Fantasy Basketball Thread 🧵\n\n#NBA #FantasyBasketball",
            "1/ Today's top waiver wire targets...",
            "2/ Streaming candidates for tonight...",
            "3/ Injury impacts to monitor..."
        ])
    """
    try:
        import tweepy
    except ImportError:
        return [PostResult(
            success=False,
            platform="twitter",
            error="tweepy library not installed"
        )]
    
    config = config_override or _load_social_config().get("twitter", {})
    
    required_keys = ["api_key", "api_secret", "access_token", "access_token_secret"]
    if not all(k in config for k in required_keys):
        return [PostResult(
            success=False,
            platform="twitter",
            error="Missing Twitter credentials"
        )]
    
    try:
        client = tweepy.Client(
            consumer_key=config["api_key"],
            consumer_secret=config["api_secret"],
            access_token=config["access_token"],
            access_token_secret=config["access_token_secret"]
        )
        
        results = []
        previous_tweet_id = None
        
        for i, tweet_text in enumerate(tweets):
            # Upload media only for first tweet
            media_ids = None
            if i == 0 and media_paths:
                auth = tweepy.OAuth1UserHandler(
                    config["api_key"],
                    config["api_secret"],
                    config["access_token"],
                    config["access_token_secret"]
                )
                api_v1 = tweepy.API(auth)
                media_ids = [api_v1.media_upload(p).media_id for p in media_paths]
            
            # Post as reply to previous tweet if not first
            response = client.create_tweet(
                text=tweet_text,
                in_reply_to_tweet_id=previous_tweet_id,
                media_ids=media_ids
            )
            
            tweet_id = response.data["id"]
            username = config.get("username", "user")
            
            results.append(PostResult(
                success=True,
                platform="twitter",
                post_id=tweet_id,
                url=f"https://twitter.com/{username}/status/{tweet_id}",
                raw_response=response.data
            ))
            
            previous_tweet_id = tweet_id
            time.sleep(1)  # Rate limit buffer between tweets
        
        logger.info(f"Posted Twitter thread: {len(results)} tweets")
        return results
        
    except Exception as e:
        logger.error(f"Twitter thread error: {e}")
        return [PostResult(success=False, platform="twitter", error=str(e))]


# ============================================================
# LINKEDIN POSTING
# ============================================================

def post_to_linkedin(
    content: str,
    config_override: Optional[Dict] = None
) -> PostResult:
    """
    Post to LinkedIn using linkedin-api-client.
    
    Args:
        content: Post content (markdown supported, max 3000 chars)
        config_override: Optional credentials dict
    
    Returns:
        PostResult with success status and post URL
    
    Example:
        result = post_to_linkedin(
            content="Excited to share today's NBA fantasy basketball insights..."
        )
    """
    try:
        from linkedin_api import Linkedin
    except ImportError:
        return PostResult(
            success=False,
            platform="linkedin",
            error="linkedin-api library not installed. Run: pip install linkedin-api"
        )
    
    config = config_override or _load_social_config().get("linkedin", {})
    
    if not all(k in config for k in ["username", "password"]):
        return PostResult(
            success=False,
            platform="linkedin",
            error="Missing LinkedIn credentials in business_config.json"
        )
    
    try:
        # Initialize LinkedIn client
        api = Linkedin(config["username"], config["password"])
        
        # Post update
        # Note: linkedin-api doesn't return post ID easily, this is a limitation
        api.post_update(content)
        
        logger.info("Posted to LinkedIn")
        
        return PostResult(
            success=True,
            platform="linkedin",
            post_id=None,  # linkedin-api limitation
            url=f"https://www.linkedin.com/in/{config['username']}/recent-activity/all/",
            raw_response={"content": content}
        )
        
    except Exception as e:
        logger.error(f"LinkedIn posting error: {e}")
        return PostResult(
            success=False,
            platform="linkedin",
            error=str(e)
        )


# ============================================================
# DISCORD POSTING
# ============================================================

def post_to_discord(
    content: str,
    webhook_url: Optional[str] = None,
    embed: Optional[Dict] = None,
    config_override: Optional[Dict] = None
) -> PostResult:
    """
    Post to Discord using webhooks.
    
    WHY webhooks: Simplest Discord integration - no bot setup needed.
    Just create a webhook in Discord channel settings.
    
    Args:
        content: Message text (max 2000 chars)
        webhook_url: Discord webhook URL (overrides config)
        embed: Optional embed object for rich formatting
            {
                "title": "...",
                "description": "...",
                "color": 0x00ff00,  # Green
                "fields": [{"name": "...", "value": "...", "inline": True}],
                "footer": {"text": "..."},
                "timestamp": "2024-01-01T00:00:00.000Z"
            }
        config_override: Optional credentials dict
    
    Returns:
        PostResult with success status
    
    Example:
        # Simple text post
        result = post_to_discord(
            content="Today's fantasy basketball picks are here! 🏀"
        )
        
        # Rich embed post
        result = post_to_discord(
            content="Daily Update",
            embed={
                "title": "Waiver Wire Targets",
                "description": "Top picks for today...",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Player A", "value": "32.5 FP projected", "inline": True},
                    {"name": "Player B", "value": "28.1 FP projected", "inline": True}
                ]
            }
        )
    """
    try:
        import requests
    except ImportError:
        return PostResult(
            success=False,
            platform="discord",
            error="requests library not installed (should be in requirements)"
        )
    
    # Get webhook URL from config or parameter
    config = config_override or _load_social_config().get("discord", {})
    url = webhook_url or config.get("webhook_url")
    
    if not url:
        return PostResult(
            success=False,
            platform="discord",
            error="Missing Discord webhook_url in business_config.json"
        )
    
    # Build payload
    payload = {}
    
    if content:
        payload["content"] = content
    
    if embed:
        payload["embeds"] = [embed]
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code in (200, 204):
            logger.info("Posted to Discord")
            
            return PostResult(
                success=True,
                platform="discord",
                post_id=None,  # Webhooks don't return message ID
                url=url,  # Return webhook URL as reference
                raw_response={"status": response.status_code}
            )
        else:
            logger.error(f"Discord webhook error: {response.status_code} - {response.text}")
            return PostResult(
                success=False,
                platform="discord",
                error=f"HTTP {response.status_code}: {response.text}"
            )
        
    except Exception as e:
        logger.error(f"Discord posting error: {e}")
        return PostResult(
            success=False,
            platform="discord",
            error=str(e)
        )


# ============================================================
# FACEBOOK POSTING
# ============================================================

def post_to_facebook(
    content: str,
    page_id: Optional[str] = None,
    config_override: Optional[Dict] = None
) -> PostResult:
    """
    Post to Facebook Page using facebook-sdk.
    
    Args:
        content: Post content
        page_id: Facebook Page ID (if posting to page, not profile)
        config_override: Optional credentials dict
    
    Returns:
        PostResult with success status and post URL
    
    Example:
        result = post_to_facebook(
            content="Check out today's fantasy basketball projections!",
            page_id="123456789"
        )
    """
    try:
        import facebook
    except ImportError:
        return PostResult(
            success=False,
            platform="facebook",
            error="facebook-sdk library not installed. Run: pip install facebook-sdk"
        )
    
    config = config_override or _load_social_config().get("facebook", {})
    
    if "access_token" not in config:
        return PostResult(
            success=False,
            platform="facebook",
            error="Missing Facebook access_token in business_config.json"
        )
    
    try:
        graph = facebook.GraphAPI(access_token=config["access_token"])
        
        # Post to page or profile
        target = page_id or "me"
        response = graph.put_object(
            parent_object=target,
            connection_name="feed",
            message=content
        )
        
        post_id = response.get("id")
        post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"
        
        logger.info(f"Posted to Facebook: {post_id}")
        
        return PostResult(
            success=True,
            platform="facebook",
            post_id=post_id,
            url=post_url,
            raw_response=response
        )
        
    except Exception as e:
        logger.error(f"Facebook posting error: {e}")
        return PostResult(
            success=False,
            platform="facebook",
            error=str(e)
        )


# ============================================================
# MULTI-PLATFORM POSTING
# ============================================================

def post_to_all_platforms(
    content: Dict[str, str],
    platforms: Optional[List[str]] = None
) -> Dict[str, PostResult]:
    """
    Post to multiple platforms at once.
    
    WHY: Marketing tier posts same campaign across all channels.
    
    CRITICAL: Reddit is MANDATORY. If Reddit is not configured or fails,
              the entire operation is considered a failure.
    
    Args:
        content: Dict mapping platform to content
            {
                "reddit": {"title": "...", "content": "...", "subreddit": "..."},
                "discord": {"content": "...", "embed": {...}},
                "twitter": {"content": "..."},
                "linkedin": {"content": "..."},
                "facebook": {"content": "..."}
            }
        platforms: Optional list to filter which platforms to post to
                   If not provided, reads from business_config.json marketing.platforms
    
    Returns:
        Dict mapping platform name to PostResult
    
    Example:
        results = post_to_all_platforms({
            "reddit": {
                "title": "Daily Tips",
                "content": "Here are today's picks...",
                "subreddit": "fantasybball"
            },
            "discord": {
                "content": "Daily update is live! 🏀",
                "embed": {
                    "title": "Waiver Wire Targets",
                    "description": "Top 3 picks...",
                    "color": 0x00ff00
                }
            },
            "twitter": {
                "content": "Today's picks are live! 🔥"
            }
        })
        
        for platform, result in results.items():
            if result.success:
                print(f"✓ {platform}: {result.url}")
    """
    
    # Determine which platforms to post to
    if platforms is None:
        # Read from config
        config = _load_social_config()
        marketing_config = config.get("marketing", {})
        platforms = marketing_config.get("platforms", ["reddit"])
    
    # CRITICAL: Ensure Reddit is always included
    if "reddit" not in platforms:
        logger.warning("Reddit not in platforms list - adding it (Reddit is mandatory)")
        platforms = ["reddit"] + platforms
    
    # CRITICAL: Validate Reddit content is provided
    if "reddit" not in content:
        logger.error("Reddit content not provided - Reddit is mandatory for Tier 3")
        return {
            "reddit": PostResult(
                success=False,
                platform="reddit",
                error="Reddit is mandatory but no content was provided"
            )
        }
    
    results = {}
    reddit_succeeded = False
    
    # Post to Reddit FIRST (mandatory)
    try:
        reddit_content = content["reddit"]
        reddit_result = post_to_reddit(**reddit_content)
        results["reddit"] = reddit_result
        reddit_succeeded = reddit_result.success
        
        if not reddit_succeeded:
            logger.error(f"Reddit posting failed (mandatory): {reddit_result.error}")
        else:
            logger.info(f"Reddit posting succeeded (mandatory): {reddit_result.url}")
        
    except Exception as e:
        logger.error(f"Reddit posting error (mandatory): {e}")
        results["reddit"] = PostResult(
            success=False,
            platform="reddit",
            error=str(e)
        )
        reddit_succeeded = False
    
    # Post to other platforms (optional - failures don't block)
    for platform in platforms:
        if platform == "reddit":
            continue  # Already posted above
        
        if platform not in content:
            logger.warning(f"Platform {platform} configured but no content provided - skipping")
            continue
        
        platform_content = content[platform]
        
        try:
            if platform == "twitter":
                result = post_to_twitter(**platform_content)
            elif platform == "discord":
                result = post_to_discord(**platform_content)
            elif platform == "linkedin":
                result = post_to_linkedin(**platform_content)
            elif platform == "facebook":
                result = post_to_facebook(**platform_content)
            else:
                result = PostResult(
                    success=False,
                    platform=platform,
                    error=f"Unknown platform: {platform}"
                )
            
            results[platform] = result
            
            if result.success:
                logger.info(f"{platform} posting succeeded (optional): {result.url or 'OK'}")
            else:
                logger.warning(f"{platform} posting failed (optional): {result.error}")
            
            # Rate limit buffer between platforms
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error posting to {platform} (optional): {e}")
            results[platform] = PostResult(
                success=False,
                platform=platform,
                error=str(e)
            )
    
    # Add summary metadata
    total_platforms = len(results)
    successful_platforms = sum(1 for r in results.values() if r.success)
    
    logger.info(
        f"Multi-platform posting complete: {successful_platforms}/{total_platforms} succeeded. "
        f"Reddit (mandatory): {'✓' if reddit_succeeded else '✗'}"
    )
    
    return results
