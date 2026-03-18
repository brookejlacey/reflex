import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import * as yaml from "yaml";

const FLOWS_DIR = path.resolve(__dirname, "../../../.gitlab/duo/flows");
const ROOT = path.resolve(__dirname, "../../..");

function loadFlow(filename: string) {
  const content = fs.readFileSync(path.join(FLOWS_DIR, filename), "utf-8");
  return yaml.parse(content);
}

// ============================================================================
// MAIN PIPELINE — reflex.yaml
// ============================================================================

test.describe("reflex.yaml — Main incident pipeline with debate protocol", () => {
  let flow: any;

  test.beforeAll(() => {
    flow = loadFlow("reflex.yaml");
  });

  test("has valid v1 schema version", () => {
    expect(flow.version).toBe("v1");
  });

  test("uses ambient environment", () => {
    expect(flow.environment).toBe("ambient");
  });

  test("has 8 agents: knowledge + triage + root_cause + challenger + fix + validation + deploy + postmortem", () => {
    const names = flow.components.map((c: any) => c.name);
    expect(names).toContain("knowledge_lookup");
    expect(names).toContain("triage");
    expect(names).toContain("root_cause");
    expect(names).toContain("challenger");
    expect(names).toContain("fix");
    expect(names).toContain("validation");
    expect(names).toContain("deploy");
    expect(names).toContain("postmortem");
    expect(flow.components).toHaveLength(8);
  });

  test("entry point is knowledge_lookup (organizational memory first)", () => {
    expect(flow.flow.entry_point).toBe("knowledge_lookup");
  });

  test("all components are AgentComponents with required fields", () => {
    for (const component of flow.components) {
      expect(component.name).toBeTruthy();
      expect(component.type).toBe("AgentComponent");
      expect(component.prompt_id).toBeTruthy();
      expect(component.toolset).toBeInstanceOf(Array);
      expect(component.toolset.length).toBeGreaterThan(0);
      expect(component.inputs).toBeInstanceOf(Array);
      expect(component.response_schema).toBeTruthy();
    }
  });

  test("all components have JSON Schema draft-07 response schemas", () => {
    for (const component of flow.components) {
      const schema = component.response_schema;
      expect(schema.$schema).toBe("http://json-schema.org/draft-07/schema#");
      expect(schema.type).toBe("object");
      expect(schema.properties).toBeTruthy();
      expect(schema.required).toBeInstanceOf(Array);
      expect(schema.required.length).toBeGreaterThan(0);
    }
  });

  test("every prompt_id has a matching prompt definition", () => {
    const promptIds = flow.prompts.map((p: any) => p.prompt_id);
    for (const component of flow.components) {
      expect(promptIds).toContain(component.prompt_id);
    }
  });

  test("all prompts have detailed system and user templates", () => {
    for (const prompt of flow.prompts) {
      expect(prompt.prompt_template.system).toBeTruthy();
      expect(prompt.prompt_template.user).toBeTruthy();
      expect(prompt.prompt_template.system.length).toBeGreaterThan(100);
    }
  });

  // --- DEBATE PROTOCOL TESTS ---

  test("challenger agent exists and receives root_cause hypothesis", () => {
    const challenger = flow.components.find((c: any) => c.name === "challenger");
    expect(challenger).toBeTruthy();
    const inputs = challenger.inputs.map((i: any) => i.from);
    expect(inputs).toContain("context:root_cause.final_answer");
  });

  test("challenger has verdict enum: confirmed/refined/rejected", () => {
    const challenger = flow.components.find((c: any) => c.name === "challenger");
    const verdict = challenger.response_schema.properties.verdict;
    expect(verdict.enum).toContain("confirmed");
    expect(verdict.enum).toContain("refined");
    expect(verdict.enum).toContain("rejected");
  });

  test("fix agent receives debate result from challenger", () => {
    const fix = flow.components.find((c: any) => c.name === "fix");
    const inputs = fix.inputs.map((i: any) => i.from);
    expect(inputs).toContain("context:challenger.final_answer");
  });

  // --- KNOWLEDGE GRAPH TESTS ---

  test("knowledge_lookup is the first component", () => {
    expect(flow.components[0].name).toBe("knowledge_lookup");
  });

  test("knowledge_lookup has is_recurrence detection", () => {
    const kl = flow.components.find((c: any) => c.name === "knowledge_lookup");
    expect(kl.response_schema.properties.is_recurrence).toBeTruthy();
    expect(kl.response_schema.properties.similar_incidents).toBeTruthy();
  });

  test("triage receives knowledge context", () => {
    const triage = flow.components.find((c: any) => c.name === "triage");
    const inputs = triage.inputs.map((i: any) => i.from);
    expect(inputs).toContain("context:knowledge_lookup.final_answer");
  });

  test("postmortem has knowledge_graph_update in response schema", () => {
    const pm = flow.components.find((c: any) => c.name === "postmortem");
    expect(pm.response_schema.properties.knowledge_graph_update).toBeTruthy();
  });

  // --- ROUTING TESTS ---

  test("knowledge_lookup routes to triage", () => {
    const router = flow.routers.find((r: any) => r.from === "knowledge_lookup");
    expect(router.to).toBe("triage");
  });

  test("root_cause routes to challenger (debate protocol)", () => {
    const router = flow.routers.find((r: any) => r.from === "root_cause");
    expect(router.to).toBe("challenger");
  });

  test("challenger routes based on refined_confidence", () => {
    const router = flow.routers.find((r: any) => r.from === "challenger");
    expect(router.condition).toBeTruthy();
    expect(router.condition.input).toContain("refined_confidence");
    expect(Object.values(router.condition.routes)).toContain("fix");
    expect(Object.values(router.condition.routes)).toContain("postmortem");
  });

  test("full routing chain: knowledge → triage → root_cause → challenger → fix → validation → deploy → postmortem → end", () => {
    const routers = flow.routers;

    // Verify all expected nodes have outgoing routes
    const fromNodes = routers.map((r: any) => r.from);
    expect(fromNodes).toContain("knowledge_lookup");
    expect(fromNodes).toContain("triage");
    expect(fromNodes).toContain("root_cause");
    expect(fromNodes).toContain("challenger");
    expect(fromNodes).toContain("fix");
    expect(fromNodes).toContain("validation");
    expect(fromNodes).toContain("deploy");
    expect(fromNodes).toContain("postmortem");

    // Postmortem routes to end
    const pmRouter = routers.find((r: any) => r.from === "postmortem");
    expect(pmRouter.to).toBe("end");
  });

  test("data flows correctly through debate protocol", () => {
    const getInputSources = (name: string) => {
      const component = flow.components.find((c: any) => c.name === name);
      return component.inputs.map((i: any) => i.from);
    };

    // Root cause gets knowledge context
    expect(getInputSources("root_cause")).toContain("context:knowledge_lookup.final_answer");

    // Challenger gets root_cause hypothesis
    expect(getInputSources("challenger")).toContain("context:root_cause.final_answer");

    // Fix gets debate result
    expect(getInputSources("fix")).toContain("context:challenger.final_answer");

    // Postmortem gets EVERYTHING including debate and knowledge
    const pmInputs = getInputSources("postmortem");
    expect(pmInputs).toContain("context:knowledge_lookup.final_answer");
    expect(pmInputs).toContain("context:root_cause.final_answer");
    expect(pmInputs).toContain("context:challenger.final_answer");
    expect(pmInputs).toContain("context:fix.final_answer");
    expect(pmInputs).toContain("context:deploy.final_answer");
  });

  test("toolsets are appropriate for each agent role", () => {
    const toolsOf = (name: string) =>
      flow.components.find((c: any) => c.name === name).toolset;

    // Knowledge lookup reads files
    expect(toolsOf("knowledge_lookup")).toContain("read_file");

    // Triage can comment on issues
    expect(toolsOf("triage")).toContain("create_issue_note");

    // Fix can edit files
    expect(toolsOf("fix")).toContain("edit_file");

    // Deploy can create MRs
    expect(toolsOf("deploy")).toContain("create_merge_request");

    // Postmortem can update knowledge graph
    expect(toolsOf("postmortem")).toContain("edit_file");
    expect(toolsOf("postmortem")).toContain("create_file_with_contents");
  });
});

