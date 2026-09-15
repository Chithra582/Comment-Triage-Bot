---
name: comment-triage
description: Ingest YouTube comments, classify into actionable categories, and compute priority scores.
---

# Comment Triage Skill

## Instructions
1. Parse YouTube Video URL or 11-character Video ID.
2. Ingest top-level comment threads and engagement metadata.
3. Batch comments (15-20 per batch) and classify into:
   - `question`
   - `sponsor_pitch`
   - `spam`
   - `toxic`
   - `positive`
   - `negative`
4. Calculate composite priority score using engagement leverage and recency freshness decay.
5. Return structured JSON with classification, confidence, and reasoning.
