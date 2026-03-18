---
name: fix
description: "Generates minimal, targeted code fixes that follow existing codebase patterns, conventions, and style to resolve the identified root cause."
metadata:
  slash-command: enabled
---

# Fix

## Overview

The Fix skill generates the smallest correct patch to resolve an incident's root cause. It is deliberately conservative: rather than refactoring or improving code, it restores correctness by following the patterns, idioms, and conventions already present in the codebase. The goal is a low-risk change that can be reviewed, tested, and deployed quickly.

Fix does not innovate. It imitates the surrounding code and applies the minimum diff required to resolve the defect.

## Invocation

### As a slash command

```
/fix <root-cause-report-or-incident-id>
```

### Standalone

```
reflex fix --file lib/billing/invoice.rb --line 142 --issue "nil guard removed" --strategy restore
```

### As part of the Reflex pipeline

Automatically receives root cause analysis from the `root-cause` skill and passes its patch to the `validation` skill.

## Inputs

| Input | Required | Description |
|---|---|---|
| `root_cause` | Yes | Structured output from the root-cause skill, or manual specification of the defect |
| `file` | No | Target file path (inferred from root cause if not provided) |
| `strategy` | No | Fix strategy: `restore` (revert the breaking logic), `guard` (add defensive check), `patch` (apply targeted edit). Default: auto-selected |
| `scope` | No | `minimal` (default) or `thorough` (allows broader refactoring if justified) |

## Outputs

- **Patch** -- A Git-compatible diff containing the fix.
- **Changed Files** -- List of files modified with line-level descriptions.
- **Fix Rationale** -- Why this specific change resolves the issue.
- **Pattern Reference** -- Links to similar patterns elsewhere in the codebase that the fix mimics.
- **Risk Assessment** -- `low`, `medium`, or `high` based on scope of change and test coverage.

## Behavior

1. **Context Loading** -- Read the target file(s) and surrounding code. Build understanding of local conventions: error handling style, naming patterns, indentation, guard clause usage.
2. **Pattern Matching** -- Search the codebase for analogous code that handles the same class of problem correctly. Use these as templates for the fix.
3. **Strategy Selection** -- Choose the appropriate fix strategy:
   - **Restore** -- If a previously working version exists in Git history, restore the relevant logic.
   - **Guard** -- If the defect is a missing safety check, add one consistent with how the codebase handles similar cases.
   - **Patch** -- If the defect is a logic error, apply a targeted correction.
4. **Diff Generation** -- Produce the minimal diff. Constraints:
   - No unrelated formatting changes.
   - No import/require additions unless absolutely necessary.
   - No variable renames or refactors.
   - Match existing indentation (tabs vs spaces, width).
   - Preserve surrounding blank lines and comment style.
5. **Self-Review** -- Before emitting the patch, verify:
   - Does the fix address the root cause?
   - Does it introduce any new issues (type errors, missing imports)?
   - Is it the smallest change possible?
6. **Emit** -- Output the patch and metadata for the validation skill.

## Example Usage

```
/fix --file lib/billing/invoice.rb --line 142 --issue "nil guard on current_subscription removed"

# Output:
# Fix (strategy: restore, risk: low)
#
# --- a/lib/billing/invoice.rb
# +++ b/lib/billing/invoice.rb
# @@ -140,6 +140,7 @@
#    def calculate_total
#      subscription = current_subscription
# +    return Money.zero unless subscription
#      subscription.total + adjustments_total
#    end
#
# Rationale: Restores the nil guard that was present before commit a3f8e21.
# Pattern: 14 other methods in this file use `return ... unless` guards.
# Risk: low -- single line addition, no behavioral change for non-nil path.
```

## Fix Principles

1. **Minimal diff** -- Every line in the patch must be justified by the root cause.
2. **Pattern conformity** -- The fix should look like it was written by the same person who wrote the surrounding code.
3. **No side quests** -- Do not fix adjacent issues, improve performance, or refactor. File those as follow-ups.
4. **Reversibility** -- The fix should be easy to revert if it causes unexpected problems.
5. **Test awareness** -- If the fix touches untested code, flag it for the validation skill to address.

## Role in the Reflex Pipeline

```
Triage --> Root Cause --> [ Fix ] --> Validation --> Deploy --> Postmortem
```

Fix takes the root cause analysis and produces a patch. The patch is never applied directly -- it is passed to the Validation skill for automated testing and security review before any merge request is created.
