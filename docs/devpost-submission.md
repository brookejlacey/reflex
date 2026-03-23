# Reflex — Autonomous Incident-to-Fix Pipeline with Organizational Memory

## Inspiration

It is 2 AM. Your phone buzzes. Pipeline failed, production is down. You jolt awake, log in, stare at a wall of logs, page two more people, and start the grind: triage, root cause, hotfix, code review, deploy, postmortem. Four hours later the incident is resolved but the postmortem never gets written, the follow-up issues never get filed, and six weeks later the same class of bug takes down the service again.

We have all lived this. Industry data shows Mean Time to Resolution (MTTR) averaging 2-4 hours. On-call engineers burn out. Knowledge about past incidents evaporates. The same patterns recur because nobody has time to harden the codebase after firefighting the immediate problem — and even when they do, the fix only covers one project while the same anti-pattern sits in five sibling services waiting to detonate.

We asked: what if your repository had an immune system? Not a tool that helps humans respond faster, but a system that autonomously handles the entire incident lifecycle — from the moment a pipeline fails to the merge request that fixes it, the regression tests that prevent it, the postmortem that documents it, and the organizational memory that ensures it never happens again. A system that debates its own diagnoses, learns from every incident, predicts future failures, and protects every project in the organization.

That is Reflex.

## What it does

Reflex is a self-healing immune system for GitLab repositories. It orchestrates **17 specialized AI agents across 4 coordinated flows** that autonomously handle the full incident lifecycle — and then go beyond, building organizational memory and predictive prevention.

### Flow 1: Incident Response (8 agents)

The primary pipeline, from detection to resolution:

1. **Knowledge Lookup Agent** — Searches the persistent knowledge graph before any analysis begins. Finds similar past incidents, matching patterns, and proven fix strategies. If Reflex has seen this bug before, every downstream agent knows immediately.

2. **Triage Agent** — Classifies severity, identifies blast radius, gathers diagnostic context from pipeline logs and GCP Cloud Logging. Cross-references with knowledge graph findings for faster, more accurate classification. Escalates severity for recurring patterns.

3. **Root Cause Agent** — Performs git archaeology through blame analysis, commit history, and code diffs. Proposes a hypothesis with specific file paths, line numbers, and evidence chains. This hypothesis is designed to be challenged.

4. **Challenger Agent** — The adversarial second opinion. Independently reads the code, tests alternative explanations, looks for counter-evidence, and verifies the proposed fix strategy. Issues a verdict: CONFIRMED, REFINED, or REJECTED. This debate protocol produces dramatically better diagnoses than single-pass analysis.

5. **Fix Agent** — Generates a minimal, targeted code fix informed by the debate result. If the Challenger refined the fix strategy, the Fix Agent uses the refined version. Operates on the principle of changing the fewest lines possible.

6. **Validation Agent** — Writes regression tests covering edge cases identified during the debate. Runs a security review. Only passes the fix forward if confident the change is safe and tested.

7. **Deploy Agent** — Creates a properly labeled merge request with fix, tests, debate summary, and knowledge graph context. Links to the original issue. Never auto-merges.

8. **Postmortem Agent** — Generates a blameless postmortem with full timeline (including debate rounds), then performs the critical step: **updates the knowledge graph**. New patterns are recorded, recurrence counts are incremented, fix strategies are indexed. This is how Reflex learns.

**Smart conditional routing** makes the pipeline adaptive:
- Backlog items skip to postmortem for documentation only
- Low-confidence debate verdicts skip the fix and flag for human investigation
- Failed validation skips deployment and reports concerns

### Flow 2: Proactive Hardening (3 agents)

After an incident is resolved, Reflex hardens the entire codebase:

9. **Pattern Extraction Agent** — Generalizes the specific bug into abstract vulnerability patterns with regex search expressions.

10. **Codebase Scan Agent** — Systematically scans the repository for other instances of the same vulnerability class, verifying each match to eliminate false positives.

11. **Preventive Fix Agent** — Applies fixes across all confirmed vulnerabilities and creates a hardening merge request. Bugs that have not happened yet — prevented.

### Flow 3: Sentinel — Predictive Prevention (3 agents)

The predictive layer that catches incidents before they happen:

12. **Pattern Matcher Agent** — Scans incoming merge request diffs against the knowledge graph. Compares code changes against every known incident signature — direct matches, structural matches, dependency matches, configuration matches.

13. **Risk Assessor Agent** — Aggregates pattern matches into an overall risk verdict. Weighs recency, severity, and confidence to determine whether the MR should proceed, be warned, or be blocked.

14. **Reporter Agent** — Posts clear, evidence-based findings on the MR. When Sentinel warns, it explains exactly which past incident the code resembles and what the developer should check. Organizational memory translated into actionable developer feedback.

