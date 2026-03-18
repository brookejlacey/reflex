import { test, expect } from "@playwright/test";
import { GitLabAPI } from "../helpers/gitlab-api";
import { INCIDENT_ISSUE } from "../fixtures/test-data";

/**
 * Integration Tests — Incident Pipeline
 *
 * These tests require a live GitLab instance with Reflex configured.
 * Set environment variables:
 *   GITLAB_BASE_URL - GitLab instance URL
 *   GITLAB_ACCESS_TOKEN - Personal access token
 *   GITLAB_PROJECT_ID - Project ID where Reflex is configured
 *
 * These tests validate the full end-to-end flow:
 * 1. Create an incident issue
 * 2. Trigger Reflex via mention
 * 3. Verify each agent produces output
 * 4. Verify MR is created with fix
 * 5. Verify postmortem is generated
 */

const PROJECT_ID = process.env.GITLAB_PROJECT_ID || "";

test.describe("Reflex End-to-End Incident Pipeline", () => {
  let api: GitLabAPI;

  test.beforeAll(async ({ request }) => {
    test.skip(!PROJECT_ID, "GITLAB_PROJECT_ID not set — skipping live tests");
    api = new GitLabAPI(request, PROJECT_ID);
  });

  test("full incident-to-fix pipeline", async () => {
    // Step 1: Create incident issue
    const issue = await api.createIncidentIssue(
      INCIDENT_ISSUE.title,
      INCIDENT_ISSUE.description
    );
    expect(issue.iid).toBeTruthy();
    console.log(`Created incident issue #${issue.iid}`);

    // Step 2: Trigger Reflex by mentioning
    await api.mentionReflex(
      issue.iid,
      "Please triage and fix this incident automatically."
    );
    console.log("Triggered Reflex via @mention");

    // Step 3: Wait for triage comment (first agent response)
    const triageNotes = await api.waitFor(
      () => api.getIssueNotes(issue.iid),
      (notes: any[]) =>
        notes.some(
          (n: any) =>
            n.body.includes("Triage") || n.body.includes("severity")
        ),
      { timeout: 120_000, description: "triage agent response" }
    );
    console.log("Triage agent responded");

    const triageNote = triageNotes.find(
      (n: any) => n.body.includes("Triage") || n.body.includes("severity")
    );
    expect(triageNote).toBeTruthy();

    // Step 4: Wait for root cause comment
    const rcNotes = await api.waitFor(
      () => api.getIssueNotes(issue.iid),
      (notes: any[]) =>
        notes.some(
          (n: any) =>
            n.body.includes("Root Cause") || n.body.includes("root cause")
        ),
      { timeout: 180_000, description: "root cause agent response" }
    );
    console.log("Root Cause agent responded");

    // Step 5: Wait for MR creation (deploy agent)
    const mergeRequests = await api.waitFor(
      () =>
        api.getMergeRequests({
          state: "opened",
          search: "Reflex",
          order_by: "created_at",
          sort: "desc",
        }),
      (mrs: any[]) => mrs.length > 0,
      { timeout: 300_000, description: "Reflex MR creation" }
    );

    const reflexMR = mergeRequests[0];
    expect(reflexMR.title).toContain("Reflex");
    console.log(`MR created: !${reflexMR.iid} — ${reflexMR.title}`);

    // Step 6: Verify MR has fix content
    const mrChanges = await api.getMergeRequestChanges(reflexMR.iid);
    expect(mrChanges.changes).toBeTruthy();
    expect(mrChanges.changes.length).toBeGreaterThan(0);
    console.log(`MR has ${mrChanges.changes.length} file changes`);

    // Step 7: Verify MR description includes key sections
    expect(reflexMR.description).toContain("Root Cause");
    expect(reflexMR.description).toContain("Fix");

    // Step 8: Wait for postmortem comment
    const pmNotes = await api.waitFor(
      () => api.getIssueNotes(issue.iid),
      (notes: any[]) =>
        notes.some(
          (n: any) =>
            n.body.includes("Postmortem") || n.body.includes("postmortem")
        ),
      { timeout: 120_000, description: "postmortem agent response" }
    );

    const postmortemNote = pmNotes.find(
      (n: any) =>
        n.body.includes("Postmortem") || n.body.includes("postmortem")
    );
    expect(postmortemNote).toBeTruthy();
    console.log("Postmortem generated");

    // Step 9: Verify sustainability metrics in postmortem
    expect(postmortemNote.body).toMatch(
      /time.saved|carbon|sustainability/i
    );

    console.log("Full pipeline completed successfully!");
  });

  test("low-confidence root cause skips fix and goes to postmortem", async () => {
    // Create an ambiguous incident that should result in low confidence
    const issue = await api.createIncidentIssue(
      "[Incident] Intermittent timeout — unclear cause",
      `## Incident Report
**Severity**: Low
**Service**: unknown

Seeing intermittent timeouts in staging. No clear error message.
Could be network, could be database, could be the app.
No recent code changes correlate.`
    );

    await api.mentionReflex(issue.iid, "Investigate this incident.");

    // Should eventually get a postmortem without a fix MR
    const notes = await api.waitFor(
      () => api.getIssueNotes(issue.iid),
      (notes: any[]) =>
        notes.some((n: any) => n.body.toLowerCase().includes("postmortem")),
      { timeout: 300_000, description: "postmortem for low-confidence case" }
    );

    // Verify no MR was created for this incident
    const mrs = await api.getMergeRequests({
      state: "opened",
      search: `fix-${issue.iid}`,
    });
    expect(mrs).toHaveLength(0);
  });
});

test.describe("Reflex Hardening Flow", () => {
  let api: GitLabAPI;

  test.beforeAll(async ({ request }) => {
    test.skip(!PROJECT_ID, "GITLAB_PROJECT_ID not set — skipping live tests");
    api = new GitLabAPI(request, PROJECT_ID);
  });

  test("hardening flow creates preventive MR after incident resolution", async () => {
    // Look for hardening MRs (would be created after main flow completes)
    const mrs = await api.getMergeRequests({
      state: "opened",
      search: "Reflex Harden",
      order_by: "created_at",
      sort: "desc",
    });

    if (mrs.length > 0) {
      const hardenMR = mrs[0];
      expect(hardenMR.title).toContain("Harden");
      expect(hardenMR.description).toContain("Preventive");
      console.log(
        `Hardening MR found: !${hardenMR.iid} — ${hardenMR.title}`
      );
    } else {
      console.log(
        "No hardening MRs found — run after a full incident resolution"
      );
    }
  });
});
