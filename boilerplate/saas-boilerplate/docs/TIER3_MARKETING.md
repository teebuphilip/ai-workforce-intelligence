# Tier 3 Marketing - Social Media Posting System

## Overview

The Tier 3 marketing system enables automated content posting to social media platforms. It consists of two parts:

1. **Generic Posting Engine** (`backend/core/posting.py`) - Infrastructure that posts to platforms
2. **Business Content Generator** (`business/backend/routes/content_marketing.py`) - Business-specific content creation

**MANDATORY PLATFORM:**
- ✅ **Reddit** - Required for all Tier 3. Cannot disable.

**CONFIGURABLE PLATFORMS (Add credentials to enable):**
- Discord - Real-time community updates
- Twitter/X - Social media reach
- LinkedIn - Professional networking
- Facebook - Pages and groups

**Hero chooses which optional platforms to enable by:**
1. Adding credentials to `business_config.json` for desired platforms
2. Adding platform name to `marketing.platforms` array
3. System posts to Reddit + any enabled optional platforms

---

## Architecture

```
business/backend/routes/content_marketing.py
    ↓ (generates content)
    ↓
backend/core/posting.py
    ↓ (posts to platforms)
    ↓
Reddit, Twitter, LinkedIn, Facebook
```

**Separation of Concerns:**
- **Posting engine** = generic infrastructure (never changes)
- **Content generator** = business logic (Claude builds per business from INTAKE Tier 3)

---

## Setup (Hero)

### 1. Install Dependencies

Already in `requirements.txt`:
```
praw>=7.7.0           # Reddit
tweepy>=4.14.0        # Twitter
linkedin-api>=2.2.0   # LinkedIn
facebook-sdk>=3.1.0   # Facebook
```

### 2. Get Platform Credentials

**Reddit:**
1. Go to https://www.reddit.com/prefs/apps
2. Create app (script type)
3. Get `client_id`, `client_secret`
4. Use your Reddit username/password

**Discord:**
1. Open your Discord server
2. Go to Channel Settings → Integrations → Webhooks
3. Click "New Webhook"
4. Copy the Webhook URL (format: `https://discord.com/api/webhooks/ID/TOKEN`)
5. Paste into config

**Twitter:**
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create app (read + write permissions)
3. Get API keys and access tokens

**LinkedIn:**
1. Use your LinkedIn email/password
2. (Note: This is unofficial API - consider official API for production)

**Facebook:**
1. Go to https://developers.facebook.com/tools/explorer/
2. Get Page Access Token
3. Get your Page ID

### 3. Configure Platforms in `business_config.json`

**Reddit is MANDATORY. All others are optional.**

**Step 1: Add credentials for platforms you want:**

```json
{
  "social_media": {
    "reddit": {
      "_comment": "MANDATORY",
      "client_id": "YOUR_REDDIT_CLIENT_ID",
      "client_secret": "YOUR_REDDIT_CLIENT_SECRET",
      "username": "your_reddit_username",
      "password": "your_reddit_password",
      "user_agent": "YourBusinessName/1.0"
    },
    "discord": {
      "_comment": "OPTIONAL - only add if you want Discord",
      "webhook_url": "https://discord.com/api/webhooks/ID/TOKEN"
    },
    "twitter": {
      "_comment": "OPTIONAL - only add if you want Twitter",
      "api_key": "YOUR_TWITTER_API_KEY",
      "api_secret": "YOUR_TWITTER_API_SECRET",
      "access_token": "YOUR_ACCESS_TOKEN",
      "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET"
    }
  }
}
```

**Step 2: Enable platforms in marketing section:**

```json
{
  "marketing": {
    "enabled": true,
    "platforms": ["reddit", "discord", "twitter"]
  }
}
```

**Examples:**

```json
// Minimum - Reddit only
"platforms": ["reddit"]

// Reddit + Discord
"platforms": ["reddit", "discord"]

// Reddit + all optional platforms
"platforms": ["reddit", "discord", "twitter", "linkedin", "facebook"]
```

