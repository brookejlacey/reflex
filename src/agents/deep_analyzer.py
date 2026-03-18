#!/usr/bin/env python3
"""
Reflex Deep Analyzer — External Agent for enhanced incident analysis.

This agent runs as a Docker container on GitLab Runners and provides
capabilities beyond the built-in agent toolset:
- Git bisect for finding breaking commits
- GCP Cloud Logging queries for production log analysis
- Complex pattern matching across the codebase
- Sustainability metrics calculation
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gcp.cloud_logging import CloudLoggingClient
from gcp.monitoring import CloudMonitoringClient as MonitoringClient
from utils.sustainability import SustainabilityTracker


def parse_args():
    parser = argparse.ArgumentParser(description="Reflex Deep Analyzer")
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--gitlab-token", required=True)
    parser.add_argument("--gitlab-hostname", required=True)
    parser.add_argument("--gcp-project", default="")
    parser.add_argument("--context", default="{}")
    parser.add_argument("--input", default="")
    return parser.parse_args()


def git_log_recent(n=20):
    """Get recent git commits for analysis."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--oneline", "--no-decorate"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def git_diff_commit(commit_sha: str):
    """Get the diff for a specific commit."""
    try:
        result = subprocess.run(
            ["git", "diff", f"{commit_sha}^", commit_sha, "--stat"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def git_blame_file(filepath: str, start_line: int, end_line: int):
    """Get git blame for a specific file region."""
    try:
        result = subprocess.run(
            ["git", "blame", "-L", f"{start_line},{end_line}", filepath],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def find_breaking_commit(test_command: str, good_ref: str = "HEAD~10", bad_ref: str = "HEAD"):
    """Use git bisect to find the commit that broke tests."""
    try:
        subprocess.run(["git", "bisect", "start"], capture_output=True, timeout=10)
        subprocess.run(["git", "bisect", "bad", bad_ref], capture_output=True, timeout=10)
        subprocess.run(["git", "bisect", "good", good_ref], capture_output=True, timeout=10)

        result = subprocess.run(
            ["git", "bisect", "run"] + test_command.split(),
            capture_output=True,
            text=True,
            timeout=300,
        )

        bisect_output = result.stdout + result.stderr

        # Reset bisect state
        subprocess.run(["git", "bisect", "reset"], capture_output=True, timeout=10)

        # Extract the breaking commit from bisect output
        for line in bisect_output.split("\n"):
            if "is the first bad commit" in line:
                return line.split()[0]

        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        subprocess.run(["git", "bisect", "reset"], capture_output=True, timeout=10)
        return None


def analyze_incident(context: dict, gcp_project: str):
    """Main incident analysis pipeline."""
    import time as _time

    tracker = SustainabilityTracker()
    tracker.start_pipeline()
    pipeline_start = _time.time()

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis_type": "deep",
        "git_history": [],
        "gcp_logs": [],
        "gcp_metrics": [],
        "breaking_commit": None,
        "pattern_analysis": [],
    }

    # Phase 1: Git History Analysis
    print("[Reflex] Analyzing git history...")
    git_start = _time.time()

    recent_commits = git_log_recent(20)
    results["git_history"] = recent_commits

    for commit_line in recent_commits[:5]:
        sha = commit_line.split()[0] if commit_line else ""
        if sha:
            diff = git_diff_commit(sha)
            if diff:
                results["pattern_analysis"].append(
                    {"commit": sha, "changes": diff}
                )

    tracker.record_step("deep_analyzer", "git_analysis", 500, 200, _time.time() - git_start)

    # Phase 2: GCP Log Analysis
    if gcp_project:
        print("[Reflex] Querying GCP Cloud Logging...")
        gcp_log_start = _time.time()

        try:
            logging_client = CloudLoggingClient(project_id=gcp_project)
            diagnostic = logging_client.query_incident_logs(incident_id="deep-analysis")
            results["gcp_logs"] = [e.to_dict() for e in diagnostic.entries]

            print(f"[Reflex] Found {len(diagnostic.entries)} relevant log entries")
        except Exception as e:
            print(f"[Reflex] GCP Logging unavailable: {e}")
            results["gcp_logs"] = [{"note": f"GCP Logging unavailable: {e}"}]

        tracker.record_step("deep_analyzer", "gcp_logging", 300, 150, _time.time() - gcp_log_start)

        # Phase 3: GCP Monitoring
        print("[Reflex] Checking GCP Monitoring for anomalies...")
        gcp_mon_start = _time.time()

        try:
            monitoring_client = MonitoringClient(project_id=gcp_project)
            monitoring_data = monitoring_client.query_incident_metrics(incident_id="deep-analysis")
            results["gcp_metrics"] = [a.to_dict() for a in monitoring_data.anomalies]

            print(f"[Reflex] Found {len(monitoring_data.anomalies)} metric anomalies")
        except Exception as e:
            print(f"[Reflex] GCP Monitoring unavailable: {e}")
            results["gcp_metrics"] = [{"note": f"GCP Monitoring unavailable: {e}"}]

        tracker.record_step("deep_analyzer", "gcp_monitoring", 200, 100, _time.time() - gcp_mon_start)
    else:
        print("[Reflex] GCP project not configured — skipping cloud diagnostics")

    # Phase 4: Generate sustainability report
    tracker.end_pipeline()
    results["sustainability"] = tracker.generate_report()

    return results


def main():
    args = parse_args()

    print("=" * 60)
    print("REFLEX DEEP ANALYZER — External Agent")
    print("=" * 60)
    print(f"Project: {args.project_path}")
    print(f"GitLab: {args.gitlab_hostname}")
    print(f"GCP Project: {args.gcp_project or 'not configured'}")
    print("=" * 60)

    # Parse context
    try:
        context = json.loads(args.context) if args.context else {}
    except json.JSONDecodeError:
        context = {"raw": args.context}

    # Run analysis
    results = analyze_incident(context, args.gcp_project)

    # Output results as JSON for the flow to consume
    print("\n[Reflex] Analysis complete. Results:")
    print(json.dumps(results, indent=2, default=str))

    # Write results to file for downstream consumption
    output_path = "/tmp/reflex-analysis.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[Reflex] Results written to {output_path}")


if __name__ == "__main__":
    main()
