# EXPLAINABILITY.md

This document explains the internal mechanisms, data lineage, and operational boundaries of **Comment Triage Bot** in accordance with the OpenGAP specification.

---

## How the Agent Decides

Comment Triage Bot makes decisions through a deterministic two-stage pipeline combining structured LLM evaluation with an algorithmic priority scoring model.

### 1. Decision Architecture
The decision process flows through two sequential stages:

```
Raw Comment
    │
    ▼
[Stage 1: Batch LLM Classification]
    │  - Evaluates intent against 6 discrete categories
    │  - Decides boolean: needs_reply (true/false)
    │  - Generates confidence score (0.0 – 1.0)
    │  - Formulates transparent reasoning justification
    ▼
[Priority Scoring Algorithm]
    │  - Computes composite priority score based on engagement, recency, and category
    │  - Assigns priority tier: High, Medium, or Low
    ▼
(Branching Decision: Does comment require reply?)
    ├── True  ──► [Stage 2: Style-Matched Response Drafter]
    │                 - Injects creator voice persona & few-shot past examples
    │                 - Generates tailored first-person draft reply
    │                 - Routes to Human-in-the-Loop review queue
    └── False ──► Categorized and stored into filtered buckets (Spam, Toxic, Positive)
```

### 2. Classification Rubric & Decision Criteria
The agent classifies each comment into one of six distinct categories using explicit criteria:

- **`question` (`needs_reply: true`)**: Viewer inquiries asking for technical clarification, help with code, timestamp queries, or tutorials. The agent prioritizes these to build community trust.
- **`sponsor_pitch` (`needs_reply: true`)**: Inquiries from brands, marketing agencies, or collaborators offering sponsorships, partnerships, or PR review units. The agent routes these as high-leverage commercial opportunities.
- **`negative` (`needs_reply: true` when constructive)**: Viewer critique regarding audio/video quality, disagreeing technical perspectives, or constructive feedback. The agent flags these for polite creator clarification.
- **`positive` (`needs_reply: false`)**: General viewer appreciation, compliments, or emojis. The agent acknowledges these without requiring creator action unless a question is embedded.
- **`spam` (`needs_reply: false`)**: Bot-generated promotions, cryptocurrency giveaways, WhatsApp/Telegram solicitations, and phishing links. The agent isolates these to protect viewers.
- **`toxic` (`needs_reply: false`)**: Hate speech, profanity, harassment, or personal attacks. The agent quarantines these to shield the creator from emotional burnout.

### 3. Confidence Scoring & Reasoning Output
- For every comment, the model outputs a confidence score between `0.0` and `1.0`.
- The model outputs an explicit `reasoning` string explaining why the classification was made. This string is displayed on the creator dashboard for complete decision transparency.

### 4. Priority Scoring Formula
To ensure creators answer high-leverage comments first, the agent applies an algorithmic ranking formula:

$$\text{Priority Score} = \text{Engagement Score} + \text{Recency Freshness} + \text{Category Weight}$$

- **Engagement Score**: $6.5 \cdot \ln(1 + \text{likes}) + 4.0 \cdot \ln(1 + \text{replies})$. Comments with high upvotes indicate widespread viewer interest.
- **Recency Freshness Bonus**:
  - $\le 3\text{ hours}$: $+35\text{ points}$
  - $\le 12\text{ hours}$: $+25\text{ points}$
  - $\le 24\text{ hours}$: $+18\text{ points}$
  - $\le 72\text{ hours}$: $+10\text{ points}$
  - $> 72\text{ hours}$: $+4\text{ points}$
- **Category Urgency Weight**:
  - `sponsor_pitch`: $+35\text{ points}$ (High commercial value)
  - `question`: $+25\text{ points}$ (High retention value)
  - `negative`: $+18\text{ points}$ (Service recovery)
  - `positive`: $+8\text{ points}$
  - `spam` / `toxic`: $0\text{ points}$

Comments scoring $\ge 55$ are assigned **High Priority**, $35–54$ **Medium Priority**, and $< 35$ **Low Priority**.

### 5. Fallback Decision Mechanism
If the primary LLM API (OpenAI or Claude) is unreachable or times out, the agent falls back to a deterministic rule-based heuristic classifier utilizing regex pattern matching for spam URLs, sponsor keywords, and question marks. This ensures zero downtime.

### 6. Human-in-the-Loop Governance
The agent acts solely as an advisory drafting system. **It never publishes directly to YouTube without creator review.** The creator can inspect the AI reasoning, edit the draft response, copy it to the clipboard, or mark it as approved.

---

## The Data It Uses

Comment Triage Bot operates strictly on public data and creator-provided preferences.