### Flow 4: CrossProject — Group-Level Intelligence (3 agents)

One incident, resolved everywhere:

15. **Pattern Broadcaster Agent** — Extracts vulnerability patterns from a resolved incident and prepares them for organization-wide scanning. Enriches patterns with knowledge graph history.

16. **Cross Scanner Agent** — Scans sibling projects in the GitLab group for the same vulnerability. The same anti-pattern — a missing null check, an unvalidated input, a race condition — likely exists in projects built by the same team with the same conventions.

17. **Cross Fixer Agent** — Creates hardening merge requests across every affected project. Each MR includes full context from the knowledge graph, linking the fix to the original incident. One incident triggers protection for all.

### Additional Capabilities

- **Knowledge Graph** — A persistent JSON record of every incident, root cause, fix strategy, pattern, and recurrence. Lives at `.reflex/knowledge/incidents.json` and travels with the repository. Similarity matching connects new incidents to organizational history.

- **Carbon-Aware Scheduler** — Schedules agent execution during low-grid-intensity windows when possible. Every postmortem includes a sustainability report comparing Reflex's carbon footprint against a traditional manual incident response (laptops, monitors, video calls, infrastructure idle time).

- **Incident Dashboard** — Visualizes MTTR trends, incident counts by severity, pattern recurrence heatmaps, active Sentinel warnings, and knowledge graph statistics.

## How we built it

**GitLab Duo Agent Platform** is the backbone. We defined 4 Flow YAML files (`reflex.yaml`, `harden.yaml`, `sentinel.yaml`, `crossproject.yaml`) using the Flow Registry v1 schema, with conditional routers that branch the pipeline based on typed agent output. Every agent is an `AgentComponent` with a detailed system prompt, a curated toolset, structured `response_schema` definitions (JSON Schema draft-07), and explicit input mappings that chain outputs from upstream agents.

**The Debate Protocol** is a first-of-its-kind adversarial verification pattern in a GitLab agent flow. The Root Cause Agent proposes a hypothesis. The Challenger Agent independently verifies the code, tests alternatives, and issues a structured verdict (confirmed/refined/rejected) with specific challenges and resolutions. The Fix Agent then uses the debate-verified analysis. This catches incorrect root causes, discovers additional affected files, and produces better fix strategies through adversarial refinement.

**Structured data passing** is what makes the 17-agent orchestration work. Each agent produces typed JSON output (severity enums, file path arrays, confidence levels, boolean validation flags, debate verdicts) that downstream agents consume as structured input. The routing decisions are based on actual field values — `recommended_priority`, `refined_confidence`, `validation_passed` — not LLM text parsing. This is a typed data pipeline, not prompt chaining.

**The Knowledge Graph** (`incidents.json`) is a Python-managed persistent data structure that records every incident with its patterns, root causes, fix strategies, recurrence counts, and outcomes. The Knowledge Lookup Agent queries it at the start of every incident. The Postmortem Agent updates it at the end. Sentinel reads it on every MR. Pattern similarity matching uses error signatures, affected files, failure types, and category taxonomy.

**External agent** using Claude Code provides deep analysis capabilities — git bisect for finding breaking commits, complex code pattern matching, and automated test execution in a containerized Python 3.11 environment with full shell access.

**Python integration with GCP Cloud Logging and Monitoring** gives agents richer context than pipeline logs alone. The `CloudLoggingClient` queries error logs, extracts deduplicated stack traces, and identifies correlated events around the incident timestamp.

**Carbon-aware scheduler** (`carbon_scheduler.py`) tracks token usage and compute time across every agent step, estimates carbon footprint using published data (Patterson et al. 2021, EPA eGRID 2023, cloud provider PUE adjustments), and schedules non-urgent agent work during low grid intensity windows. Every postmortem includes per-agent breakdowns and total carbon savings versus manual response.

**Playwright E2E test suite** with 40+ tests across 3 spec files validates everything without requiring a live GitLab instance: flow structure validation (all 4 flows, all components, routers, schemas, prompt references, data flow graph), skills validation, API prerequisite checks, and full end-to-end integration tests.

**Demo Flask app** with a realistic intentional bug — a "performance optimization" MR that accesses `users[0]["name"]` on a potentially empty list. This is exactly the kind of subtle bug that passes code review but breaks in production, and it maps to a real pattern in the knowledge graph.

## Challenges we ran into

**Designing the debate protocol routing.** The adversarial debate between Root Cause and Challenger agents required careful orchestration. The Challenger needs the Root Cause output as input, and downstream agents need to handle three possible verdicts (confirmed, refined, rejected) — each with different implications for the fix strategy. Getting the conditional routing to branch on `refined_confidence` after the debate, and ensuring the Fix Agent correctly prioritizes the Challenger's refined analysis over the original hypothesis, required multiple iterations of the schema design.

