# Reflex Demo Video Script

**Duration:** 3 minutes
**Format:** Screen recording with voiceover
**Resolution:** 1920x1080, 60fps
**Tone:** Confident, technical, fast-paced. No filler. Every second earns the next.

---

## 0:00 – 0:05 | The Hook

**SCREEN:** Black screen. White monospace text fades in, line by line:

```
It's 2 AM.
Your phone buzzes.
Pipeline failed. Production is down.
You've seen this bug before.
But nobody wrote the postmortem.
```

A beat. The text clears. New line:

```
What if your repository remembered?
```

**CUT TO:** Reflex logo + tagline: *Your repository's immune system.*

---

## 0:05 – 0:20 | The Incident

**SCREEN:** GitLab pipeline view — **Pipeline #8341** shows green for `build`, red X on `test`. Click into the failed job. The traceback scrolls into view:

```
TypeError: 'NoneType' object is not subscriptable
  File "app.py", line 91, in list_users
```

**[ANNOTATION]:** `MR !247 merged yesterday — "Optimize user listing to reduce memory allocation"`

**NARRATION:**

> "A developer shipped an optimization. CI passed on seeded data. But when the database returns zero results, `users[0]` is `None`. The service crashes. Twenty-three users already hit this in production."

**[ANNOTATION]:** `This is where Reflex takes over.`

---

## 0:20 – 0:35 | Knowledge Graph Lookup

**SCREEN:** GitLab issue auto-created. First comment appears from `@reflex-bot`:

```
## Knowledge Graph Lookup
Searching organizational memory... 3 past incidents indexed.

MATCH FOUND — 87% similarity to INC-001:
  "Payment API 500 errors on empty cart checkout"
  Root cause: Unsafe direct dict/attribute access on nullable
  Pattern: object[index] without None/empty check
  Fix strategy: Guard access with empty check

Recommendation: This is a RECURRENCE of a known pattern.
  Apply the same fix strategy that resolved INC-001.
```

**[ANNOTATION — highlight the similarity score]:** `Reflex remembers. It's seen this pattern before.`

**NARRATION:**

> "Before any analysis begins, Reflex checks its knowledge graph — a persistent record of every past incident. It finds an 87 percent match to a payment API crash from two weeks ago. Same pattern: unsafe access on a nullable value. Reflex already knows what to do."

---

## 0:35 – 0:50 | Triage with Knowledge Context

**SCREEN:** Second comment appears:

```
## Triage Report
Severity: P2 — Service degradation (ESCALATED: recurring pattern)
Blast radius: All clients calling GET /api/users with empty filters
Knowledge insight: This is the 2nd occurrence of pattern
  "Unsafe direct dict/attribute access on nullable"
  First seen in INC-001 (payment-api). Pattern was not
  fully hardened across the codebase.
GCP Cloud Logging: 23 matching errors in last 6 hours
Priority: IMMEDIATE
```

**NARRATION:**

> "Triage is faster because of organizational memory. Reflex knows this pattern has recurred — it escalates severity and flags the gap: the codebase was never fully hardened after the first incident."

---

## 0:50 – 1:25 | Root Cause and Challenger Debate

**This is the money shot. Split screen or sequential comments showing the debate.**

**SCREEN:** Third comment — Root Cause Agent:

```
## Root Cause Hypothesis
Breaking commit: a3f7c91 (MR !247, @chen.wei, 2026-03-14)
File: src/demo/app.py, lines 90-92
Mechanism: Null-safety omission — accessing properties on
  None when user list is empty
Evidence:
  - Line 90: first_user = users[0] if users else None
  - Line 91: response["newest_user"] = first_user["name"]  ← CRASH
  - users is empty list when no filter matches
Knowledge graph match: Identical to INC-001 pattern
Confidence: HIGH
Fix strategy: Add null guard before dict access
```

**[ANNOTATION]:** `Root Cause proposes. Now the Challenger tests it.`

**SCREEN:** Fourth comment — Challenger Agent:

```
## Debate Protocol — Challenger Analysis

Challenge 1: "Is this the ONLY crash path?"
  Claim: Root cause is line 91, first_user["name"]
  Counter-evidence: Verified. Line 92 (first_user["email"])
    would also crash — TWO crash paths, not one.
  Resolution: CONFIRMED + EXPANDED. Both lines need the guard.

Challenge 2: "Could this come from a different source?"
  Claim: Breaking commit is a3f7c91
  Counter-evidence: Checked git blame. No other recent changes
    to this function. The commit introduced both lines.
  Resolution: CONFIRMED.

Challenge 3: "Does the fix strategy cover all cases?"
  Claim: Add null guard before dict access
  Counter-evidence: The original fix strategy only mentions
    line 91. Line 92 has the same vulnerability.
  Resolution: REFINED — fix must guard BOTH lines 91 and 92.

╔══════════════════════════════════════════╗
║  VERDICT: CONFIRMED                      ║
║  Refined confidence: HIGH (98%)          ║
║  Root cause verified through adversarial ║
║  testing. Fix strategy expanded.         ║
╚══════════════════════════════════════════╝
```

**NARRATION:**

> "This is what makes Reflex different. The Root Cause Agent proposes a hypothesis. Then the Challenger Agent — an adversarial second opinion — independently reads the code, pokes holes, and tests alternatives. Here, it confirmed the root cause but caught that the fix strategy was incomplete: two crash paths, not one. The debate resolves to confirmed with 98 percent confidence. No single-pass analysis catches this."

---

## 1:25 – 1:50 | Fix, Validate, Deploy (Quick Montage)

**SCREEN:** Rapid cascade of comments. Show each for 3-4 seconds:

**Fix Agent:**
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

**[ANNOTATION]:** `Debate-informed: fixes BOTH crash paths the Challenger identified`

**Validation Agent:**
```
## Validation — PASSED
3 regression tests added:
  - test_list_users_empty_db
  - test_list_users_no_filter_match
  - test_list_users_with_results
SAST scan: PASSED
```

**Deploy Agent:**
```
MR !251 created: "Fix: guard against empty user list in list_users"
Pipeline: ALL GREEN
Labels: reflex::auto-fix, priority::high
Status: Ready for human review
```

**NARRATION:**

> "Fix, validate, deploy — in seconds. The fix addresses both crash paths the Challenger found. Three regression tests. Security scan clean. Merge request ready for one-click approval."

---

## 1:50 – 2:10 | Postmortem + Knowledge Graph Update

**SCREEN:** Postmortem comment on the issue, then zoom into the knowledge graph update:

```
## Postmortem — Incident #8341
Timeline:
  2026-03-14 14:22 — MR !247 merged (introduced bug)
  2026-03-16 08:15 — First error in Cloud Logging
  2026-03-16 09:41 — Pipeline #8341 fails
  2026-03-16 09:42 — Reflex triggered
  2026-03-16 09:43 — Knowledge graph: 87% match to INC-001
  2026-03-16 09:44 — Debate protocol: CONFIRMED (98%)
  2026-03-16 09:47 — MR !251 created with fix

RECURRENCE DETECTED: This is the 2nd occurrence of pattern
  "Unsafe direct dict/attribute access on nullable"
```

**SCREEN:** Cut to the actual JSON being updated — show the knowledge graph file:

```json
{
  "incident_id": "INC-003",
  "title": "TypeError in user-service list_users on empty results",
  "patterns": [{
    "pattern_id": "a1b2c3d4e5f6",
    "name": "Unsafe direct dict/attribute access on nullable",
    "recurrence_count": 2
  }],
  "debate_verdict": "confirmed",
  "debate_confidence": "high"
}
```

**[ANNOTATION — on the JSON]:** `This is how Reflex LEARNS. Every incident updates the knowledge graph.`

**NARRATION:**

> "The Postmortem Agent writes the blameless report — and then does something no other system does: it updates the knowledge graph. This incident becomes organizational memory. The pattern's recurrence count goes to 2. Next time Reflex sees this pattern, it will be even faster."

---

## 2:10 – 2:30 | Sentinel: Predictive Prevention

**SCREEN:** Cut to a completely new scene. A developer opens a new merge request: **MR !260 — "Add premium user tier with exclusive content"**

The diff shows:

```python
premium_users = get_premium_users(tier="gold")
featured = premium_users[0]["display_name"]
```

A comment appears from `@reflex-sentinel`:

```
## Sentinel Predictive Analysis: HIGH RISK — Review Required

Reflex has seen this before. This merge request contains code
that matches a pattern from 2 past incidents:

| File | Pattern | Past Incident | Risk |
|------|---------|---------------|------|
| premium.py:14 | Unsafe direct access on nullable | INC-001, INC-003 | HIGH |

This EXACT pattern caused:
  - INC-001: Payment API 500 errors (critical, 2026-03-02)
  - INC-003: user-service TypeError (high, 2026-03-16)

Recommendation: Add a guard check before accessing
  premium_users[0]. If the query returns no gold-tier
  users, this line will crash.

This MR has been flagged for mandatory review.
```

**[ANNOTATION]:** `The bug that HASN'T happened yet — caught before it merges.`

**NARRATION:**

> "But here is where it gets powerful. A week later, a different developer submits a new MR. Sentinel — Reflex's predictive prevention flow — scans the diff against the knowledge graph and warns: this code matches the exact pattern that caused incidents 001 and 003. The bug is caught BEFORE it reaches production. Reflex did not just heal — it built immunity."

---

## 2:30 – 2:45 | Dashboard + Sustainability

**SCREEN:** Flash the incident dashboard — show a clean visualization with:

- MTTR trend line dropping from 3 hours to 5 minutes
- Incident count by severity (bar chart)
- Pattern recurrence heatmap
- Active Sentinel warnings
- Knowledge graph stats: 3 incidents, 5 patterns, 1 recurrence detected

**SCREEN:** Sustainability comparison card:

```
Sustainability Report — Incident #8341
  Agent steps: 8 | Tokens: ~18,000
  Reflex carbon: ~12g CO2
  Manual response: ~750g CO2 (est. 3 person-hours)
  Carbon reduction: 98.4%

  Carbon-aware scheduling: Active
  Agents scheduled during low-grid-intensity windows
```

**NARRATION:**

> "Every run is tracked. Reflex reports its carbon footprint versus a traditional manual response — and the carbon-aware scheduler runs agents during low-intensity grid windows when possible. This incident: 98.4 percent carbon reduction."

---

## 2:45 – 3:00 | The Close

**SCREEN:** Clean slide with key stats appearing one by one:

```
17 agents across 4 orchestrated flows
Adversarial debate protocol for verified root causes
Persistent knowledge graph — organizational memory
Predictive prevention — catches bugs before they merge
Cross-project intelligence — one fix, every project
Carbon-aware scheduling — sustainable AI operations
MTTR: 2–4 hours  →  5 minutes
```

**NARRATION:**

> "Reflex is 17 agents across 4 flows. It triages, debates, fixes, validates, deploys, documents, hardens, predicts, and protects — across every project in your organization. It learns from every incident and prevents the next one before the code is ever merged."

**SCREEN:** Reflex logo. Tagline fades in:

> *Your repository's immune system.*

**NARRATION:**

> "Reflex. Built on GitLab Duo Agent Platform. Powered by Anthropic Claude. Integrated with Google Cloud. And it gets smarter every time it runs."

**SCREEN:** GitLab repo URL + team info. Fade to black.

---

## Production Notes

**Pacing:** The demo has three acts: (1) Memory + Triage is fast and confident, (2) the Debate Protocol section is the centerpiece — give it room to breathe, (3) Sentinel is the dramatic payoff. Everything after Sentinel is quick hits.

**Screen recordings needed:**
1. GitLab pipeline view (failed pipeline #8341)
2. GitLab issue with knowledge lookup comment
3. GitLab issue with triage comment
4. GitLab issue with root cause + challenger debate comments (the money shot)
5. GitLab issue with fix/validation/deploy cascade
6. GitLab issue with postmortem + knowledge graph JSON
7. GitLab MR view with Sentinel warning (new MR !260)
8. Dashboard visualization (can be a polished mockup or live page)
9. Sustainability comparison card
10. Closing stats slide

**The debate section (0:50-1:25):** This is 35 seconds and the most important part of the demo. Show the Root Cause comment appearing, then a brief pause, then the Challenger comment appearing with its structured challenges and verdict box. The viewer should feel the adversarial tension resolving into confidence.

**Annotations style:** Use minimal, high-contrast callout boxes (white text on dark semi-transparent background). Position them consistently in the top-right or as inline pointers. Do not clutter the screen.

**Music:** Low, driving electronic track. Builds during the debate section. Swells when the verdict box appears. Drops to ambient during Sentinel reveal. Clean resolution for closing.

**Do NOT include:** Long pauses, "um"s, webcam footage, or slides with walls of text. Every frame should show the product working.