**CRITICAL:**
- Reddit MUST have credentials configured
- Reddit MUST post successfully or entire operation fails
- Optional platforms with missing credentials are skipped (logged as warning)
- Optional platforms that fail don't block other platforms

See `docs/SOCIAL_MEDIA_CONFIG.json` for full example.

---

## Usage

### Python API

```python
from core.posting import (
    post_to_reddit, 
    post_to_discord,
    post_to_twitter, 
    post_twitter_thread
)

# Post to Reddit
result = post_to_reddit(
    title="Daily Tips",
    content="Here's today's advice...",
    subreddit="yoursubreddit"
)

# Post to Discord (simple text)
result = post_to_discord(
    content="Daily update is live! 🏀 Check it out!"
)

# Post to Discord (rich embed)
result = post_to_discord(
    content="Daily Picks",
    embed={
        "title": "Today's Waiver Wire Targets",
        "description": "Top picks for fantasy basketball...",
        "color": 0x00ff00,  # Green
        "fields": [
            {"name": "Player A", "value": "32.5 FP projected", "inline": True},
            {"name": "Player B", "value": "28.1 FP projected", "inline": True}
        ],
        "footer": {"text": "CourtDominion"},
        "timestamp": "2024-01-01T00:00:00.000Z"
    }
)

if result.success:
    print(f"Posted: {result.url}")
else:
    print(f"Error: {result.error}")

# Post to Twitter
result = post_to_twitter(
    content="Check out today's tips! 🔥\n\n#YourHashtag"
)

# Post Twitter thread
results = post_twitter_thread([
    "Thread intro tweet 🧵",
    "1/ First point...",
    "2/ Second point...",
    "3/ Conclusion"
])

# Post to all platforms at once
from core.posting import post_to_all_platforms

results = post_to_all_platforms({
    "reddit": {
        "title": "Daily Update",
        "content": "...",
        "subreddit": "yoursubreddit"
    },
    "discord": {
        "content": "Daily update! 🔥",
        "embed": {
            "title": "Top Picks",
            "description": "Today's targets...",
            "color": 0x00ff00
        }
    },
    "twitter": {
        "content": "..."
    },
    "linkedin": {
        "content": "..."
    }
})

for platform, result in results.items():
    if result.success:
        print(f"✓ {platform}: {result.url}")
```

### REST API

Generated routes (in `business/backend/routes/content_marketing.py`):

```
POST /api/content-marketing/publish-daily-content
  → Posts to all configured platforms

POST /api/content-marketing/publish-to-reddit?subreddit=fantasybball
  → Post to Reddit only

POST /api/content-marketing/publish-to-twitter
  → Post to Twitter only

POST /api/content-marketing/publish-to-linkedin
  → Post to LinkedIn only
```

---

## CRON Setup (Automated Posting)

### Daily Posting Schedule

```bash
# Generate content at 5:00 AM
0 5 * * * curl -X POST http://localhost:8000/api/content-marketing/generate-daily-content

# Publish at 5:45 AM (after generation)
45 5 * * * curl -X POST http://localhost:8000/api/content-marketing/publish-daily-content
```

### GitHub Actions (Alternative)

```yaml
# .github/workflows/daily_marketing.yml
name: Daily Marketing Posts

on:
  schedule:
    - cron: '0 5 * * *'  # 5 AM UTC daily
  workflow_dispatch:  # Manual trigger

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - name: Generate and Post Content
        run: |
          curl -X POST ${{ secrets.BACKEND_URL }}/api/content-marketing/publish-daily-content
```

---

## Business-Specific Content Generation

**Claude generates this during BUILD from Tier 3 INTAKE schedule.**

Example INTAKE Tier 3:
```json
{
  "tier3_marketing": {
    "content_type": "waiver_wire_tips",
    "platforms": ["reddit", "twitter", "linkedin"],
    "subreddits": ["fantasybball", "nbadiscussion"],
    "frequency": "daily",
    "post_time": "05:00"
  }
}
```

