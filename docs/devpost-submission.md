# Reflex — Autonomous Incident-to-Fix Pipeline for GitLab

## Inspiration

A production alert fires at 2 AM. An engineer jolts awake, logs in, stares at a wall of logs, pages two more people, and starts the grind: triage, root cause, hotfix, code review, deploy, postmortem. Four hours later the incident is resolved but the postmortem never gets written, the follow-up issues never get filed, and six weeks later the same class of bug takes down the service again.

This is the reality of incident response. Industry data shows Mean Time to Resolution (MTTR) averaging 2-4 hours. On-call engineers burn out. Knowledge about past incidents evaporates. The same patterns recur because nobody has time to harden the codebase after firefighting the immediate problem.

We asked: what if your repository had an immune system? Not a tool that helps humans respond faster, but a system that autonomously handles the entire incident lifecycle — from the moment a pipeline fails to the merge request that fixes it, the regression tests that prevent it, and the postmortem that documents it. That's Reflex.

## What it does

Reflex is a self-healing immune system for GitLab repositories. It orchestrates 9 specialized AI agents across 2 coordinated flows that autonomously handle the full incident lifecycle without human intervention:

**Primary Flow — Incident Response (6 agents):**

1. **Triage Agent** — First responder. Classifies severity (critical/high/medium/low), identifies the blast radius across affected services, gathers diagnostic context from pipeline logs and GCP Cloud Logging, and posts a structured triage summary on the incident issue.

2. **Root Cause Agent** — Detective. Performs git archaeology through blame analysis, commit history, and code diffs. Traces the call chain to pinpoint the exact file, line, and commit that introduced the failure. Produces a specific fix strategy for the next agent.

3. **Fix Agent** — Surgeon. Generates a minimal, targeted code fix that follows existing patterns and conventions. Operates on the principle of changing the fewest lines possible — no refactoring, no cleanup, just the precise change needed.

4. **Validation Agent** — QA + Security. Writes regression tests that would have caught the original bug. Runs a security review checklist covering injection, auth bypass, data exposure, and dependency vulnerabilities. Only passes the fix forward if it's confident the change is safe and tested.

5. **Deploy Agent** — DevOps. Creates a properly labeled merge request with the fix, tests, and full incident context. Links it to the original issue. Never auto-merges — always creates an MR for human review.

6. **Postmortem Agent** — Analyst. Generates a blameless postmortem with full timeline, root cause explanation, impact assessment, lessons learned, and actionable follow-up issues. Includes a sustainability report comparing the carbon footprint of the automated response vs. a traditional human-driven process.

**Secondary Flow — Proactive Hardening (3 agents):**

7. **Pattern Extraction Agent** — Generalizes the specific bug into abstract vulnerability patterns with regex search expressions.

8. **Codebase Scan Agent** — Systematically scans the entire repository for other instances of the same vulnerability class, verifying each match to eliminate false positives.

9. **Preventive Fix Agent** — Applies fixes across all confirmed vulnerabilities and creates a hardening merge request, preventing future incidents before they happen.

**Smart conditional routing** makes the pipeline adaptive, not just linear:
- Low-priority or backlog items skip straight to postmortem for documentation
- Low-confidence root causes skip the fix and flag for human investigation
- Failed validation skips deployment and reports concerns in the postmortem

This means Reflex doesn't just follow a script — it makes decisions about when automation is appropriate and when to hand off to humans.

## How we built it

**GitLab Duo Agent Platform** is the backbone. We defined 2 Flow YAML files (`reflex.yaml` and `harden.yaml`) using the Flow Registry v1 schema, with conditional routers that branch the pipeline based on agent output. Every agent is an `AgentComponent` with a detailed system prompt, a curated toolset, structured `response_schema` definitions (JSON Schema draft-07), and explicit input mappings that chain outputs from upstream agents.

**Structured data passing** is what makes the multi-agent orchestration work. Each agent produces typed JSON output (severity enums, file path arrays, confidence levels, boolean validation flags) that downstream agents consume as structured input. The Triage Agent's `recommended_priority` field drives the first router. The Root Cause Agent's `confidence` field drives the second. The Validation Agent's `validation_passed` boolean drives the third. This isn't agents chatting — it's a typed data pipeline.

**7 standalone skills** (one per agent role plus the harden skill) let developers invoke any agent individually via slash commands (`/reflex-triage`, `/reflex-fix`, `/reflex-harden`, etc.) for targeted use outside the full pipeline.

**External agent** using Claude Code provides deep analysis capabilities beyond the built-in toolset — git bisect for finding breaking commits, complex code pattern matching, and automated test execution in a containerized Python 3.11 environment with full shell access.

**Python integration with GCP Cloud Logging and Monitoring** gives agents richer context than pipeline logs alone. The `CloudLoggingClient` queries error logs, extracts deduplicated stack traces, and identifies correlated events around the incident timestamp. It falls back gracefully to realistic mock data when GCP credentials aren't available, keeping the demo fully functional.

**Sustainability tracker** (`CarbonTracker`) records token usage and compute time across every agent step, then estimates carbon footprint using published data: energy-per-token estimates from Patterson et al. 2021, US grid carbon intensity from EPA eGRID 2023, and cloud provider PUE adjustments. Every postmortem includes a comparison showing the carbon savings of autonomous response vs. traditional human incident response (laptops + monitors + video calls + infrastructure idle time).

**Playwright E2E test suite** with 40 tests across 3 spec files validates everything without requiring a live GitLab instance:
- Flow structure validation (all components, routers, schemas, prompt references, data flow graph)
- Skills validation (all 7 SKILL.md files with proper frontmatter)
- API prerequisite checks for live integration testing
- Full end-to-end incident pipeline integration tests

