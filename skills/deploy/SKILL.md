---
name: deploy
description: "Creates merge requests, monitors CI/CD pipeline execution, and prepares validated fixes for production deployment."
metadata:
  slash-command: enabled
---

# Deploy

## Overview

The Deploy skill handles the final logistics of getting a validated fix into production. It creates a merge request with full context, monitors the CI/CD pipeline, and manages the deployment workflow. Deploy does not push directly to production -- it prepares everything so that a merge (manual or auto-merge) results in a clean, traceable deployment.

## Invocation

### As a slash command

```
/deploy <validation-report-or-branch>
```

### Standalone

```
reflex deploy --branch fix/invoice-nil-guard --target main --auto-merge enabled
```

### As part of the Reflex pipeline

Automatically receives the validation report from the `validation` skill and passes deployment metadata to the `postmortem` skill.

## Inputs

| Input | Required | Description |
|---|---|---|
| `validation_report` | Yes | Structured output from the validation skill, or a branch reference |
| `target` | No | Target branch for the merge request (default: `main`) |
| `auto_merge` | No | Enable auto-merge when pipeline passes: `enabled` or `disabled` (default: `disabled`) |
| `reviewers` | No | GitLab usernames to assign as reviewers |
| `labels` | No | Labels to apply to the MR (default: `reflex,incident-fix`) |
| `priority` | No | MR priority: `critical` (expedited review), `normal` (default) |

## Outputs

- **Merge Request** -- URL and metadata for the created MR.
- **Pipeline Status** -- Real-time status of the CI/CD pipeline triggered by the MR.
- **Deployment Checklist** -- Pre-deployment verification items.
- **Rollback Plan** -- Steps to revert the change if post-deploy issues arise.

## Behavior

### 1. Branch Preparation

- Ensure the fix branch is up to date with the target branch.
- Rebase if necessary to produce a clean history.
- Verify no merge conflicts exist.

### 2. Merge Request Creation

Create a merge request with a structured description:

```markdown
## Incident Fix

**Incident:** <incident-id>
**Severity:** <severity>
**Root Cause:** <summary with link to analysis>

## Changes

<description of what the patch does and why>

## Validation

- Unit tests: PASS
- Integration tests: PASS
- Security scan: CLEAR
- Coverage: <percentage> on changed lines

## Rollback

To revert this change:
git revert <commit-sha>
```

### 3. Pipeline Monitoring

Monitor the MR pipeline in real time:

- Track each stage (build, test, security, deploy-staging).
- Report failures immediately with log context.
- If the pipeline fails on an unrelated flaky test, identify it and note it separately.

### 4. Deployment Readiness

When the pipeline passes, prepare the deployment:

- For `auto_merge: enabled` -- Enable GitLab's auto-merge feature.
- For `auto_merge: disabled` -- Notify reviewers and provide a one-click merge prompt.
- For `priority: critical` -- Tag the MR as expedited and ping on-call reviewers.

### 5. Post-Merge Monitoring

After the MR is merged:

- Monitor the deployment pipeline.
- Watch for error rate changes in the first 10 minutes.
- If error rates spike, trigger the rollback plan and alert.

## Example Usage

```
/deploy --branch fix/invoice-nil-guard --auto-merge enabled --priority critical

# Output:
# Merge Request Created
# URL: https://gitlab.com/org/billing/merge_requests/947
# Title: "Fix: Restore nil guard on subscription lookup (SEV-2)"
# Labels: reflex, incident-fix, critical
# Reviewers: @oncall-backend
# Auto-merge: enabled (will merge when pipeline passes)
#
# Pipeline Status:
#   build:     PASSED (42s)
#   unit:      PASSED (2m 18s)
#   security:  PASSED (1m 04s)
#   staging:   RUNNING...
#
# Rollback Plan:
#   git revert abc1234 && git push origin main
```

## Merge Request Conventions

- **Title format:** `Fix: <short description> (<severity>)`
- **Labels:** Always include `reflex` and `incident-fix`. Add severity label (`sev-1`, `sev-2`, etc.).
- **Description:** Always include the incident link, root cause summary, validation results, and rollback instructions.
- **Assignee:** The on-call engineer or the engineer who authored the breaking change.
- **Reviewers:** At least one reviewer from the affected team's CODEOWNERS.

## Role in the Reflex Pipeline

```
Triage --> Root Cause --> Fix --> Validation --> [ Deploy ] --> Postmortem
```

Deploy is the bridge between "fix verified" and "fix in production." It ensures traceability by linking the MR to the incident, the root cause analysis, and the validation report. After deployment completes, it hands off timing and metadata to the Postmortem skill.