**Knowledge graph similarity matching.** Comparing a new incident against past incidents is not string matching. We needed to match across error signatures, affected services, code patterns, and failure categories. Designing the knowledge graph schema to support this — with pattern IDs, category taxonomy, recurrence tracking, and cross-incident references — was a data modeling challenge as much as an AI challenge.

**Flow YAML schema was uncharted territory.** The GitLab Duo Agent Platform's flow definition format has limited documentation and few examples. Getting the `response_schema` definitions right so that structured outputs could reliably feed into downstream agent `inputs` via `context:agent_name.final_answer` references took significant iteration. One missing `required` field could silently break data flow between agents.

**Making conditional routing work across 17 agents.** Four flows with conditional branches based on typed field values. The triage router inspects `recommended_priority`. The debate router inspects `refined_confidence`. The validation router inspects `validation_passed`. Each router had to be designed in conjunction with the upstream agent's response schema. We had to think about the entire system as a typed data flow graph.

**Cross-project scanning at group level.** The CrossProject flow needs to reason about sibling projects — their languages, frameworks, and conventions — while only having direct tool access to the current project. Designing the Pattern Broadcaster to prepare search queries generic enough to work across different codebases, while specific enough to avoid false positives, required balancing abstraction with precision.

**Balancing prompt detail with token efficiency.** Each agent needs enough context to act autonomously (security review checklists, debate protocol rules, fix principles, severity rubrics), but prompts cannot consume the token budget before the agent starts working. We found the sweet spot with comprehensive system prompts and minimal user prompts — passing only the structured data each agent actually needs.

## Accomplishments that we're proud of

**First-ever adversarial debate protocol in a GitLab agent flow.** The Root Cause and Challenger agents argue until they converge on the truth. This is not prompt chaining — it is structured adversarial verification with typed verdicts, specific challenges, and resolution records. In our demo scenario, the Challenger caught an incomplete fix strategy that single-pass analysis missed.

**Persistent organizational memory that travels with the code.** The knowledge graph lives in the repository. Every incident, pattern, and fix strategy is indexed. When Reflex sees a new failure, it checks organizational history first. When it resolves an incident, it updates the record. The system gets measurably smarter with every run.

**Predictive prevention that catches bugs BEFORE they merge.** Sentinel reads every incoming MR diff against the knowledge graph. When it finds code that matches a known incident signature, it warns the developer with specific evidence: which past incident, what happened, and what to change. Prevention, not just response.

**Cross-project group-level protection.** When a vulnerability is found in one project, CrossProject broadcasts the pattern across the entire GitLab group, scans sibling projects, and creates hardening MRs. One incident triggers protection for all.

**17 agents across 4 flows with typed data contracts.** Every agent has a distinct role, curated toolset, and structured response schema. Routing decisions are based on typed field values, not text parsing. The system is a typed data pipeline with conditional branching, not a chatbot.

**Full sustainability tracking with carbon-aware scheduling.** The `CarbonTracker` uses peer-reviewed energy estimates and government data to produce defensible carbon comparisons. The carbon-aware scheduler runs non-urgent agents during low grid intensity windows. Every postmortem shows per-agent token breakdowns and total carbon savings — typically 98%+ reduction versus manual incident response.

**Smart conditional routing that knows when to stop.** The pipeline does not blindly run every agent. Backlog items skip to documentation. Low-confidence diagnoses flag for humans rather than generating potentially wrong fixes. Failed validation blocks deployment. The system makes decisions about when automation is appropriate and when to hand off.

## What we learned

**Agent orchestration is a data engineering problem, not just a prompt engineering problem.** The hardest part was not writing good prompts — it was designing the data contracts between 17 agents so that structured outputs reliably flow through routers and into downstream inputs. Typed response schemas and explicit input mappings matter more than clever prompt tricks.

**Adversarial AI verification produces better results than single-pass analysis.** The debate protocol consistently catches issues that a single root cause agent misses: additional affected files, incomplete fix strategies, alternative explanations. Having two agents argue is more reliable than having one agent think harder.

**Knowledge graphs change everything about incident response.** When agents have access to organizational history, every phase gets faster and more accurate. Triage knows whether this is a recurrence. Root cause has a starting hypothesis from a similar past incident. Sentinel can prevent future incidents proactively. Memory is the multiplier.

**Sustainability tracking changes how you think about AI systems.** When you see the per-agent token breakdown and carbon estimate after every run, you start optimizing for efficiency instinctively. It pushed us toward more targeted prompts, smarter routing (skip agents when you can), and the carbon-aware scheduler.

**The GitLab Duo Agent Platform is genuinely powerful for multi-agent workflows.** Flows with conditional routing, structured response schemas, and ambient execution give you real orchestration primitives. The platform handles agent lifecycle, tool access, and context passing, letting us focus on domain logic. We pushed it further than the documentation covers and it held up.

