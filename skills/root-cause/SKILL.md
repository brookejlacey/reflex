---
name: root-cause
description: "Git detective that traces breaking changes through commit history, blame analysis, and code archaeology to identify the exact cause of an incident."
metadata:
  slash-command: enabled
---

# Root Cause

## Overview

The Root Cause skill is the investigative core of the Reflex pipeline. Given a triage report, it performs systematic code archaeology -- walking Git history, analyzing blame, diffing deployments, and correlating changes with failure signatures -- to pinpoint the exact commit, line, or configuration change that caused the incident.

This skill thinks like a detective. It starts with the symptoms, builds a timeline of suspects (recent changes), and narrows the field through evidence until it can make a confident attribution.

## Invocation

### As a slash command

```
/root-cause <triage-report-or-incident-id>
```

### Standalone

```
reflex root-cause --component api/payments --error "NullReferenceException at line 142" --since "2h ago"
```

### As part of the Reflex pipeline

Automatically receives the triage report from the `triage` skill and passes its findings to the `fix` skill.

## Inputs

| Input | Required | Description |
|---|---|---|
| `triage_report` | Yes | Structured output from the triage skill, or an incident ID to look up |
| `component` | No | Specific file, module, or service to focus on |
| `since` | No | How far back to search Git history (default: 7 days) |
| `depth` | No | Max number of commits to traverse (default: 100) |

## Outputs

A structured **Root Cause Analysis** containing:

- **Culprit Commit** -- The SHA, author, timestamp, and MR reference of the change that introduced the defect.
- **Culprit File(s)** -- Exact file paths and line ranges responsible.
- **Diff Summary** -- What changed and why it broke things.
- **Confidence** -- `high`, `medium`, or `low` based on evidence strength.
- **Evidence Chain** -- Step-by-step reasoning linking the commit to the failure.
- **Contributing Factors** -- Other changes or conditions that made the defect possible (missing tests, config drift, dependency updates).

## Behavior

1. **Scope Identification** -- From the triage report, identify affected files, services, and error signatures.
2. **Blame Analysis** -- Run `git blame` on affected files. Identify which commits last touched the failing lines.
3. **History Walking** -- Traverse `git log` for the affected paths within the timeframe. Rank commits by relevance using:
   - Proximity to failure time
   - Number of lines changed in affected files
   - Whether the commit touched test files (or didn't)
4. **Diff Inspection** -- For top candidate commits, analyze the full diff. Look for:
   - Removed nil/null checks
   - Changed function signatures
   - Modified configuration values
   - New dependencies or version bumps
5. **Bisect Logic** -- If multiple candidates remain, apply logical bisection: determine which commit, if reverted, would resolve the failure.
6. **Correlation** -- Cross-reference with CI pipeline results. Did the candidate commit's pipeline pass? Were there skipped or flaky tests?
7. **Report Assembly** -- Produce the root cause analysis with full evidence chain.

## Example Usage

```
/root-cause --component lib/billing/invoice.rb --error "undefined method 'total' for nil:NilClass"

# Output:
# Root Cause Analysis
# Confidence: high
# Culprit: commit a3f8e21 by @dev (MR !891, merged 4h ago)
# File: lib/billing/invoice.rb:142
# Change: Removed nil-guard on `current_subscription` lookup
# Evidence: git blame shows line 142 was last modified in a3f8e21.
#           The previous version had `return unless current_subscription`.
#           The new version calls `.total` directly without the guard.
#           Error signature matches: NoMethodError on NilClass.
# Contributing: No test coverage for the nil-subscription path.
```

## Investigation Strategies

The skill employs multiple strategies depending on the situation:

- **Direct Blame** -- When the failing line is known, blame it directly.
- **Changelog Sweep** -- When the failure is behavioral, sweep recent changes to the affected module.
- **Dependency Audit** -- When the error comes from a library, check Gemfile.lock / package-lock.json / Cargo.lock diffs.
- **Config Archaeology** -- When infrastructure is involved, check environment variables, CI/CD configs, and deployment manifests.

## Role in the Reflex Pipeline

```
Triage --> [ Root Cause ] --> Fix --> Validation --> Deploy --> Postmortem
```

Root Cause receives the triage report and produces the analysis that the Fix skill needs to generate a targeted patch. A high-confidence root cause leads to an automated fix attempt. A low-confidence result triggers a human review checkpoint before proceeding.