### 1. Ingested Input Data
The agent consumes data directly from the YouTube Data API v3 (`videos` and `commentThreads.list` endpoints):
- **Comment Body**: UTF-8 plain text string of the viewer's comment.
- **Comment Metadata**: Comment ID, published timestamp (ISO 8601), and last updated timestamp.
- **Engagement Metrics**: Upvote/like count and nested reply count.
- **Author Information**: Author display name, channel URL, and public avatar image URL.
- **Video Context**: Video ID, video title, channel title, view count, total like count, and total comment count.

### 2. Creator Configuration Data
To calibrate drafting style, the agent uses:
- **Voice Persona**: Selected creator archetype (*Friendly & Concise*, *High Energy Hype*, *Deep Tech Expert*, or *Business Executive*).
- **Style Guidelines**: Instructions governing tone, sentence brevity, and emoji frequency.
- **Past Reply Reference Data**: 2–3 authentic past replies written by the creator, injected as few-shot examples into the drafting prompt.

### 3. Training & Base Model Data
- The agent utilizes pre-trained frontier foundation models (such as OpenAI `gpt-4o-mini` or Anthropic `claude-3-5-haiku-20241022`).
- No proprietary models are trained from scratch. The agent relies on in-context learning and structured output schemas.

### 4. Data Privacy, Storage, and Retention
- **No Private Data Access**: The agent accesses only public comments and video metadata. It does not access private messages, unlisted videos, or watch history.
- **Local Credentials**: User API keys (YouTube API key, OpenAI key, Anthropic key) are stored solely in the user's browser local storage or local `.env` file. Keys are never sent to external tracking servers.
- **Stateless Operation**: Comments and drafts are processed in memory during the active session. Analysis reports can be exported locally by the creator as CSV or JSON files.

---

## Limitations

Understanding the operational boundaries and constraints of Comment Triage Bot is critical for safe deployment.

### 1. Linguistic and Contextual Limitations
- **Sarcasm and Satire**: Highly sarcastic or ironic comments may occasionally be misclassified as positive compliments or toxic remarks.
- **Subtle Cultural Nuances & Slang**: Emerging internet slang, regional dialects, or multilingual comments outside the base model's high-resource training languages may result in lower confidence scores.
- **Short or Ambiguous Comments**: One-word comments (e.g., *"why"*, *"nah"*, *"lol"*) contain minimal context, causing the agent to default to conservative low-priority classifications.

### 2. Architectural & Operational Boundaries
- **Top-Level Scope**: The ingestion pipeline focuses primarily on top-level comment threads. Deeply nested multi-level discussion trees are not evaluated recursively.
- **YouTube API Rate Limits**: YouTube Data API v3 has a default quota of 10,000 units per day. High-volume channels analyzing tens of thousands of comments simultaneously may encounter quota limits.
- **Batch Boundary Independence**: Comments are evaluated in batches of 15–20. While this drastically reduces latency and API costs, comments that refer back to a comment in an earlier batch are evaluated independently.

### 3. Hallucination and Factuality Safeguards
- **Channel Specifics**: The LLM does not have real-time access to the creator's private repository or personal schedule. If a viewer asks *"When is video #3 coming out?"*, the draft reply acknowledges the question politely but leaves date specifics for the creator to confirm.
- **Mandatory Human Review**: Because language models can occasionally hallucinate technical details, the agent enforces a strict Human-in-the-Loop design: no reply is ever auto-submitted to YouTube without human editorial approval.

### 4. Content Moderation Limitations
- **Legal Compliance**: The agent's toxicity classification is an assistance tool, not a legal filter. It is not designed to replace formal legal compliance or child safety reporting pipelines.
- **Evolving Spam Vectors**: Malicious actors constantly invent obfuscated links or zero-width characters. While common patterns are caught, novel obfuscation methods may occasionally bypass filters.

---

## Summary & Compliance Checklist

| Checkpoint 2 Requirement | Corresponding Section | Status |
| :--- | :--- | :---: |
| **How the agent decides** | [How the Agent Decides](#how-the-agent-decides) | **Covered** |
| - Decision architecture & taxonomy | Section 1 & 2 | Verified |
| - Confidence scoring & priority ranking | Section 3 & 4 | Verified |
| - Fallback & human-in-the-loop gates | Section 5 & 6 | Verified |
| **The data it uses** | [The Data It Uses](#the-data-it-uses) | **Covered** |
| - Ingested comment & video metadata | Section 1 | Verified |
| - Creator configuration & few-shot data | Section 2 | Verified |
| - Data privacy & local credentials | Section 4 | Verified |
| **Its limitations** | [Limitations](#limitations) | **Covered** |
| - Linguistic & sarcasm boundaries | Section 1 | Verified |
| - API quotas & architectural limits | Section 2 | Verified |
| - Hallucination safeguards & human review | Section 3 & 4 | Verified |