## What's next for Reflex

- **PagerDuty/Opsgenie integration** — Trigger Reflex from real incident management platforms, not just pipeline events
- **ML-based pattern matching** — Replace string/category matching with embedding-based similarity for higher-precision knowledge graph lookups
- **Automatic severity calibration** — Track prediction accuracy over time and adjust severity thresholds from historical data
- **Cross-organization learning** — Opt-in anonymized pattern sharing across organizations, so a vulnerability found at Company A protects Company B
- **Multi-repo incident tracing** — Trace incidents across microservice boundaries, correlating failures in one repo with root causes in another
- **Custom pattern libraries** — Industry-specific vulnerability detection (OWASP for web, CWE for infrastructure, HIPAA for healthcare)
- **Debate protocol expansion** — Multi-round debates for complex incidents, and a jury of multiple challenger agents for critical severity

## Prize Category Qualifications

### Best Overall Agent

Reflex is the most comprehensive multi-agent system in the competition: 17 agents across 4 flows handling the full incident lifecycle from detection through predictive prevention. It demonstrates advanced orchestration patterns (debate protocol, conditional routing, cross-flow data passing), persistent state (knowledge graph), and real-world impact (MTTR reduction from hours to minutes).

### Best Use of Flows (Agentic Workflow Automation)

Four production-grade flows with the Flow Registry v1 schema:
- `reflex.yaml` — 8 agents with 4 conditional routers branching on typed field values
- `harden.yaml` — 3-agent sequential pipeline for codebase-wide vulnerability scanning
- `sentinel.yaml` — 3-agent predictive pipeline that scans MRs against organizational memory
- `crossproject.yaml` — 3-agent pipeline for group-level vulnerability intelligence

The flows demonstrate conditional routing (priority-based, confidence-based, boolean-based), structured data contracts between agents, and the first adversarial debate protocol in a GitLab flow.

### Best Use of Custom Agents

Every one of the 17 agents is custom-built with:
- Specialized system prompts defining a distinct role and responsibility
- Curated toolsets (each agent only has the tools it needs)
- Typed JSON response schemas (JSON Schema draft-07) consumed by downstream agents
- Explicit input mappings from upstream agent outputs

Standout custom agents: the Challenger Agent (adversarial verification), the Knowledge Lookup Agent (organizational memory), the Pattern Matcher Agent (predictive prevention), and the Pattern Broadcaster Agent (cross-project intelligence).

### Best Use of External Agents

The external Claude Code agent provides capabilities beyond the built-in toolset: git bisect for breaking commit detection, complex code pattern matching with shell access, and automated test execution in a containerized Python 3.11 environment. Configured through the GitLab AI Gateway proxy (`ANTHROPIC_BASE_URL` pointing to `cloud.gitlab.com/ai/v1/proxy/anthropic`).

### Best Integration with Google Cloud

Deep integration with GCP Cloud Logging and Cloud Monitoring:
- The `CloudLoggingClient` queries production error logs correlated to the incident timestamp
- Extracts deduplicated stack traces and identifies related events
- Provides agents with production context beyond what pipeline logs contain (e.g., "23 matching errors in the last 6 hours")
- Falls back gracefully to mock data when credentials are unavailable

### Green Agent (Sustainability)

Sustainability is built into the architecture, not bolted on:
- **CarbonTracker** records token usage and compute time per agent step
- Uses published methodology: Patterson et al. 2021 (energy/token), EPA eGRID 2023 (grid intensity), cloud PUE adjustments
- Every postmortem includes a carbon comparison vs. manual response (typically 98%+ reduction)
- **Carbon-aware scheduler** (`carbon_scheduler.py`) defers non-urgent agent work to low grid intensity windows
- Smart conditional routing reduces unnecessary compute: backlog items skip 5 agents, low-confidence diagnoses skip 3 agents

### Best Quality Assurance (Testing)

Playwright E2E test suite with 40+ tests across 3 spec files:
- Flow structure validation for all 4 flows (components, routers, schemas, prompt references, data flow graph integrity)
- Skills validation for all SKILL.md files with proper frontmatter
- API prerequisite checks for live integration testing
- Full end-to-end incident pipeline integration tests
- All tests run without a live GitLab instance

## Built With

- GitLab Duo Agent Platform (Flows + Custom Agents + External Agents)
- Anthropic Claude (via GitLab AI Gateway)
- Google Cloud Logging + Cloud Monitoring
- Python 3.11
- Flask (demo application)
- Playwright (E2E test suite)
- TypeScript (test infrastructure)
- Knowledge Graph (persistent JSON with Python management layer)
- Carbon-Aware Scheduler (EPA eGRID + cloud PUE data)

## Try it out

[GitLab Repository](https://gitlab.com/) | [Demo Video]()
