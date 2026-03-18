# Reflex Demo Video Script

**Duration:** 3 minutes
**Format:** Screen recording with voiceover
**Resolution:** 1920x1080, 60fps
**Tone:** Confident, technical, fast-paced. No filler. Every second earns the next.

---

## 0:00 – 0:20 | The Hook

**SCREEN:** Black screen. A single terminal cursor blinks. Then, in large monospace text, a pipeline failure notification appears line by line:

```
PIPELINE #8341 FAILED
Stage: test
Job: unit-tests
Project: acme/user-service
```

A beat of silence. Then the text clears and a new line appears:

```
Reflex has entered the chat.
```

**NARRATION:**

> "Every engineering team knows this feeling. The pipeline breaks. Slack lights up. Someone drops what they're doing, digs through logs, writes a fix, adds tests, creates a merge request, writes a postmortem. Two to four hours gone — if you're lucky."
>
> "What if your repository could heal itself?"

**CUT TO:** Reflex logo + tagline: *Autonomous Incident-to-Fix Pipeline for GitLab.*

---

## 0:20 – 0:50 | The Problem

**SCREEN:** GitLab merge request view showing **MR !247** — *"Optimize user listing to reduce memory allocation"*

**[ANNOTATION — top right corner]:** `This MR was approved and merged yesterday.`

**NARRATION:**

> "Here's a real scenario. A developer ships an optimization to the user listing endpoint — PR 247. It pre-allocates a response dict and attaches summary stats from the first record. The code review looked fine. CI passed on the seeded test data."

**SCREEN:** Zoom into the code diff. Highlight lines 90–92 of `app.py`:

```python
first_user = users[0] if users else None
response["newest_user"] = first_user["name"]      # BUG
response["newest_email"] = first_user["email"]
```

**[ANNOTATION — red callout on line 91]:** `TypeError: NoneType is not subscriptable — when no users match the filter`

**NARRATION:**

> "But there's a subtle bug. When the database returns empty results — no users match the filter — `first_user` is `None`. Accessing `None["name"]` crashes the service. This morning, an integration test with an empty filter hit it."

**SCREEN:** GitLab pipeline view — **Pipeline #8341** shows green for `build`, red X on `test`. Click into the failed job. The traceback scrolls into view:

```
TypeError: 'NoneType' object is not subscriptable
  File "app.py", line 91, in list_users
```

**[ANNOTATION]:** `This is where Reflex takes over.`

---

## 0:50 – 2:20 | Reflex In Action

**SCREEN:** GitLab issue auto-created: **"Pipeline #8341 failure: TypeError in user-service list_users"**

**NARRATION:**

> "Reflex triggers automatically on pipeline failure. Nine specialized agents across two orchestrated flows — powered by Anthropic Claude through the GitLab AI Gateway. Watch."

### Agent 1: Triage (0:55 – 1:10)

**SCREEN:** A comment appears on the issue from `@reflex-bot`:

```
## Triage Report
Severity: P2 — Service degradation
Affected service: user-service (api/users endpoint)
Blast radius: All clients calling GET /api/users with filters
              returning zero results
Error: TypeError at app.py:91 — NoneType subscript access
GCP Cloud Logging: 23 matching errors in last 6 hours
```

**[ANNOTATION — beside the GCP line]:** `Google Cloud Logging integration — pulls correlated errors automatically`

**NARRATION:**

> "The Triage Agent classifies severity, identifies the blast radius, and pulls correlated errors from Google Cloud Logging. Twenty-three users already hit this in production."

### Agent 2: Root Cause (1:10 – 1:25)

**SCREEN:** A second comment appears:

```
## Root Cause Analysis
Breaking commit: a3f7c91 (PR #247, @chen.wei, 2026-03-14)
File: src/demo/app.py, lines 90-92
Cause: Null-safety omission — accessing properties on a
       None value when the user list is empty
Confidence: 98%
```

**NARRATION:**

> "Root Cause Agent does git archaeology — blame, diff analysis, change correlation. It pinpoints commit `a3f7c91` from PR 247, lines 90 through 92. Confidence: 98 percent."

### Agent 3: Fix (1:25 – 1:40)

**SCREEN:** A third comment with a code diff:

```diff
- first_user = users[0] if users else None
- response["newest_user"] = first_user["name"]
- response["newest_email"] = first_user["email"]
+ if users:
+     response["newest_user"] = users[0]["name"]
+     response["newest_email"] = users[0]["email"]
+ else:
+     response["newest_user"] = None
+     response["newest_email"] = None
```

**NARRATION:**

> "The Fix Agent generates a minimal, safe patch. It doesn't rewrite the function — it adds a null guard that matches the existing code style. Surgical."

### Agent 4: Validation (1:40 – 1:55)

**SCREEN:** A fourth comment:

