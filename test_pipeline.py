import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.youtube_client import extract_video_id, fetch_youtube_comments
from backend.classifier import classify_comments_batch
from backend.priority import rank_and_combine_comments
from backend.drafter import draft_replies_for_triaged_comments, draft_single_reply

def test_pipeline():
    print("=== 1. Testing Video ID Extractor ===")
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("demo-ai-agent") == "demo-ai-agent"
    print("✓ Video ID extraction passed.")

    print("\n=== 2. Testing YouTube Ingestion Layer ===")
    metadata, comments, is_fallback, fallback_reason = fetch_youtube_comments("demo-ai-agent")
    assert metadata is not None
    assert len(comments) > 0
    print(f"✓ Ingestion passed: '{metadata.title}' with {len(comments)} comments.")

    print("\n=== 3. Testing Classification Engine ===")
    classifications = classify_comments_batch(comments)
    assert len(classifications) == len(comments)
    cat_names = set(c.category.value for c in classifications)
    print(f"✓ Classification passed: Found categories {cat_names}")

    print("\n=== 4. Testing Priority Scoring Engine ===")
    triaged = rank_and_combine_comments(comments, classifications)
    assert len(triaged) == len(comments)
    # Check that highest priority / needs_reply is sorted to top
    assert triaged[0].needs_reply is True
    print(f"✓ Priority ranking passed: Top item priority score = {triaged[0].priority_score} ({triaged[0].priority_label})")

    print("\n=== 5. Testing Style-Matched Response Drafter ===")
    triaged_with_drafts = draft_replies_for_triaged_comments(triaged, creator_style="friendly_concise")
    drafted_count = sum(1 for c in triaged_with_drafts if c.draft_reply is not None)
    assert drafted_count > 0
    print(f"✓ Drafting passed: {drafted_count} replies drafted in creator voice.")
    first_draft = next(c.draft_reply for c in triaged_with_drafts if c.draft_reply)
    print(f"  Sample Draft Reply: \"{first_draft}\"")

    print("\n=== 6. Testing Single Draft On-Demand ===")
    single = draft_single_reply(
        comment_text="Can we use Redis with this?",
        author="Dave",
        category="question",
        creator_style="energetic_emojis"
    )
    assert len(single) > 10
    print(f"✓ Single draft passed: \"{single}\"")

    print("\n=== 7. Testing FastAPI Endpoints ===")
    client = TestClient(app)
    
    # Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    print("✓ GET /api/health passed.")

    # Sample videos
    res_samples = client.get("/api/sample-videos")
    assert res_samples.status_code == 200
    assert len(res_samples.json()["sample_videos"]) >= 2
    print("✓ GET /api/sample-videos passed.")

    # Full Analyze endpoint
    res_analyze = client.post("/api/analyze", json={
        "video_url_or_id": "demo-ai-agent",
        "max_comments": 15,
        "creator_style": "friendly_concise"
    })
    assert res_analyze.status_code == 200
    data = res_analyze.json()
    assert "metadata" in data
    assert "stats" in data
    assert len(data["comments"]) == 15
    print("✓ POST /api/analyze passed.")

    # Export CSV endpoint
    res_export = client.get("/api/export?format=csv")
    assert res_export.status_code == 200
    assert "Comment ID" in res_export.text
    print("✓ GET /api/export?format=csv passed.")

    print("\n🎉 ALL AUTOMATED TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pipeline()
