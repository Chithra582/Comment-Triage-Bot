import os
import io
import csv
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from .models import (
    AnalyzeRequest,
    DraftRequest,
    ApproveRequest,
    TriagedComment,
    VideoMetadata,
    CommentCategory
)
from .youtube_client import fetch_youtube_comments, DEMO_VIDEOS
from .classifier import classify_comments_batch
from .priority import rank_and_combine_comments
from .drafter import (
    draft_replies_for_triaged_comments,
    draft_single_reply,
    STYLE_PERSONAS
)

load_dotenv()

app = FastAPI(
    title="YouTube Comment Triage Bot API",
    description="Automated YouTube Comment Triaging, Classification & Style-Matched Reply Drafting",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for current active session triage results
CURRENT_SESSION: Dict[str, Any] = {
    "metadata": None,
    "comments": []
}


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Comment Triage Bot",
        "has_youtube_key": bool(os.getenv("YOUTUBE_API_KEY")),
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "has_anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY"))
    }


@app.get("/api/sample-videos")
def get_sample_videos():
    """Returns curated demo videos for 1-click testing."""
    samples = []
    for vid_id, data in DEMO_VIDEOS.items():
        meta: VideoMetadata = data["metadata"]
        samples.append({
            "video_id": vid_id,
            "title": meta.title,
            "channel_title": meta.channel_title,
            "thumbnail_url": meta.thumbnail_url,
            "comment_count": len(data["comments"]),
            "view_count": meta.view_count
        })
    return {"sample_videos": samples}


@app.get("/api/styles")
def get_creator_styles():
    """Returns available creator voice personas."""
    return {"styles": STYLE_PERSONAS}


@app.post("/api/analyze")
def analyze_video_comments(req: AnalyzeRequest):
    """
    Main End-to-End Pipeline:
    1. Ingestion: Pulls comments via YouTube Data API v3 (or curated dataset).
    2. Batch Classification: Evaluates category, confidence, needs_reply, reasoning.
    3. Priority Ranking: Calculates leverage score (likes, recency, category).
    4. Style-Matched Drafting: Generates ready-to-copy replies in creator's voice.
    """
    try:
        # Step 1: Ingestion
        metadata, raw_comments, is_fallback, fallback_reason = fetch_youtube_comments(
            video_url_or_id=req.video_url_or_id,
            api_key=req.api_key_youtube,
            max_comments=req.max_comments or 50
        )

        if not raw_comments:
            raise HTTPException(status_code=404, detail="No comments could be retrieved for this video.")

        # Step 2: Batch Classification
        classifications = classify_comments_batch(
            comments=raw_comments,
            api_key_llm=req.api_key_llm,
            provider=req.llm_provider or "auto",
            batch_size=20
        )

        # Step 3: Priority Ranking & Assembly
        triaged = rank_and_combine_comments(raw_comments, classifications)

        # Step 4: Style-Matched Reply Drafting for 'needs_reply' comments
        triaged_with_drafts = draft_replies_for_triaged_comments(
            comments=triaged,
            creator_style=req.creator_style or "friendly_concise",
            custom_style_prompt=req.custom_style_prompt,
            past_replies=req.past_replies,
            api_key_llm=req.api_key_llm,
            provider=req.llm_provider or "auto"
        )

        # Step 5: Compute summary stats
        category_counts = {}
        for c in triaged_with_drafts:
            val = c.category.value
            category_counts[val] = category_counts.get(val, 0) + 1

        needs_reply_count = sum(1 for c in triaged_with_drafts if c.needs_reply)
        spam_count = category_counts.get("spam", 0) + category_counts.get("toxic", 0)
        sponsor_count = category_counts.get("sponsor_pitch", 0)
        question_count = category_counts.get("question", 0)

        # Estimate time saved: avg creator spends 1.5 min per comment triaged manually
        est_minutes_saved = round(len(triaged_with_drafts) * 1.5)

        stats = {
            "total_comments": len(triaged_with_drafts),
            "needs_reply": needs_reply_count,
            "questions": question_count,
            "sponsor_pitches": sponsor_count,
            "spam_and_toxic": spam_count,
            "est_minutes_saved": est_minutes_saved,
            "category_breakdown": category_counts
        }

        # Cache in current session
        CURRENT_SESSION["metadata"] = metadata.dict()
        CURRENT_SESSION["comments"] = [c.dict() for c in triaged_with_drafts]

        return {
            "metadata": metadata,
            "stats": stats,
            "comments": triaged_with_drafts,
            "is_fallback": is_fallback,
            "fallback_reason": fallback_reason
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")


@app.post("/api/draft")
def regenerate_single_draft(req: DraftRequest):
    """Regenerates a single reply draft on-demand with customized tone."""
    try:
        reply = draft_single_reply(
            comment_text=req.comment_text,
            author=req.author,
            category=req.category,
            creator_style=req.creator_style or "friendly_concise",
            custom_style_prompt=req.custom_style_prompt,
            past_replies=req.past_replies,
            api_key_llm=req.api_key_llm,
            provider=req.llm_provider or "auto"
        )
        return {"comment_id": req.comment_id, "draft_reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to draft reply: {str(e)}")


@app.post("/api/approve")
def approve_comment_reply(req: ApproveRequest):
    """Marks a comment reply as approved by creator."""
    # Update status in session
    for c in CURRENT_SESSION.get("comments", []):
        if c.get("id") == req.comment_id:
            c["is_approved"] = True
            c["draft_reply"] = req.draft_reply
            break

    return {
        "status": "approved",
        "comment_id": req.comment_id,
        "message": "Reply approved and ready for publishing."
    }


@app.get("/api/export")
def export_triage_results(format: str = Query("csv", regex="^(csv|json)$")):
    """Exports the latest triaged comments with classifications and draft replies."""
    comments = CURRENT_SESSION.get("comments", [])
    if not comments:
        raise HTTPException(status_code=400, detail="No triage results available to export. Run an analysis first.")

    if format == "json":
        json_data = json.dumps({
            "metadata": CURRENT_SESSION.get("metadata"),
            "triaged_comments": comments
        }, indent=2)
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=comment_triage_results.json"}
        )

    # Export CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Comment ID", "Author", "Comment Text", "Likes", "Category",
        "Needs Reply", "Priority Score", "Priority Tier", "Confidence",
        "Reasoning", "Draft Reply", "Approved"
    ])

    for c in comments:
        writer.writerow([
            c.get("id"),
            c.get("author"),
            c.get("text"),
            c.get("like_count"),
            c.get("category"),
            c.get("needs_reply"),
            c.get("priority_score"),
            c.get("priority_label"),
            c.get("confidence"),
            c.get("reasoning"),
            c.get("draft_reply") or "",
            c.get("is_approved", False)
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=comment_triage_results.csv"}
    )


# Mount frontend static directory
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
