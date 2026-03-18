import { test, expect } from "@playwright/test";
import { GitLabAPI } from "../helpers/gitlab-api";

/**
 * API Validation Tests
 *
 * Validates that the GitLab instance is properly configured for Reflex.
 * These are prerequisite checks before running integration tests.
 */

const PROJECT_ID = process.env.GITLAB_PROJECT_ID || "";

test.describe("GitLab Environment Prerequisites", () => {
  let api: GitLabAPI;

  test.beforeAll(async ({ request }) => {
    test.skip(!PROJECT_ID, "GITLAB_PROJECT_ID not set — skipping API tests");
    api = new GitLabAPI(request, PROJECT_ID);
  });

  test("can authenticate with GitLab API", async ({ request }) => {
    const response = await request.get("/api/v4/user");
    expect(response.ok()).toBe(true);
    const user = await response.json();
    expect(user.id).toBeTruthy();
    console.log(`Authenticated as: ${user.username}`);
  });

  test("project exists and is accessible", async ({ request }) => {
    const response = await request.get(`/api/v4/projects/${PROJECT_ID}`);
    expect(response.ok()).toBe(true);
    const project = await response.json();
    expect(project.id).toBeTruthy();
    console.log(`Project: ${project.path_with_namespace}`);
  });

  test("reflex.yaml flow file exists in repository", async () => {
    const file = await api.getRepositoryFile(
      ".gitlab/duo/flows/reflex.yaml"
    );
    expect(file.file_name).toBe("reflex.yaml");
  });

  test("harden.yaml flow file exists in repository", async () => {
    const file = await api.getRepositoryFile(
      ".gitlab/duo/flows/harden.yaml"
    );
    expect(file.file_name).toBe("harden.yaml");
  });

  test("agent-config.yml exists in repository", async () => {
    const file = await api.getRepositoryFile(
      ".gitlab/duo/agent-config.yml"
    );
    expect(file.file_name).toBe("agent-config.yml");
  });

  test("AGENTS.md exists in repository", async () => {
    const file = await api.getRepositoryFile("AGENTS.md");
    expect(file.file_name).toBe("AGENTS.md");
  });

  test("can create and read issues", async () => {
    const issue = await api.createIncidentIssue(
      "[Test] Reflex E2E validation check",
      "Automated test — safe to close."
    );
    expect(issue.iid).toBeTruthy();

    const fetched = await api.getIssue(issue.iid);
    expect(fetched.title).toContain("Reflex E2E");

    console.log(`Test issue created: #${issue.iid}`);
  });

  test("can list pipelines", async () => {
    const pipelines = await api.getPipelines({ per_page: "5" });
    expect(Array.isArray(pipelines)).toBe(true);
    console.log(`Found ${pipelines.length} recent pipelines`);
  });

  test("reflex branches namespace exists", async () => {
    const branches = await api.getBranches("reflex/");
    // May be empty if no incidents have been processed yet
    expect(Array.isArray(branches)).toBe(true);
    console.log(`Found ${branches.length} reflex/* branches`);
  });
});