// ============================================================================
// HARDEN FLOW
// ============================================================================

test.describe("harden.yaml — Proactive hardening flow", () => {
  let flow: any;

  test.beforeAll(() => {
    flow = loadFlow("harden.yaml");
  });

  test("has valid v1 schema", () => {
    expect(flow.version).toBe("v1");
    expect(flow.environment).toBe("ambient");
  });

  test("has 3 components in linear pipeline", () => {
    expect(flow.components).toHaveLength(3);
    expect(flow.flow.entry_point).toBe("pattern_extract");
  });

  test("forms linear pipeline: extract → scan → fix → end", () => {
    expect(flow.routers[0]).toEqual({ from: "pattern_extract", to: "codebase_scan" });
    expect(flow.routers[1]).toEqual({ from: "codebase_scan", to: "preventive_fix" });
    expect(flow.routers[2]).toEqual({ from: "preventive_fix", to: "end" });
  });
});

// ============================================================================
// SENTINEL FLOW
// ============================================================================

test.describe("sentinel.yaml — Predictive prevention flow", () => {
  let flow: any;

  test.beforeAll(() => {
    flow = loadFlow("sentinel.yaml");
  });

  test("has valid v1 schema", () => {
    expect(flow.version).toBe("v1");
    expect(flow.environment).toBe("ambient");
  });

  test("has 3 predictive pipeline components", () => {
    const names = flow.components.map((c: any) => c.name);
    expect(names).toContain("pattern_matcher");
    expect(names).toContain("risk_assessor");
    expect(names).toContain("reporter");
  });

  test("all components have response schemas", () => {
    for (const component of flow.components) {
      expect(component.response_schema).toBeTruthy();
      expect(component.response_schema.required.length).toBeGreaterThan(0);
    }
  });
});

// ============================================================================
// CROSSPROJECT FLOW
// ============================================================================

