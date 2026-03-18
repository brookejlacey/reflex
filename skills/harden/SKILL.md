---
name: harden
description: "Proactively scans the codebase for vulnerability patterns similar to a resolved incident, identifies at-risk code, and generates preventive fixes before they become production incidents."
metadata:
  slash-command: enabled
---

# Harden

## Overview

The Harden skill is the proactive arm of the Reflex pipeline. While the standard flow is reactive (incident happens, pipeline responds), Harden goes on the offensive: given a known vulnerability pattern from a resolved incident, it sweeps the entire codebase for similar weaknesses and generates preventive fixes before they cause their own incidents.

Harden turns every incident into a codebase-wide improvement. One nil-guard bug found means every similar nil-guard gap gets identified and patched.

## Invocation

### As a slash command

```
/harden <pattern-description-or-postmortem-id>
```

### Standalone

```
reflex harden --pattern "nil guard missing before method call on optional association" --scope lib/
```

### Triggered by the Postmortem skill

When a postmortem identifies a systemic pattern, it automatically triggers a hardening pass as a follow-up.

### As a scheduled scan

```
reflex harden --mode sweep --categories nil-safety,error-handling,auth-checks
```

## Inputs

| Input | Required | Description |
|---|---|---|
| `pattern` | Yes | Description of the vulnerability pattern to scan for, or a postmortem/incident ID to extract the pattern from |
| `scope` | No | Directory or file glob to limit the scan (default: entire repository) |
| `mode` | No | `targeted` (single pattern, default) or `sweep` (multiple pattern categories) |
| `categories` | No | For sweep mode: comma-separated list of vulnerability categories |
| `auto_fix` | No | Generate fixes for findings: `enabled` (default) or `report-only` |
| `severity_threshold` | No | Minimum severity to report: `critical`, `high`, `medium` (default), `low` |

## Outputs

### Hardening Report

- **Pattern Definition** -- Formal description of the vulnerability pattern being scanned.
- **Scan Scope** -- Files and directories covered.
- **Findings** -- List of at-risk locations, each with:
  - File path and line range
  - Code snippet showing the vulnerable pattern
  - Severity rating
  - Confidence that this is a genuine vulnerability (not a false positive)
- **Statistics** -- Total files scanned, findings count, severity breakdown.

### Preventive Fixes

For each finding (when `auto_fix: enabled`):

- A minimal patch following the same principles as the Fix skill.
- Test cases covering the hardened code path.
- Grouped into logical merge requests (one per module or directory).

### Hardening Summary

- Total vulnerabilities found and fixed.
- Estimated incidents prevented.
- Recommended additions to linting rules or CI checks to prevent recurrence.

## Behavior

### 1. Pattern Extraction

If given a postmortem or incident ID, extract the vulnerability pattern:

- What was the defect class? (nil safety, auth bypass, race condition, etc.)
- What did the vulnerable code look like?
- What did the fixed code look like?
- What are the structural markers of this pattern?

### 2. Pattern Formalization

Convert the pattern into searchable criteria:

- **AST patterns** -- Structural code patterns (e.g., method call on potentially nil receiver without guard).
- **Regex patterns** -- Text-level patterns for simpler cases.
- **Semantic patterns** -- Logical conditions (e.g., "database lookup result used without existence check").

### 3. Codebase Scan

Sweep the scoped codebase for matches:

- Parse files and match against the formalized pattern.
- Rank findings by severity and confidence.
- Filter out false positives using contextual analysis (e.g., the variable is guaranteed non-nil by an earlier check).

### 4. Fix Generation

For each confirmed finding:

- Apply the same fix strategy that resolved the original incident.
- Adapt to local code conventions (the surrounding code may use different patterns than the original file).
- Generate a test case that would catch the vulnerability.

### 5. MR Grouping

Organize fixes into merge requests:

- Group by module or directory for manageable review scope.
- Each MR includes the hardening rationale, linking back to the original incident.
- Label MRs with `reflex`, `hardening`, and the pattern category.

## Vulnerability Categories

The following categories are available for sweep mode:

| Category | Description | Examples |
|---|---|---|
| `nil-safety` | Missing null/nil checks before method calls | Optional associations, API responses |
| `error-handling` | Unhandled exceptions or swallowed errors | Bare rescue, empty catch blocks |
| `auth-checks` | Missing or inconsistent authorization | Endpoints without policy checks |
| `input-validation` | Unsanitized user input | SQL injection, XSS, path traversal |
| `race-conditions` | Concurrent access without synchronization | TOCTOU, double-spend |
| `config-drift` | Environment-specific values hardcoded or mismatched | Production URLs in dev configs |
| `dependency-risk` | Outdated or vulnerable dependencies | Known CVEs, unmaintained packages |
| `secret-exposure` | Credentials or tokens in code or logs | API keys, passwords in strings |

## Example Usage

```
/harden --pattern "method call on optional ActiveRecord association without nil check" --scope app/

# Output:
# Hardening Report
# Pattern: Unguarded method call on optional ActiveRecord association
# Scope: app/ (487 files scanned)
#
# Findings: 12 instances across 8 files
#
#   HIGH   app/models/order.rb:89        -- shipping_address.full_street
#   HIGH   app/models/order.rb:134       -- billing_contact.email
#   MEDIUM app/services/notify.rb:45     -- user.preferences.email_enabled?
#   MEDIUM app/controllers/api/v2/...    -- current_plan.features
#   ...8 more
#
# Fixes Generated: 12 patches across 3 merge requests
#   MR 1: Harden nil safety in Order model (4 fixes)
#   MR 2: Harden nil safety in notification services (3 fixes)
#   MR 3: Harden nil safety in API controllers (5 fixes)
#
# Recommendations:
#   - Add rubocop-rails rule for `Rails/SafeNavigation` to CI
#   - Consider making `shipping_address` a required association
#
# Estimated incidents prevented: 4-6 (based on usage frequency of affected paths)
```

## Sweep Mode

In sweep mode, Harden runs multiple pattern categories in a single pass:

```
/harden --mode sweep --categories nil-safety,error-handling,auth-checks

# Runs all three categories and produces a consolidated report
# with findings grouped by category and severity.
```

This is useful for scheduled maintenance windows or as a periodic codebase health check.

## Role in the Reflex Pipeline

```
Triage --> Root Cause --> Fix --> Validation --> Deploy --> Postmortem
                                                               |
                                                          [ Harden ]
                                                               |
                                                     preventive fixes
```

Harden sits outside the main incident response flow. It is triggered by postmortems or invoked directly for proactive scanning. Its output feeds back into the standard pipeline: hardening fixes go through the same Validation and Deploy stages as incident fixes, ensuring the same quality bar applies.

Harden transforms reactive incident response into proactive codebase resilience. Every incident becomes an opportunity to eliminate an entire class of vulnerabilities, not just the one instance that caused the outage.
