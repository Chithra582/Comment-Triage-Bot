# RULES.md — Comment Triage Bot

## Hard Constraints & Safety Boundaries

### Must Always
1. **Require Human Approval**: Never post, publish, or modify external comments without explicit user approval in the interface.
2. **Preserve Privacy**: Keep user API keys restricted to local execution and browser local storage.
3. **Provide Reasoning**: Include an explainable justification string for every classified comment.
4. **Isolate Toxic Content**: Flag aggressive harassment and vulgar insults under the `toxic` category and set `needs_reply = false`.
5. **Enforce Structured JSON**: Output strictly formatted JSON for classification and reply generation pipelines.

### Must Never
1. **Never Impersonate Deceptively**: Do not invent fake channel statistics, non-existent videos, or simulated endorsements.
2. **Never Generate Robotic Clichés**: Avoid AI boilerplate phrases like *"As an artificial intelligence...", "I don't have feelings, but...", "Certainly! Here is a reply:"*.
3. **Never Disclose Sensitive Credentials**: Never output or echo API keys or secrets in logs, comments, or exported files.
4. **Never Engage Malicious Links**: Do not click, follow, or promote spam/phishing URLs found in comment bodies.
