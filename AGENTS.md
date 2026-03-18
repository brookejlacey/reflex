# Reflex — Adaptive Immune System for GitLab Repositories

## Overview
Reflex is an autonomous, learning incident response system built on the GitLab Duo Agent Platform. It orchestrates 17 specialized AI agents across 4 flows to detect, diagnose, fix, validate, deploy, and prevent software failures — while getting smarter with every incident it handles.

## What Makes Reflex Different
1. **Knowledge Graph** — Persistent organizational memory at `.reflex/knowledge/incidents.json`. Every resolved incident is decomposed into patterns, indexed, and committed to the repo. New incidents are matched against this history so Reflex never starts from scratch.
2. **Debate Protocol** — Root Cause and Challenger agents argue adversarially until they converge. This catches wrong diagnoses before bad fixes are applied.
3. **Predictive Prevention** — The Sentinel flow scans every new MR against the knowledge graph and warns when code matches patterns that previously caused incidents.
4. **Cross-Project Intelligence** — Operates at the GitLab Group level. A fix in one project triggers hardening scans across all sibling projects.
5. **Carbon-Aware Scheduling** — Non-urgent tasks defer to low-carbon grid hours.

## The Four Flows

### 1. reflex.yaml — Main Incident Pipeline (8 agents)
```
Knowledge Lookup → Triage → Root Cause ⟷ Challenger → Fix → Validation → Deploy → Postmortem
```
Triggered by pipeline failures or @mention. The debate protocol between Root Cause and Challenger ensures high-confidence diagnoses. Postmortem updates the knowledge graph.

### 2. sentinel.yaml — Predictive Prevention (3 agents)
```
Pattern Matcher → Risk Assessor → Reporter
```
Triggered by new MR events. Scans code changes against the knowledge graph to warn before bugs merge.

### 3. harden.yaml — Proactive Hardening (3 agents)
```
Pattern Extract → Codebase Scan → Preventive Fix
```
Triggered after incident resolution. Scans codebase for similar vulnerability patterns.

### 4. crossproject.yaml — Group-Level Intelligence (3 agents)
```
Pattern Broadcaster → Cross Scanner → Cross Fixer
```
Triggered after incident resolution. Scans sibling projects in the GitLab group.

## Tech Stack
- GitLab Duo Agent Platform (Flow Registry v1)
- Anthropic Claude (via GitLab AI Gateway)
- Google Cloud Logging + Monitoring
- Python (knowledge graph, GCP integration, sustainability tracking)
- Playwright (E2E testing)

## Code Conventions
- Flow YAML files follow GitLab Flow Registry v1 schema
- All agent outputs use structured JSON Schema (draft-07) response schemas
- Knowledge graph is JSON, committed to repo, versioned with code
- Agent prompts reference organizational memory for context-aware decisions
- Sustainability metrics tracked across all pipeline executions

## Repository Structure
```
reflex/
├── .gitlab/duo/
│   ├── agent-config.yml
│   └── flows/
│       ├── reflex.yaml          # 8-agent incident pipeline with debate
│       ├── sentinel.yaml        # 3-agent predictive prevention
│       ├── harden.yaml          # 3-agent proactive hardening
│       ├── crossproject.yaml    # 3-agent group-level intelligence
│       └── reflex-external.yaml # Claude Code deep analysis
├── .reflex/knowledge/
│   └── incidents.json           # Knowledge graph (organizational memory)
├── skills/                      # 7 standalone agent skills
├── src/
│   ├── knowledge/graph.py       # Knowledge graph CRUD + similarity matching
│   ├── gcp/                     # Cloud Logging + Monitoring integration
│   ├── utils/
│   │   ├── sustainability.py    # Carbon footprint tracking
│   │   ├── carbon_scheduler.py  # Carbon-aware task scheduling
│   │   └── report_generator.py  # Postmortem report templates
│   ├── agents/deep_analyzer.py  # External agent implementation
│   └── demo/                    # Demo scenario
├── dashboard/index.html         # Incident dashboard (GitLab Pages)
├── tests/e2e/                   # Playwright E2E tests
└── docs/                        # Demo script, Devpost submission
```
