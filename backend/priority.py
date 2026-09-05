import math
from datetime import datetime, timezone
from typing import List
from .models import RawComment, ClassificationResult, TriagedComment, CommentCategory


def calculate_priority_score(comment: RawComment, classification: ClassificationResult) -> tuple[float, str]:
    """
    Computes priority score (0-100+) based on:
    1. Engagement leverage (likes + reply count)
    2. Recency freshness (hours since published)
    3. Category urgency (sponsor pitch > question > constructive negative > positive)
    """
    score = 0.0

    # 1. Engagement Leverage
    # Log-scaled like count: 10 likes -> ~12 pts, 50 likes -> ~20 pts, 100 likes -> ~23 pts
    likes = max(0, comment.like_count)
    replies = max(0, comment.reply_count)
    score += math.log1p(likes) * 6.5
    score += math.log1p(replies) * 4.0

    # 2. Recency Freshness
    now = datetime.now(timezone.utc)
    try:
        # Parse ISO timestamp
        pub_date = datetime.fromisoformat(comment.published_at.replace("Z", "+00:00"))
        age_hours = max(0.1, (now - pub_date).total_seconds() / 3600.0)
    except Exception:
        age_hours = 12.0

    # Fast exponential decay on recency: replying in the first 24h yields max YouTube algorithmic boost
    if age_hours <= 3:
        score += 35.0
    elif age_hours <= 12:
        score += 25.0
    elif age_hours <= 24:
        score += 18.0
    elif age_hours <= 72:
        score += 10.0
    else:
        score += 4.0

    # 3. Category Urgency
    cat_weights = {
        CommentCategory.SPONSOR_PITCH: 35.0,  # High business value
        CommentCategory.QUESTION: 25.0,       # High audience retention & engagement
        CommentCategory.NEGATIVE: 18.0,       # Service recovery / timely clarification
        CommentCategory.POSITIVE: 8.0,        # Community relationship
        CommentCategory.SPAM: 0.0,
        CommentCategory.TOXIC: 0.0
    }
    score += cat_weights.get(classification.category, 5.0)

    # Round score
    final_score = round(score, 1)

    # Determine priority tier
    if not classification.needs_reply:
        label = "Low"
    elif final_score >= 55.0:
        label = "High"
    elif final_score >= 35.0:
        label = "Medium"
    else:
        label = "Low"

    return final_score, label


def rank_and_combine_comments(
    raw_comments: List[RawComment],
    classifications: List[ClassificationResult]
) -> List[TriagedComment]:
    """
    Combines raw comment data with classification results,
    computes priority scores, and ranks them with needs_reply + high priority first.
    """
    class_map = {c.comment_id: c for c in classifications}
    triaged: List[TriagedComment] = []

    for raw in raw_comments:
        cls = class_map.get(raw.id)
        if not cls:
            continue
        
        priority_score, priority_label = calculate_priority_score(raw, cls)

        triaged.append(TriagedComment(
            id=raw.id,
            text=raw.text,
            author=raw.author,
            author_profile_image=raw.author_profile_image,
            like_count=raw.like_count,
            reply_count=raw.reply_count,
            published_at=raw.published_at,
            video_id=raw.video_id,
            needs_reply=cls.needs_reply,
            category=cls.category,
            confidence=cls.confidence,
            reasoning=cls.reasoning,
            priority_score=priority_score,
            priority_label=priority_label,
            draft_reply=None
        ))

    # Sort primarily: needs_reply (True before False), then priority_score descending
    triaged.sort(key=lambda x: (x.needs_reply, x.priority_score), reverse=True)
    return triaged
