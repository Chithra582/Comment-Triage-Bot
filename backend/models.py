from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CommentCategory(str, Enum):
    QUESTION = "question"
    SPAM = "spam"
    SPONSOR_PITCH = "sponsor_pitch"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    TOXIC = "toxic"


class RawComment(BaseModel):
    id: str
    text: str
    author: str
    author_channel_url: Optional[str] = ""
    author_profile_image: Optional[str] = ""
    like_count: int = 0
    reply_count: int = 0
    published_at: str
    video_id: str


class ClassificationResult(BaseModel):
    comment_id: str
    needs_reply: bool
    category: CommentCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class DraftReplyResult(BaseModel):
    comment_id: str
    draft_reply: str
    tone_used: str


class TriagedComment(BaseModel):
    id: str
    text: str
    author: str
    author_profile_image: Optional[str] = ""
    like_count: int = 0
    reply_count: int = 0
    published_at: str
    video_id: str
    needs_reply: bool
    category: CommentCategory
    confidence: float
    reasoning: str
    priority_score: float = 0.0
    priority_label: str = "Medium"  # High, Medium, Low
    draft_reply: Optional[str] = None
    is_approved: bool = False
    is_copied: bool = False


class AnalyzeRequest(BaseModel):
    video_url_or_id: str
    api_key_youtube: Optional[str] = None
    api_key_llm: Optional[str] = None
    llm_provider: Optional[str] = "auto"  # auto, openai, anthropic, gemini, local
    max_comments: Optional[int] = 50
    creator_style: Optional[str] = "friendly_concise"  # friendly_concise, energetic_emojis, deep_tech, custom
    custom_style_prompt: Optional[str] = None
    past_replies: Optional[List[str]] = None


class DraftRequest(BaseModel):
    comment_id: str
    comment_text: str
    author: str
    category: str
    creator_style: Optional[str] = "friendly_concise"
    custom_style_prompt: Optional[str] = None
    past_replies: Optional[List[str]] = None
    api_key_llm: Optional[str] = None
    llm_provider: Optional[str] = "auto"


class ApproveRequest(BaseModel):
    comment_id: str
    draft_reply: str
    post_live: Optional[bool] = False


class VideoMetadata(BaseModel):
    video_id: str
    title: str
    channel_title: str
    view_count: Optional[int] = 0
    like_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    thumbnail_url: Optional[str] = ""
