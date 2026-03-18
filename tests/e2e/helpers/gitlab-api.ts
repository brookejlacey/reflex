import { APIRequestContext } from "@playwright/test";

/**
 * GitLab API helper for Reflex E2E tests.
 * Wraps common GitLab API operations needed for testing the agent pipeline.
 */
export class GitLabAPI {
  private request: APIRequestContext;
  private projectId: string;

  constructor(request: APIRequestContext, projectId: string) {
    this.request = request;
    this.projectId = projectId;
  }

  /** Create an issue to trigger Reflex */
  async createIncidentIssue(title: string, description: string) {
    const response = await this.request.post(
      `/api/v4/projects/${this.projectId}/issues`,
      {
        data: {
          title,
          description,
          labels: "incident,reflex::trigger",
          issue_type: "incident",
        },
      }
    );
    return response.json();
  }

  /** Get issue details */
  async getIssue(issueIid: number) {
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/issues/${issueIid}`
    );
    return response.json();
  }

  /** Get issue notes (comments) */
  async getIssueNotes(issueIid: number) {
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/issues/${issueIid}/notes`
    );
    return response.json();
  }

  /** Get merge requests */
  async getMergeRequests(params?: Record<string, string>) {
    const query = new URLSearchParams(params).toString();
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/merge_requests?${query}`
    );
    return response.json();
  }

  /** Get a specific merge request */
  async getMergeRequest(mrIid: number) {
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/merge_requests/${mrIid}`
    );
    return response.json();
  }

  /** Get merge request changes (diff) */
  async getMergeRequestChanges(mrIid: number) {
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/merge_requests/${mrIid}/changes`
    );
    return response.json();
  }

  /** Get pipeline status */
  async getPipeline(pipelineId: number) {
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/pipelines/${pipelineId}`
    );
    return response.json();
  }

  /** Get recent pipelines */
  async getPipelines(params?: Record<string, string>) {
    const query = new URLSearchParams(params).toString();
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/pipelines?${query}`
    );
    return response.json();
  }

  /** Get pipeline jobs */
  async getPipelineJobs(pipelineId: number) {
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/pipelines/${pipelineId}/jobs`
    );
    return response.json();
  }

  /** Get job log/trace */
  async getJobTrace(jobId: number) {
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/jobs/${jobId}/trace`
    );
    return response.text();
  }

  /** Check if a file exists in the repo */
  async getRepositoryFile(filePath: string, ref = "main") {
    const encoded = encodeURIComponent(filePath);
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/repository/files/${encoded}?ref=${ref}`
    );
    return response.json();
  }

  /** List repository branches */
  async getBranches(search?: string) {
    const query = search ? `?search=${search}` : "";
    const response = await this.request.get(
      `/api/v4/projects/${this.projectId}/repository/branches${query}`
    );
    return response.json();
  }

  /** Add a mention comment to trigger Reflex */
  async mentionReflex(issueIid: number, message: string) {
    const response = await this.request.post(
      `/api/v4/projects/${this.projectId}/issues/${issueIid}/notes`,
      {
        data: {
          body: `@reflex ${message}`,
        },
      }
    );
    return response.json();
  }

  /** Wait for a condition with polling */
  async waitFor<T>(
    fn: () => Promise<T>,
    predicate: (result: T) => boolean,
    {
      timeout = 90_000,
      interval = 5_000,
      description = "condition",
    }: { timeout?: number; interval?: number; description?: string } = {}
  ): Promise<T> {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const result = await fn();
      if (predicate(result)) return result;
      await new Promise((r) => setTimeout(r, interval));
    }
    throw new Error(`Timed out waiting for ${description} after ${timeout}ms`);
  }
}
