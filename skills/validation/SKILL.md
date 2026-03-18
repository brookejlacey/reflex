---
name: validation
description: "Runs regression tests, generates new test cases for the fix, performs security scanning, and gates the patch before it can proceed to deployment."
metadata:
  slash-command: enabled
---

# Validation

## Overview

The Validation skill is the quality gate of the Reflex pipeline. It takes the patch produced by the Fix skill and subjects it to automated testing, security analysis, and regression checks before allowing the change to move toward deployment. No fix reaches production without passing validation.

Validation operates on the principle of defense in depth: it runs multiple independent checks so that no single class of defect slips through.

## Invocation

### As a slash command

```
/validation <patch-or-branch>
```

### Standalone

```
reflex validation --patch fix-invoice-nil-guard.patch --suite unit,integration --security enabled
```

### As part of the Reflex pipeline

Automatically receives the patch from the `fix` skill and passes its verdict to the `deploy` skill.

## Inputs

| Input | Required | Description |
|---|---|---|
| `patch` | Yes | The diff or branch reference containing the fix |
| `suite` | No | Test suites to run: `unit`, `integration`, `e2e`, or `all` (default: `unit,integration`) |
| `security` | No | Enable security scanning: `enabled` (default) or `disabled` |
| `coverage_threshold` | No | Minimum line coverage for changed files (default: 80%) |
| `timeout` | No | Max time for the validation run (default: 15 minutes) |

## Outputs

A structured **Validation Report** containing:

- **Verdict** -- `pass`, `fail`, or `warn` (passes with caveats).
- **Test Results** -- Suite-by-suite pass/fail counts with failure details.
- **New Tests** -- Any test cases generated to cover the fix.
- **Coverage Delta** -- How the patch affects code coverage.
- **Security Findings** -- Results from static analysis and dependency scanning.
- **Performance Impact** -- If applicable, benchmark comparisons.
- **Blockers** -- Issues that must be resolved before deployment.

## Behavior

### 1. Patch Application

Apply the fix to a clean branch off the target (usually `main`). Verify the patch applies cleanly without conflicts.

### 2. Existing Test Suite

Run the project's existing test suites against the patched code:

- **Unit tests** -- Fast, isolated tests for the affected module.
- **Integration tests** -- Tests that exercise the affected component's interactions.
- **E2E tests** -- If available and requested, run end-to-end tests.

All existing tests must pass. Any failure is a blocker.

### 3. Regression Test Generation

Generate new test cases that specifically target the defect:

- **Reproduction test** -- A test that fails on the broken code and passes on the fix.
- **Edge case tests** -- Tests for boundary conditions around the fix.
- **Nil/null/empty tests** -- If the fix involves a guard, test all nil paths.

New tests follow the project's existing test framework and conventions (RSpec, Jest, pytest, etc.).

### 4. Security Scanning

Run security checks on the changed files:

- **Static Analysis (SAST)** -- Check for common vulnerability patterns.
- **Dependency Scanning** -- If dependencies changed, check for known CVEs.
- **Secrets Detection** -- Ensure no credentials or tokens were introduced.

### 5. Coverage Analysis

Measure code coverage for the changed lines:

- All new/modified lines should be covered by at least one test.
- If coverage drops below the threshold, emit a warning.

### 6. Verdict

Combine all results into a final verdict:

- **Pass** -- All tests pass, no security findings, coverage meets threshold.
- **Warn** -- Tests pass but coverage is below threshold or there are low-severity security notes.
- **Fail** -- Test failures, high-severity security findings, or patch application errors.

## Example Usage

```
/validation --patch fix-invoice-nil-guard.patch

# Output:
# Validation Report
# Verdict: pass
#
# Test Results:
#   Unit:        412 passed, 0 failed (2.3s)
#   Integration:  87 passed, 0 failed (14.1s)
#
# New Tests Generated:
#   spec/billing/invoice_nil_subscription_spec.rb
#     - it "returns zero when subscription is nil"
#     - it "returns zero when subscription is not found"
#     - it "calculates total when subscription exists"
#
# Coverage: 94% on changed lines (threshold: 80%) -- OK
# Security: no findings
# Blockers: none
```

## Failure Handling

When validation fails, the skill provides actionable feedback:

- **Test failure** -- Includes the failing test name, expected vs actual output, and a suggestion for the Fix skill to revise.
- **Security finding** -- Includes the CWE/CVE reference, affected line, and remediation guidance.
- **Coverage gap** -- Identifies untested lines and suggests test cases.

If validation fails, the pipeline loops back to the Fix skill with the failure details for a revised patch attempt (max 3 iterations before escalating to human review).

## Role in the Reflex Pipeline

```
Triage --> Root Cause --> Fix --> [ Validation ] --> Deploy --> Postmortem
                           ^          |
                           |__ retry __|  (up to 3 attempts)
```

Validation is the gatekeeper. It ensures that urgency does not compromise quality. Only patches with a `pass` or `warn` verdict proceed to the Deploy skill.