test.describe("crossproject.yaml — Group-level intelligence flow", () => {
  let flow: any;

  test.beforeAll(() => {
    flow = loadFlow("crossproject.yaml");
  });

  test("has valid v1 schema", () => {
    expect(flow.version).toBe("v1");
    expect(flow.environment).toBe("ambient");
  });

  test("has 3 cross-project components", () => {
    const names = flow.components.map((c: any) => c.name);
    expect(names).toContain("pattern_broadcaster");
    expect(names).toContain("cross_scanner");
    expect(names).toContain("cross_fixer");
  });

  test("cross_fixer can create merge requests", () => {
    const fixer = flow.components.find((c: any) => c.name === "cross_fixer");
    expect(fixer.toolset).toContain("create_merge_request");
  });
});

// ============================================================================
// SKILLS
// ============================================================================

test.describe("Skills Validation", () => {
  const SKILLS_DIR = path.resolve(__dirname, "../../../skills");

  const expectedSkills = [
    "triage", "root-cause", "fix", "validation",
    "deploy", "postmortem", "harden",
  ];

  for (const skill of expectedSkills) {
    test(`${skill}/SKILL.md exists with valid frontmatter`, () => {
      const content = fs.readFileSync(
        path.join(SKILLS_DIR, skill, "SKILL.md"), "utf-8"
      );
      expect(content.startsWith("---")).toBe(true);
      const endIdx = content.indexOf("---", 3);
      expect(endIdx).toBeGreaterThan(3);
      const fm = content.substring(3, endIdx);
      expect(fm).toContain("name:");
      expect(fm).toContain("description:");
    });
  }
});

// ============================================================================
// KNOWLEDGE GRAPH
// ============================================================================

test.describe("Knowledge Graph", () => {
  test("incidents.json exists and is valid", () => {
    const p = path.join(ROOT, ".reflex/knowledge/incidents.json");
    expect(fs.existsSync(p)).toBe(true);
    const data = JSON.parse(fs.readFileSync(p, "utf-8"));
    expect(data.version).toBe("1.0");
    expect(data.incidents).toBeInstanceOf(Array);
    expect(data.incidents.length).toBeGreaterThan(0);
  });

  test("each incident has required fields", () => {
    const data = JSON.parse(
      fs.readFileSync(path.join(ROOT, ".reflex/knowledge/incidents.json"), "utf-8")
    );
    for (const incident of data.incidents) {
      expect(incident.incident_id).toBeTruthy();
      expect(incident.title).toBeTruthy();
      expect(incident.severity).toBeTruthy();
      expect(incident.root_cause_summary).toBeTruthy();
      expect(incident.patterns).toBeInstanceOf(Array);
      expect(incident.patterns.length).toBeGreaterThan(0);
      expect(incident.lessons_learned).toBeInstanceOf(Array);
    }
  });

  test("patterns have searchable signatures", () => {
    const data = JSON.parse(
      fs.readFileSync(path.join(ROOT, ".reflex/knowledge/incidents.json"), "utf-8")
    );
    for (const incident of data.incidents) {
      for (const pattern of incident.patterns) {
        expect(pattern.pattern_id).toBeTruthy();
        expect(pattern.category).toBeTruthy();
        expect(pattern.signature).toBeTruthy();
        expect(pattern.search_regex).toBeTruthy();
      }
    }
  });

  test("related incidents cross-reference correctly", () => {
    const data = JSON.parse(
      fs.readFileSync(path.join(ROOT, ".reflex/knowledge/incidents.json"), "utf-8")
    );
    const ids = new Set(data.incidents.map((i: any) => i.incident_id));
    for (const incident of data.incidents) {
      for (const relId of incident.related_incidents || []) {
        expect(ids.has(relId)).toBe(true);
      }
    }
  });
});

// ============================================================================
// DASHBOARD
// ============================================================================

test.describe("Dashboard", () => {
  test("index.html exists", () => {
    expect(fs.existsSync(path.join(ROOT, "dashboard/index.html"))).toBe(true);
  });

  test("dashboard contains required sections", () => {
    const html = fs.readFileSync(
      path.join(ROOT, "dashboard/index.html"), "utf-8"
    );
    expect(html).toContain("Reflex");
    expect(html).toContain("chart");
  });
});

// ============================================================================
// PROJECT STRUCTURE
// ============================================================================

test.describe("Project Structure", () => {
  const requiredFiles = [
    "AGENTS.md",
    "LICENSE",
    "README.md",
    "requirements.txt",
    ".gitlab/duo/agent-config.yml",
    ".gitlab/duo/flows/reflex.yaml",
    ".gitlab/duo/flows/harden.yaml",
    ".gitlab/duo/flows/sentinel.yaml",
    ".gitlab/duo/flows/crossproject.yaml",
    ".gitlab-ci.yml",
    ".reflex/knowledge/incidents.json",
    "dashboard/index.html",
    "src/knowledge/graph.py",
    "src/utils/sustainability.py",
    "src/utils/carbon_scheduler.py",
  ];

  for (const file of requiredFiles) {
    test(`${file} exists`, () => {
      expect(fs.existsSync(path.join(ROOT, file))).toBe(true);
    });
  }
});