```
## Validation
New regression tests added:
  - test_list_users_empty_db → verifies empty result handling
  - test_list_users_no_filter_match → verifies filter with zero matches
  - test_list_users_with_results → confirms existing behavior preserved
SAST scan: PASSED (no new vulnerabilities)
```

**NARRATION:**

> "Validation Agent writes three regression tests — including the exact edge case that caused the crash — and runs a security scan. All green."

### Agent 5: Deploy (1:55 – 2:08)

**SCREEN:** GitLab merge request view: **MR !251 — "Fix: guard against empty user list in list_users endpoint"**

Show the MR contents: the code fix plus the new test file. Pipeline status: all stages green.

**[ANNOTATION]:** `Fix + tests + passing pipeline — ready for human review`

**NARRATION:**

> "The Deploy Agent creates a merge request with the fix and the tests in a single commit. The pipeline runs — and passes. It's ready for one-click human approval."

### Agent 6: Postmortem (2:08 – 2:20)

**SCREEN:** Back on the issue. A long, structured comment:

```
## Postmortem — Incident #8341
Timeline:
  2026-03-14 14:22 — PR #247 merged
  2026-03-16 08:15 — First error in Cloud Logging
  2026-03-16 09:41 — Pipeline #8341 fails
  2026-03-16 09:42 — Reflex triggered
  2026-03-16 09:47 — MR !251 created with fix

Root cause: Missing null check on empty query results
Contributing factor: No test coverage for empty-state scenarios
Follow-up: Harden all database access patterns (auto-created)

Sustainability Report:
  Agent steps: 6 | Tokens: ~12,400 | Energy: ~8g CO2
  vs. manual response: ~750g CO2 (est. 3 person-hours)
  Savings: 98.9% carbon reduction
```

**[ANNOTATION — on sustainability section]:** `Green Agent prize — every run tracks its carbon footprint`

**NARRATION:**

> "The Postmortem Agent produces a blameless report with a full timeline, root cause summary, and follow-up actions. And at the bottom — sustainability metrics. This five-minute automated response saved an estimated 98.9 percent in carbon versus a manual incident."

---

## 2:20 – 2:45 | The Hardening Flow

**SCREEN:** A new merge request appears: **MR !252 — "Harden: add null guards to 4 similar database access patterns"**

Show the diff — multiple files with similar null-safety fixes.

**NARRATION:**

> "But Reflex doesn't stop at the fix. The Hardening Flow kicks in — three more agents that extract the vulnerability pattern, scan the entire codebase for similar code, and create a preventive merge request. MR 252 patches four other endpoints with the same missing null guard. Bugs that haven't happened yet — prevented."

**SCREEN:** Quick montage of the two flow diagrams from the README:

- Main flow: Triage -> Root Cause -> Fix -> Validation -> Deploy -> Postmortem
- Harden flow: Pattern Extract -> Codebase Scan -> Preventive Fix

**[ANNOTATION]:** `9 agents. 2 flows. Fully autonomous. Each agent also works as a standalone GitLab Duo skill.`

---

## 2:45 – 3:00 | The Close

**SCREEN:** Clean slide with key stats:

```
MTTR: 2–4 hours  →  5 minutes
Agents: 9 across 2 orchestrated flows
LLM: Anthropic Claude via GitLab AI Gateway
Infra: Google Cloud Logging + Monitoring
Carbon: 98.9% reduction vs. manual response
Each agent: also a standalone /reflex-* skill
```

**NARRATION:**

> "Reflex turns your GitLab repository into a self-healing system. Nine agents, two flows, zero human intervention required. It detects, diagnoses, fixes, validates, deploys, documents, and hardens — in minutes, not hours."

**SCREEN:** Reflex logo. Tagline fades in:

> *Your repository's immune system.*

**NARRATION:**

> "Reflex. Built on GitLab Duo Agent Platform. Powered by Anthropic Claude. Integrated with Google Cloud. And it gets better every time it runs."

**SCREEN:** GitLab repo URL + team info. Fade to black.

---

## Production Notes

**Pacing:** The entire middle section (0:50–2:20) should feel like a cascade — each agent's comment appearing shortly after the last, building momentum. Use subtle transition sounds or a progress indicator showing which agent is active.

**Screen recordings needed:**
1. GitLab MR view (the original PR #247)
2. GitLab pipeline view (failed pipeline #8341)
3. GitLab issue with agent comments appearing sequentially
4. GitLab MR view (the fix MR !251)
5. GitLab MR view (the hardening MR !252)
6. Architecture diagram slides (two flow diagrams)
7. Closing stats slide

**Annotations style:** Use minimal, high-contrast callout boxes (white text on dark semi-transparent background). Position them consistently in the top-right or as inline pointers. Do not clutter the screen.

**Music:** Low, driving electronic track. Builds slightly during the agent cascade. Drops out for the closing statement.

**Do NOT include:** Long pauses, "um"s, webcam footage, or slides with walls of text. Every frame should show the product working.