**Demo Flask app** with a realistic intentional bug — a "performance optimization" PR that accesses `users[0]["name"]` on a potentially empty list, crashing the `/api/users` endpoint when the database returns no results. This is exactly the kind of subtle bug that passes code review but breaks in production.

## Challenges we ran into

**Flow YAML schema was uncharted territory.** The GitLab Duo Agent Platform's flow definition format has limited documentation and few examples in the wild. Getting the `response_schema` definitions right so that structured outputs could reliably feed into downstream agent `inputs` via `context:agent_name.final_answer` references took significant iteration. One missing `required` field in a schema could silently break data flow between agents.

**Conditional routing required careful schema design.** The routers inspect specific fields from agent responses (`recommended_priority`, `confidence`, `validation_passed`) to decide where to route next. This meant every agent's response schema had to be designed not just for its own downstream consumers, but for the routing infrastructure. We had to think about the pipeline as a typed data flow graph, not just a sequence of prompts.

**Balancing prompt detail with token efficiency.** Each agent needs enough context to act autonomously (security review checklists, fix principles, severity classification rubrics), but the prompts can't be so long that they consume the token budget before the agent even starts working. We found the sweet spot by making system prompts comprehensive but user prompts minimal — passing only the structured data each agent actually needs.

**Making the external agent work with Claude Code through the AI Gateway.** Configuring the proxy setup (`ANTHROPIC_BASE_URL` pointing to `cloud.gitlab.com/ai/v1/proxy/anthropic`) and wiring the gateway token through to the containerized environment required understanding both the GitLab AI Gateway authentication flow and the Claude Code API expectations.

## Accomplishments that we're proud of

**9 agents across 2 flows working as a single cohesive pipeline.** Each agent has a distinct role, a curated toolset, and produces structured output that the next agent consumes. There are no generic "do everything" agents — every component is specialized.

**Conditional routing that makes smart decisions.** The pipeline doesn't blindly run every agent. If triage says it's a backlog item, we skip straight to documentation. If root cause confidence is low, we don't generate a potentially wrong fix — we flag it for humans. If validation fails, we don't deploy broken code. The pipeline adapts.

**Every agent produces typed JSON consumed by downstream agents.** This isn't prompt chaining — it's structured data passing with JSON Schema validation. Severity enums, file path arrays, confidence levels, boolean flags. The routing decisions are based on actual field values, not LLM text parsing.

**Full sustainability tracking with published methodology.** We didn't just slap a "green" label on the project. The `CarbonTracker` uses peer-reviewed energy estimates (Patterson et al., Strubell et al.), government data (EPA eGRID 2023), and cloud provider PUE disclosures to produce defensible carbon comparisons. Every postmortem includes per-agent token breakdowns and total carbon savings.

**Proactive hardening that prevents future incidents.** Most incident response tools stop at the fix. Reflex goes further — after resolving an incident, the Harden flow generalizes the bug into a vulnerability pattern class, scans the entire codebase for similar instances, and creates a preventive merge request. It doesn't just heal; it builds immunity.

**Zero-config operation.** Enable the flow triggers, and Reflex runs autonomously on pipeline failures. No dashboards to configure, no rules to write, no integrations to set up. It works with the GitLab tools developers already use — issues, MRs, pipeline events.

## What we learned

**Agent orchestration is a data engineering problem, not just a prompt engineering problem.** The hardest part wasn't writing good prompts — it was designing the data contracts between agents so that structured outputs reliably flow through routers and into downstream inputs. Typed response schemas and explicit input mappings matter more than clever prompt tricks.

**The GitLab Duo Agent Platform is genuinely powerful for multi-agent workflows.** Flows with conditional routing, structured response schemas, and ambient execution give you real orchestration primitives — not just a chatbot interface. The platform handles agent lifecycle, tool access, and context passing, letting us focus on the domain logic.

**Sustainability tracking changes how you think about AI systems.** When you see the per-agent token breakdown and carbon estimate after every run, you start optimizing for efficiency instinctively. It pushed us toward more targeted prompts, smarter routing (skip agents when you can), and minimal-context passing.

**Incident response is a perfect domain for multi-agent AI.** Each phase (triage, root cause, fix, validation, deploy, postmortem) has distinct skill requirements, distinct tool needs, and distinct output formats. Splitting these into specialized agents with explicit data contracts produces better results than a single monolithic agent trying to do everything.

## What's next for Reflex

- **PagerDuty/Opsgenie integration** — Trigger Reflex from real incident management platforms, not just GitLab pipeline events
- **Incident memory** — Learn from past incidents to improve triage accuracy and root cause detection over time, building a knowledge base of failure patterns
- **Multi-repo support** — Trace incidents across microservice boundaries, correlating failures in one repo with root causes in another
- **Custom pattern libraries** — Industry-specific vulnerability detection (OWASP patterns for web apps, CWE patterns for infrastructure, HIPAA patterns for healthcare)
- **Confidence calibration** — Track prediction accuracy over time and adjust routing thresholds automatically
- **Team analytics** — Dashboard showing MTTR trends, incident categories, and hardening coverage across the organization

## Built With

- GitLab Duo Agent Platform (Flows + Custom Agents)
- Anthropic Claude (via GitLab AI Gateway)
- Google Cloud Logging + Cloud Monitoring
- Python 3.11
- Flask (demo application)
- Playwright (E2E test suite)
- TypeScript (test infrastructure)

## Try it out

[GitLab Repository](https://gitlab.com/) | [Demo Video]()
