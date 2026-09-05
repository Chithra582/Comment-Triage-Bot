import os
import json
import re
from typing import List, Dict, Any, Optional
from .models import RawComment, ClassificationResult, CommentCategory

# Classification System Prompt
CLASSIFICATION_SYSTEM_PROMPT = """You are an expert YouTube Comment Triage Assistant for creators.
Your job is to classify YouTube comments into specific actionable categories so the creator can respond to important comments, filter spam, and flag abuse.

For each comment, output a JSON array of objects with the exact schema:
[
  {
    "comment_id": "string",
    "needs_reply": true/false,
    "category": "question" | "spam" | "sponsor_pitch" | "positive" | "negative" | "toxic",
    "confidence": float between 0.0 and 1.0,
    "reasoning": "brief 1-sentence justification"
  }
]

Categories definition:
- "question": Genuine viewer questions, technical doubts, requests for tutorials, timestamps inquiries. Needs reply = true.
- "sponsor_pitch": Business collaboration offers, brand sponsorships, paid integration inquiries, marketing team outreach. Needs reply = true.
- "spam": Crypto scams, telegram/whatsapp recruitment, fake giveaways, bot copypasta, suspicious URLs. Needs reply = false.
- "toxic": Harassment, hate speech, vulgar abuse, aggressive personal insults directed at creator. Needs reply = false.
- "negative": Constructive criticism, sound issues, differing technical opinion, mild dissatisfaction. Needs reply = creator's choice (set true if polite/constructive, false if just a complaint).
- "positive": Compliments, gratitude, hype, generic love for the video. Needs reply = false (unless asking something).
"""


def classify_comments_batch(
    comments: List[RawComment],
    api_key_llm: Optional[str] = None,
    provider: str = "auto",
    batch_size: int = 20
) -> List[ClassificationResult]:
    """
    Classifies a list of RawComment in batches.
    Auto-detects available LLM provider or uses local heuristic fallback.
    """
    if not comments:
        return []

    resolved_provider, resolved_key = _resolve_provider(api_key_llm, provider)
    results: List[ClassificationResult] = []

    for i in range(0, len(comments), batch_size):
        chunk = comments[i : i + batch_size]
        chunk_results = _classify_chunk(chunk, resolved_provider, resolved_key)
        results.extend(chunk_results)

    # Ensure all original comments have a result
    id_map = {r.comment_id: r for r in results}
    final_results = []
    for c in comments:
        if c.id in id_map:
            final_results.append(id_map[c.id])
        else:
            # Fallback heuristic for any missed comment
            final_results.append(_heuristic_classify(c))

    return final_results


def _resolve_provider(api_key: Optional[str], provider: str) -> tuple[str, Optional[str]]:
    openai_key = api_key or os.getenv("OPENAI_API_KEY")
    anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    if provider == "openai" and openai_key:
        return "openai", openai_key
    elif provider == "anthropic" and anthropic_key:
        return "anthropic", anthropic_key
    elif provider == "auto":
        if openai_key and (openai_key.startswith("sk-") or len(openai_key) > 20):
            return "openai", openai_key
        elif anthropic_key and anthropic_key.startswith("sk-ant"):
            return "anthropic", anthropic_key

    return "local", None


def _classify_chunk(
    chunk: List[RawComment],
    provider: str,
    api_key: Optional[str]
) -> List[ClassificationResult]:
    if provider == "openai" and api_key:
        try:
            return _classify_with_openai(chunk, api_key)
        except Exception as e:
            print(f"[OpenAI classification error]: {e}. Falling back to local heuristic.")
            return [_heuristic_classify(c) for c in chunk]
    elif provider == "anthropic" and api_key:
        try:
            return _classify_with_anthropic(chunk, api_key)
        except Exception as e:
            print(f"[Anthropic classification error]: {e}. Falling back to local heuristic.")
            return [_heuristic_classify(c) for c in chunk]
    else:
        return [_heuristic_classify(c) for c in chunk]


def _classify_with_openai(chunk: List[RawComment], api_key: str) -> List[ClassificationResult]:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    payload = [
        {"id": c.id, "author": c.author, "text": c.text, "likes": c.like_count}
        for c in chunk
    ]
    prompt = f"Classify the following {len(chunk)} YouTube comments:\n{json.dumps(payload, indent=2)}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    
    # Handle both top-level list or wrapped key like {"comments": [...]}
    items = parsed if isinstance(parsed, list) else (parsed.get("comments") or parsed.get("results") or list(parsed.values())[0] if parsed else [])

    results: List[ClassificationResult] = []
    for item in items:
        cat_str = item.get("category", "positive").lower().strip()
        try:
            cat = CommentCategory(cat_str)
        except ValueError:
            cat = CommentCategory.QUESTION if "question" in cat_str else CommentCategory.POSITIVE

        results.append(ClassificationResult(
            comment_id=str(item.get("comment_id", "")),
            needs_reply=bool(item.get("needs_reply", False)),
            category=cat,
            confidence=float(item.get("confidence", 0.9)),
            reasoning=str(item.get("reasoning", "Classified by GPT-4o-mini"))
        ))
    return results


