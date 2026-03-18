---
name: postmortem
description: "Generates blameless incident reports, creates follow-up issues for systemic improvements, and tracks sustainability metrics across the Reflex pipeline."
metadata:
  slash-command: enabled
---

# Postmortem

## Overview

The Postmortem skill closes the loop on every incident handled by the Reflex pipeline. It produces a blameless incident report, files follow-up issues for systemic improvements, and computes sustainability metrics that track how the team and codebase are trending over time.

Postmortems are not about blame. They are about learning. This skill focuses on systemic causes, process gaps, and actionable improvements rather than individual mistakes.

## Invocation

### As a slash command

```
/postmortem <incident-id-or-deploy-report>
```

### Standalone

```
reflex postmortem --incident INC-2847 --format markdown --follow-ups enabled
```

### As part of the Reflex pipeline

Automatically receives deployment metadata from the `deploy` skill. This is the final stage of the standard Reflex flow.

## Inputs

| Input | Required | Description |
|---|---|---|
| `incident` | Yes | Incident ID or the full pipeline context from previous skills |
| `format` | No | Output format: `markdown` (default), `gitlab-issue`, `notion` |
| `follow_ups` | No | Auto-create follow-up issues: `enabled` (default) or `disabled` |
| `metrics` | No | Include sustainability metrics: `enabled` (default) or `disabled` |

## Outputs

### Incident Report

A structured blameless postmortem containing:

- **Summary** -- One-paragraph description of what happened.
- **Timeline** -- Minute-by-minute chronology from detection to resolution.
- **Impact** -- Users affected, duration of degradation, revenue impact if applicable.
- **Root Cause** -- Technical explanation (sourced from the root-cause skill).
- **Resolution** -- What was done to fix it (sourced from the fix and deploy skills).
- **Detection** -- How the incident was discovered and time-to-detection.
- **Contributing Factors** -- Systemic issues that allowed the defect to reach production.
- **Lessons Learned** -- What went well, what didn't, and what was lucky.
- **Action Items** -- Concrete follow-ups with owners and due dates.

### Follow-Up Issues

Automatically created GitLab issues for each action item:

- Add missing test coverage for the affected code path.
- Improve monitoring or alerting for the failure mode.
- Address contributing factors (e.g., flaky tests, missing code review checklist items).
- Harden similar patterns across the codebase (triggers the `harden` skill).

### Sustainability Metrics

Tracked per-incident and aggregated over time:

| Metric | Description |
|---|---|
| **MTTD** | Mean Time to Detection -- how long before the incident was noticed |
| **MTTR** | Mean Time to Resolution -- total time from detection to production fix |
| **Fix Accuracy** | Percentage of Reflex fixes that resolved the incident on the first attempt |
| **Recurrence Rate** | How often the same class of defect reappears |
| **Follow-Up Completion** | Percentage of postmortem action items completed within SLA |
| **Pipeline Health** | Trend of CI/CD pass rates over time |

## Behavior

### 1. Data Collection

Gather the full incident context from all preceding pipeline stages:

- Triage report (severity, affected components)
- Root cause analysis (culprit commit, confidence)
- Fix details (patch, strategy, risk)
- Validation results (test outcomes, coverage)
- Deploy metadata (MR URL, pipeline duration, merge time)

### 2. Timeline Construction

Build a chronological timeline:

```
14:32 UTC  Error rate increase detected by monitoring
14:34 UTC  Triage skill activated, classified SEV-2
14:36 UTC  Root cause identified: commit a3f8e21 (confidence: high)
14:38 UTC  Fix generated: nil guard restoration
14:41 UTC  Validation passed (unit + integration)
14:43 UTC  MR !947 created, pipeline started
14:52 UTC  Pipeline passed, MR merged
14:54 UTC  Deployment complete, error rates normalized
```

### 3. Impact Assessment

Quantify the incident's impact:

- Duration of degradation
- Number of affected users or requests
- Failed transactions or data inconsistencies
- SLA impact

### 4. Contributing Factor Analysis

Look beyond the immediate root cause to identify systemic issues:

- Why did the breaking change pass code review?
- Why was there no test for the nil case?
- Was monitoring adequate for this failure mode?
- Did the deployment process have appropriate safeguards?

### 5. Follow-Up Issue Creation

For each identified action item, create a GitLab issue:

- Title: `[Postmortem INC-XXXX] <action item>`
- Labels: `postmortem`, `follow-up`, severity label
- Assignee: Suggested owner based on CODEOWNERS
- Due date: Based on severity (SEV-1 items: 1 week, SEV-2: 2 weeks, etc.)

### 6. Metrics Computation

Calculate incident-level metrics and update rolling aggregates.

## Example Usage

```
/postmortem INC-2847

# Output:
# Postmortem: INC-2847 -- Payment Invoice Nil Reference
#
# Summary: A nil guard was removed from the invoice calculation path,
# causing 500 errors for users without active subscriptions.
#
# Timeline: (22 minutes total)
#   14:32 Detection | 14:36 Root Cause | 14:41 Fix Validated | 14:54 Resolved
#
# Impact: ~340 users received 500 errors over 22 minutes. No data loss.
# MTTD: 2 minutes | MTTR: 22 minutes
#
# Follow-ups created:
#   #1204 - Add nil subscription test coverage to billing module
#   #1205 - Add billing endpoint error rate alert (< 5 min detection)
#   #1206 - Run /harden on nil-guard patterns across codebase
#
# Sustainability: MTTR trending down (was 45min avg, now 28min avg)
```

## Role in the Reflex Pipeline

```
Triage --> Root Cause --> Fix --> Validation --> Deploy --> [ Postmortem ]
    ^                                                           |
    |________________________ feedback loop _____________________|
```

Postmortem is the final stage and the learning engine. Its follow-up issues feed back into the team's backlog, and its metrics provide visibility into whether the incident response process is improving over time. It may also trigger the `harden` skill to proactively scan for similar vulnerabilities.