Claude generates `business/backend/routes/content_marketing.py`:
```python
def generate_waiver_wire_content():
    # Call business data source (DBB2 projections)
    projections = get_projections()
    
    # Filter for deep sleepers
    targets = filter_waiver_targets(projections)
    
    # Generate platform-specific content
    return {
        "reddit_title": "...",
        "reddit_body": "...",
        "twitter_thread": [...],
        "linkedin_post": "..."
    }
```

**For InboxTamer:** `generate_email_productivity_tips()`  
**For FitnessPro:** `generate_workout_tips()`  
**For RecipeFinder:** `generate_recipe_ideas()`

---

## FO vs AF Workflows

### FO (Hero-Run Businesses)

**Tier 1 + 2 only:**
```
Build product → Deploy → No marketing → No traffic
```

**Hero orders Tier 3 (3-month extension):**
```
Build Tier 3 content_marketing.py → Add social credentials → Enable CRON → Traffic starts
```

**Hero pays extra for marketing tier.**

### AF (You-Run Businesses)

**Build all tiers at once:**
```
Build Tier 1 + 2 + 3 → Deploy with marketing enabled → Traffic from day 1
```

**You generate your own traffic automatically.**

---

## Testing

```bash
# Test Reddit posting
curl -X POST http://localhost:8000/api/content-marketing/publish-to-reddit

# Test Twitter posting
curl -X POST http://localhost:8000/api/content-marketing/publish-to-twitter

# Test all platforms
curl -X POST http://localhost:8000/api/content-marketing/publish-daily-content
```

---

## Rate Limits & Best Practices

**Reddit:**
- Max 60 requests per minute
- 1 post per 10 minutes per subreddit (approximate)
- Use relevant subreddits only

**Discord:**
- Webhooks: 30 requests per minute per webhook
- Message length: 2000 characters max
- Embed description: 4096 characters max
- Use embeds for rich formatting
- Consider separate webhooks for different types of content

**Twitter:**
- 300 tweets per 3 hours (100/hour)
- Threads count as separate tweets
- Avoid spam - space out posts

**LinkedIn:**
- 100 posts per day
- Use professional tone
- Focus on insights, not promotion

**General:**
- Post at consistent times
- Provide value, not just promotion
- Engage with comments
- Monitor analytics

---

## Troubleshooting

**"Missing Reddit credentials"**
→ Check `business_config.json` has `social_media.reddit` section

**"praw library not installed"**
→ Run `pip install -r requirements.txt`

**"Invalid access token"**
→ Regenerate tokens in platform developer console

**Posts not showing up**
→ Check platform spam filters, verify credentials, check rate limits

---

## Security

**Never commit credentials to git:**
```gitignore
# .gitignore
business_config.json
.env
```

**Use environment variables in production:**
```python
# backend/core/posting.py reads from business_config.json
# which can load from ENV vars:

import os
config = {
    "reddit": {
        "client_id": os.getenv("REDDIT_CLIENT_ID"),
        ...
    }
}
```

---

## File Structure

```
saas-boilerplate/
├── backend/
│   ├── core/
│   │   └── posting.py              ← Generic posting engine (boilerplate)
│   └── requirements.txt            ← Includes praw, tweepy, etc.
├── business/
│   └── backend/
│       ├── routes/
│       │   └── content_marketing.py  ← Business content (Claude generates)
│       └── routes_examples/
│           └── content_marketing_example.py  ← Template
└── docs/
    ├── TIER3_MARKETING.md          ← This file
    └── SOCIAL_MEDIA_CONFIG.json    ← Config template
```

---

## Next Steps

1. **Get platform credentials** from Reddit, Twitter, LinkedIn, Facebook
2. **Add to `business_config.json`**
3. **Test posting** with manual curl commands
4. **Set up CRON** for automated daily posts
5. **Monitor analytics** to optimize content and timing
