# EXPLAINABILITY.md — Comment Triage Bot

This document provides a comprehensive explanation of how **Comment Triage Bot** functions, detailing its decision-making mechanisms, data consumption, and operational limitations in accordance with the OpenGAP spec.

---

## 1. How the Agent Decides

Comment Triage Bot uses a coordinated two-stage LLM and algorithmic decision pipeline:

```
[Raw YouTube Comment]
       │
       ▼
[Stage 1: Batch LLM Classification] ──► Category, Needs Reply, Confidence, Reasoning
       │
       ▼
[Algorithmic Priority Scoring Engine] ──► Priority Score (0–100+) & Tier (High/Med/Low)
       │
       ▼
(Does comment warrant reply?)
  ├── Yes ──► [Stage 2: Style-Matched LLM Drafter] ──► First-Person Creator Draft
  └── No  ──► Muted / Stored in Category Bucket (Spam/Toxic/Positive)
```

### 1.1 Category Classification Rubric
The agent evaluates each incoming comment against six distinct functional categories:
1. **`question`**: Genuine viewer inquiries, technical debugging requests, tutorial clarification, or video timestamp questions. Flagged as `needs_reply = true`.
2. **`sponsor_pitch`**: Commercial collaboration, PR team outreach, brand sponsorship offers, or product review unit pitches. Flagged as `needs_reply = true`.
3. **`spam`**: Cryptocurrency airdrops, external contact solicitation (Telegram/WhatsApp bots), phishing links, or automated spam copypasta. Flagged as `needs_reply = false`.
4. **`toxic`**: Direct personal abuse, aggressive insults, hate speech, or harassment directed at the creator. Flagged as `needs_reply = false`.
5. **`negative`**: Constructive technical critique, complaints regarding audio/visual production quality, or respectful disagreements. Flagged as `needs_reply = true` when polite and constructive.
6. **`positive`**: Encouragement, general compliments, or expressions of gratitude. Flagged as `needs_reply = false` (unless containing an embedded question).

### 1.2 Confidence Scoring & Reasoning
- The classification engine produces a confidence score $\in [0.0, 1.0]$ for each assignment.
- A concise, human-readable justification (`reasoning`) is generated alongside each prediction to provide full transparency in the creator dashboard.

### 1.3 Priority Scoring Algorithm
To ensure creators respond to high-leverage interactions first rather than chronological noise, the agent calculates a composite **Priority Score**:

$$\text{Priority Score} = \text{Engagement Score} + \text{Recency Freshness} + \text{Category Weight}$$

Where:
- **Engagement Score**: $6.5 \cdot \ln(1 + \text{likes}) + 4.0 \cdot \ln(1 + \text{replies})$. Highly liked comments indicate topics many viewers want answered.
- **Recency Freshness**: Exponential decay bonus to capitalize on the YouTube algorithm's engagement momentum:
  - $\le 3\text{ hours}$: $+35\text{ points}$
  - $\le 12\text{ hours}$: $+25\text{ points}$
  - $\le 24\text{ hours}$: $+18\text{ points}$
  - $\le 72\text{ hours}$: $+10\text{ points}$
  - $> 72\text{ hours}$: $+4\text{ points}$
- **Category Urgency**:
  - `sponsor_pitch`: $+35\text{ points}$ (High commercial value)
  - `question`: $+25\text{ points}$ (Audience retention)
  - `negative`: $+18\text{ points}$ (Timely clarification & reputation management)
  - `positive`: $+8\text{ points}$
  - `spam` / `toxic`: $0\text{ points}$

Comments with scores $\ge 55$ are labeled **High Priority**, $35–54$ are **Medium Priority**, and $< 35$ are **Low Priority**.

### 1.4 Style-Matched Reply Drafting
When `needs_reply == true`, a second prompt is constructed using few-shot learning:
- **Voice Persona**: Parameters governing formality, concise vs. verbose explanations, and emoji density.
- **Few-Shot Seeding**: 2–3 past comment replies authored by the creator are injected as style references.
- **Output Constraint**: First-person ("I", "we"), authentic, context-specific responses avoiding generic assistant phrases (*"As an AI..."*).

---

## 2. The Data It Uses

### 2.1 Inputs Ingested
1. **Comment Data**:
   - Comment text (UTF-8 string).
   - Author display name and profile avatar URI.
   - Like count and total reply count.
   - Published timestamp (ISO 8601 UTC).
   - Comment ID and Parent Video ID.
2. **Video Context**:
   - Video title and channel name.
   - View count, total likes, and total comment count.
3. **Creator Preferences**:
   - Selected persona (*Friendly & Concise*, *High Energy Hype*, *Deep Tech*, or *Business Executive*).
   - Optional few-shot examples of typical creator responses.

### 2.2 Data Sourcing & Privacy
- All ingested data is public data fetched via the official YouTube Data API v3 (`videos` and `commentThreads.list`).
- The agent does not read private messages, personal account data, or unlisted/private user details.
- User API keys are stored locally within the user's browser environment or `.env` file and are never transmitted to third-party tracking services.

---

## 3. Limitations & Safeguards

### 3.1 Limitations
- **Sarcasm and Cultural Nuances**: Highly sarcastic or ironic viewer comments can occasionally be miscategorized as purely positive or toxic.
- **API Quota Constraints**: YouTube Data API v3 applies default quota limits (10,000 units/day). Large channels analyzing thousands of comments per hour may require quota elevation from Google Cloud.
- **Nested Comment Depth**: The current pipeline prioritizes top-level comment threads. Deep multi-turn reply chains are evaluated based on top-level relevance and reply counts.

### 3.2 Safeguards & Human-in-the-Loop
- **Strict Human Editorial Control**: The bot **never automatically posts** responses live to YouTube without explicit creator action. Drafts are presented in an editable UI where creators can review, modify, copy, or approve.
- **Toxicity Isolation**: Toxic and spam comments are sequestered into separate filtered views, preventing creator burnout while keeping actionable feedback visible.
- **Deterministic Heuristic Fallback**: If an LLM API experiences an outage, rate limiting, or network interruption, the agent falls back to a deterministic rule-based heuristic classifier, ensuring uninterrupted triage operations.