def _classify_with_anthropic(chunk: List[RawComment], api_key: str) -> List[ClassificationResult]:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    payload = [
        {"id": c.id, "author": c.author, "text": c.text, "likes": c.like_count}
        for c in chunk
    ]
    prompt = f"{CLASSIFICATION_SYSTEM_PROMPT}\n\nRespond ONLY with valid JSON array of classifications for these comments:\n{json.dumps(payload, indent=2)}"

    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1500,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )
    raw_text = message.content[0].text if message.content else "[]"
    # Extract JSON array
    json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    json_str = json_match.group(0) if json_match else raw_text
    items = json.loads(json_str)

    results: List[ClassificationResult] = []
    for item in items:
        cat_str = item.get("category", "positive").lower().strip()
        try:
            cat = CommentCategory(cat_str)
        except ValueError:
            cat = CommentCategory.POSITIVE

        results.append(ClassificationResult(
            comment_id=str(item.get("comment_id", "")),
            needs_reply=bool(item.get("needs_reply", False)),
            category=cat,
            confidence=float(item.get("confidence", 0.9)),
            reasoning=str(item.get("reasoning", "Classified by Claude 3.5 Haiku"))
        ))
    return results


def _heuristic_classify(comment: RawComment) -> ClassificationResult:
    """
    Intelligent local classification engine with regex and semantic heuristic patterns.
    Ensures the demo runs flawlessly offline and without API rate limits.
    """
    text = comment.text.lower()
    
    # 1. Spam & Scams
    spam_patterns = [
        r'(telegram|t\.me\/|whatsapp|\+1\s?\(\d{3}\)|\+?\d{10,12})',
        r'(crypto|airdrop|usdt|bitcoin|forex|invest with|profit guaranteed|wallet recovery)',
        r'(free money|claim \d+|earn \$\d+ hourly)'
    ]
    for p in spam_patterns:
        if re.search(p, text):
            return ClassificationResult(
                comment_id=comment.id,
                needs_reply=False,
                category=CommentCategory.SPAM,
                confidence=0.96,
                reasoning="Detected external contact scam link or automated promotion pattern."
            )

    # 2. Toxic & Abuse
    toxic_patterns = [
        r'\b(trash|loser|toddler|pathetic|kill yourself|stfu|idiot|clown|shut up|scammer)\b',
        r'\b(delete your channel|worst video ever|you suck)\b'
    ]
    for p in toxic_patterns:
        if re.search(p, text):
            return ClassificationResult(
                comment_id=comment.id,
                needs_reply=False,
                category=CommentCategory.TOXIC,
                confidence=0.94,
                reasoning="Contains hostile sentiment, verbal harassment or abusive phrasing."
            )

    # 3. Sponsor Pitch & Business Collabs
    sponsor_patterns = [
        r'(sponsor|sponsorship|collab|collaboration|partnership|pr team|marketing team)',
        r'(rates and timeline|dedicated integration|budget is \$|send a sample unit|promote our product)'
    ]
    for p in sponsor_patterns:
        if re.search(p, text):
            return ClassificationResult(
                comment_id=comment.id,
                needs_reply=True,
                category=CommentCategory.SPONSOR_PITCH,
                confidence=0.95,
                reasoning="Identified commercial outreach, brand collaboration proposal, or sponsorship inquiry."
            )

    # 4. Genuine Questions
    question_patterns = [
        r'(\?|what happens|how do|can this|is there|why does|would you recommend|where can|how is)',
        r'(at \d+:\d+|line \d+|pydantic|github repo|tutorial|error)'
    ]
    if "?" in text or any(re.search(p, text) for p in question_patterns):
        return ClassificationResult(
            comment_id=comment.id,
            needs_reply=True,
            category=CommentCategory.QUESTION,
            confidence=0.92,
            reasoning="Viewer asking a genuine technical or conceptual question requiring creator response."
        )

    # 5. Constructive / Negative Feedback
    negative_patterns = [
        r'(quiet|audio|volume|too fast|blurry|confusing|disagree|mistake at|fix the)'
    ]
    for p in negative_patterns:
        if re.search(p, text):
            return ClassificationResult(
                comment_id=comment.id,
                needs_reply=True,
                category=CommentCategory.NEGATIVE,
                confidence=0.88,
                reasoning="Constructive critique regarding production quality or technical accuracy."
            )

    # 6. Default: Positive
    return ClassificationResult(
        comment_id=comment.id,
        needs_reply=False,
        category=CommentCategory.POSITIVE,
        confidence=0.91,
        reasoning="Encouraging feedback, viewer compliment, or community appreciation."
    )
