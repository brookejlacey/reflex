---
name: triage
description: "Incident first responder that classifies severity, gathers context from logs, metrics, and alerts, and produces a structured triage report to bootstrap the Reflex pipeline."
metadata:
  slash-command: enabled
---

# Triage

## Overview

The Triage skill is the entry point of the Reflex incident response pipeline. It acts as an automated first responder: ingesting raw incident signals (alerts, error logs, user reports, pipeline failures), classifying severity, gathering surrounding context, and producing a structured triage report that downstream skills consume.

Triage does not attempt to fix anything. Its job is to reduce mean-time-to-understanding by answering three questions as fast as possible:

1. **What is broken?** -- Affected services, endpoints, or pipelines.
2. **How bad is it?** -- Severity classification (SEV-1 through SEV-4).
3. **What do we know so far?** -- Relevant logs, recent deploys, related issues, and on-call context.

## Invocation

### As a slash command

```
/triage <incident-description-or-alert-url>
```

### Standalone

```
reflex triage --input "Production 500 errors spiking on /api/payments since 14:32 UTC"
```

### As part of the Reflex pipeline

Triage runs automatically when an incident is opened. Its output is passed to the `root-cause` skill.

## Inputs

| Input | Required | Description |
|---|---|---|
| `incident` | Yes | Free-text description, alert URL, or issue reference |
| `logs` | No | Raw log snippets or log query to execute |
| `timeframe` | No | Time window to scope the investigation (default: last 1 hour) |
| `environment` | No | Target environment (`production`, `staging`, `development`) |

## Outputs

A structured **Triage Report** containing:

- **Incident ID** -- Generated or linked to an existing issue.
- **Severity** -- `SEV-1` (critical, customer-facing outage), `SEV-2` (degraded service), `SEV-3` (minor impact), `SEV-4` (cosmetic / low urgency).
- **Affected Components** -- Services, repos, pipelines, and infrastructure involved.
- **Timeline** -- Ordered list of events leading up to the incident.
- **Evidence** -- Log excerpts, error samples, metric snapshots.
- **Recent Changes** -- Commits, MRs, and deployments in the timeframe.
- **Initial Hypothesis** -- Best-guess failure mode to guide root-cause analysis.

## Behavior

1. **Signal Ingestion** -- Parse the incident input. If a URL is provided, fetch the alert or issue body. If raw text, extract keywords and error signatures.
2. **Context Gathering** -- Search Git history for recent merges to affected components. Query CI/CD pipeline status. Collect relevant log lines.
3. **Severity Classification** -- Apply the severity matrix:
   - Customer-facing outage or data loss -> SEV-1
   - Degraded performance or partial outage -> SEV-2
   - Non-critical feature broken, workaround exists -> SEV-3
   - Cosmetic issue, no functional impact -> SEV-4
4. **Report Generation** -- Assemble findings into the triage report format and emit it for the next pipeline stage.

## Example Usage

```
/triage Pipeline #48201 failed on main — deploy job exited with code 137 (OOMKilled)

# Output:
# Triage Report
# Severity: SEV-2
# Affected: deploy stage, production pipeline
# Evidence: Container killed by OOM at 512Mi limit during asset compilation
# Recent Changes: MR !934 added uncompressed image assets (merged 2h ago)
# Hypothesis: Memory budget exceeded due to new unoptimized assets
```

## Role in the Reflex Pipeline

```
[ Triage ] --> Root Cause --> Fix --> Validation --> Deploy --> Postmortem
    ^                                                              |
    |____________________ feedback loop ___________________________|
```

Triage is the first skill invoked. Every other skill depends on its output for scoping and prioritization. If triage misclassifies severity, escalation rules ensure a human reviewer is pulled in before the pipeline proceeds past the fix stage.
