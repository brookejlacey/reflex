/**
 * Test fixtures and data for Reflex E2E tests.
 */

/** Simulated incident issue for triggering Reflex */
export const INCIDENT_ISSUE = {
  title: "[Incident] Pipeline failure in user-service: NullReferenceError on empty DB result",
  description: `## Incident Report

**Severity**: High
**Service**: user-service
**Environment**: staging

### What happened
The CI pipeline failed on the \`test\` stage after a recent optimization to the user service.
Tests are reporting a \`TypeError: Cannot read properties of null\` in the \`/api/users\` endpoint
when the database returns an empty result set.

### Error Output
\`\`\`
FAILED tests/test_app.py::TestUserAPI::test_get_users_empty_db - TypeError: 'NoneType' object is not subscriptable
  File "app.py", line 47, in get_users
    return jsonify({"users": result["data"], "count": len(result["data"])})
TypeError: 'NoneType' object is not subscriptable
\`\`\`

### Recent Changes
- Commit \`a1b2c3d\`: "Optimize user query to use direct dict access instead of .get()"
- Changed \`result.get("data", [])\` to \`result["data"]\` for "performance"

### Impact
- All CI pipelines blocked
- Cannot deploy any changes to staging or production
- User listing endpoint broken for edge case (new/empty databases)

/label ~incident ~severity::high ~service::user-service
`,
};

/** Expected triage result structure */
export const EXPECTED_TRIAGE_FIELDS = [
  "severity",
  "affected_services",
  "failure_type",
  "error_summary",
  "recommended_priority",
] as const;

/** Expected root cause result structure */
export const EXPECTED_ROOT_CAUSE_FIELDS = [
  "root_cause_summary",
  "breaking_files",
  "failure_mechanism",
  "confidence",
  "fix_strategy",
] as const;

/** Expected fix result structure */
export const EXPECTED_FIX_FIELDS = [
  "fix_summary",
  "files_modified",
  "fix_type",
  "breaking_change",
  "rollback_safe",
] as const;

/** Expected deploy result structure */
export const EXPECTED_DEPLOY_FIELDS = [
  "merge_request_url",
  "branch_name",
  "deployment_status",
] as const;

/** Expected postmortem result structure */
export const EXPECTED_POSTMORTEM_FIELDS = [
  "postmortem_summary",
  "timeline",
  "follow_up_issues",
  "lessons_learned",
] as const;
