"""
Reflex Knowledge Graph — Organizational incident memory.

A JSON-based pattern store committed to the repository. Each resolved incident
creates a node containing the failure signature, root cause, fix strategy, and
outcome. When a new incident arrives, the graph is searched for similar patterns
so Reflex can leverage past experience instead of starting from scratch.

Over time the knowledge graph turns Reflex from a stateless pipeline into an
adaptive system that gets smarter with every incident it handles.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional


# Default location inside the repo
DEFAULT_GRAPH_PATH = ".reflex/knowledge/incidents.json"


@dataclass
class IncidentPattern:
    """A single pattern extracted from a resolved incident."""

    pattern_id: str
    name: str
    description: str
    category: str  # null_reference, dependency, config, race_condition, auth, resource_exhaustion, type_error, logic_error
    signature: str  # normalized code/error signature for matching
    search_regex: str  # regex to find this pattern in codebases
    risk_level: str  # critical, high, medium, low
    affected_languages: list[str] = field(default_factory=list)
    affected_frameworks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IncidentNode:
    """A node in the knowledge graph representing a resolved incident."""

    incident_id: str
    title: str
    severity: str
    failure_type: str
    root_cause_summary: str
    fix_strategy: str
    fix_type: str
    patterns: list[IncidentPattern]
    affected_files: list[str]
    affected_services: list[str]
    breaking_commit: Optional[str] = None
    fix_commit: Optional[str] = None
    merge_request_url: Optional[str] = None
    resolution_time_seconds: Optional[float] = None
    fix_successful: bool = True
    recurrence_count: int = 0
    related_incidents: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    resolved_at: str = ""
    postmortem_path: Optional[str] = None
    sustainability_metrics: dict[str, Any] = field(default_factory=dict)
    lessons_learned: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["patterns"] = [p.to_dict() if isinstance(p, IncidentPattern) else p for p in self.patterns]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IncidentNode:
        patterns_data = data.pop("patterns", [])
        patterns = []
        for p in patterns_data:
            if isinstance(p, IncidentPattern):
                patterns.append(p)
            else:
                patterns.append(IncidentPattern(**p))
        return cls(patterns=patterns, **data)


@dataclass
class KnowledgeGraphStats:
    """Summary statistics for the knowledge graph."""

    total_incidents: int
    total_patterns: int
    incidents_by_severity: dict[str, int]
    incidents_by_category: dict[str, int]
    top_recurring_patterns: list[dict[str, Any]]
    avg_resolution_time_seconds: float
    fix_success_rate: float
    total_recurrences: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KnowledgeGraph:
    """
    Persistent knowledge graph for incident patterns and organizational memory.

    The graph is stored as a JSON file in the repository so it travels with the
    code and is versioned alongside it. This means:
    - Every team member has access to the full incident history
    - Git blame shows when patterns were added
    - The knowledge graph itself can be code-reviewed
    """

    def __init__(self, graph_path: Optional[str] = None):
        self.graph_path = Path(graph_path or DEFAULT_GRAPH_PATH)
        self.incidents: list[IncidentNode] = []
        self._load()

    def _load(self) -> None:
        """Load the knowledge graph from disk."""
        if not self.graph_path.exists():
            self.incidents = []
            return

        try:
            with open(self.graph_path, "r") as f:
                data = json.load(f)
            self.incidents = [
                IncidentNode.from_dict(node) for node in data.get("incidents", [])
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.incidents = []

    def save(self) -> None:
        """Persist the knowledge graph to disk."""
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stats": self.stats().to_dict(),
            "incidents": [node.to_dict() for node in self.incidents],
        }
        with open(self.graph_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def add_incident(self, node: IncidentNode) -> None:
        """Add a resolved incident to the knowledge graph."""
        # Check for duplicates
        existing_ids = {n.incident_id for n in self.incidents}
        if node.incident_id in existing_ids:
            # Update existing
            self.incidents = [
                node if n.incident_id == node.incident_id else n
                for n in self.incidents
            ]
        else:
            self.incidents.append(node)

        # Check for recurrences — similar patterns seen before
        for existing in self.incidents:
            if existing.incident_id == node.incident_id:
                continue
            for new_pattern in node.patterns:
                for old_pattern in existing.patterns:
                    if self._pattern_similarity(new_pattern, old_pattern) > 0.7:
                        existing.recurrence_count += 1
                        if node.incident_id not in existing.related_incidents:
                            existing.related_incidents.append(node.incident_id)
                        if existing.incident_id not in node.related_incidents:
                            node.related_incidents.append(existing.incident_id)

        self.save()

    def search_similar(
        self,
        error_signature: str,
        failure_type: Optional[str] = None,
        threshold: float = 0.5,
        max_results: int = 5,
    ) -> list[tuple[IncidentNode, float]]:
        """
        Search the knowledge graph for incidents similar to the given error.

        Returns a list of (incident, similarity_score) tuples sorted by relevance.
        """
        results: list[tuple[IncidentNode, float]] = []

        for node in self.incidents:
            score = 0.0

            # Match against root cause summary
            score = max(score, SequenceMatcher(
                None, error_signature.lower(), node.root_cause_summary.lower()
            ).ratio())

            # Match against pattern signatures
            for pattern in node.patterns:
                sig_score = SequenceMatcher(
                    None, error_signature.lower(), pattern.signature.lower()
                ).ratio()
                score = max(score, sig_score)

                # Exact category match bonus
                if failure_type and pattern.category == failure_type:
                    score = min(1.0, score + 0.15)

            if score >= threshold:
                results.append((node, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def search_by_pattern(
        self,
        category: Optional[str] = None,
        risk_level: Optional[str] = None,
        service: Optional[str] = None,
    ) -> list[IncidentNode]:
        """Search incidents by pattern attributes."""
        results = []
        for node in self.incidents:
            match = True
            if category:
                if not any(p.category == category for p in node.patterns):
                    match = False
            if risk_level:
                if not any(p.risk_level == risk_level for p in node.patterns):
                    match = False
            if service:
                if service not in node.affected_services:
                    match = False
            if match:
                results.append(node)
        return results

    def get_pattern_frequency(self) -> dict[str, int]:
        """Get frequency count of each pattern category across all incidents."""
        freq: dict[str, int] = {}
        for node in self.incidents:
            for pattern in node.patterns:
                freq[pattern.category] = freq.get(pattern.category, 0) + 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))

    def get_recurring_patterns(self, min_occurrences: int = 2) -> list[dict[str, Any]]:
        """Find patterns that have caused multiple incidents."""
        pattern_map: dict[str, list[str]] = {}
        pattern_details: dict[str, IncidentPattern] = {}

        for node in self.incidents:
            for pattern in node.patterns:
                key = f"{pattern.category}:{pattern.name}"
                if key not in pattern_map:
                    pattern_map[key] = []
                    pattern_details[key] = pattern
                pattern_map[key].append(node.incident_id)

        recurring = []
        for key, incident_ids in pattern_map.items():
            if len(incident_ids) >= min_occurrences:
                recurring.append({
                    "pattern": pattern_details[key].to_dict(),
                    "occurrences": len(incident_ids),
                    "incident_ids": incident_ids,
                })

        recurring.sort(key=lambda x: x["occurrences"], reverse=True)
        return recurring

    def stats(self) -> KnowledgeGraphStats:
        """Generate summary statistics for the knowledge graph."""
        if not self.incidents:
            return KnowledgeGraphStats(
                total_incidents=0, total_patterns=0,
                incidents_by_severity={}, incidents_by_category={},
                top_recurring_patterns=[], avg_resolution_time_seconds=0,
                fix_success_rate=0, total_recurrences=0,
            )

        severity_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        resolution_times: list[float] = []
        success_count = 0

        for node in self.incidents:
            severity_counts[node.severity] = severity_counts.get(node.severity, 0) + 1
            if node.fix_successful:
                success_count += 1
            if node.resolution_time_seconds:
                resolution_times.append(node.resolution_time_seconds)
            for pattern in node.patterns:
                category_counts[pattern.category] = category_counts.get(pattern.category, 0) + 1

        return KnowledgeGraphStats(
            total_incidents=len(self.incidents),
            total_patterns=sum(len(n.patterns) for n in self.incidents),
            incidents_by_severity=severity_counts,
            incidents_by_category=category_counts,
            top_recurring_patterns=self.get_recurring_patterns()[:5],
            avg_resolution_time_seconds=(
                sum(resolution_times) / len(resolution_times) if resolution_times else 0
            ),
            fix_success_rate=(
                success_count / len(self.incidents) if self.incidents else 0
            ),
            total_recurrences=sum(n.recurrence_count for n in self.incidents),
        )

    def export_for_prompt(self, max_entries: int = 10) -> str:
        """
        Export the knowledge graph as a concise string for inclusion in agent
        prompts. This gives agents access to organizational memory.
        """
        if not self.incidents:
            return "No prior incidents in knowledge graph."

        lines = [f"Knowledge Graph: {len(self.incidents)} past incidents\n"]

        # Include stats
        stats = self.stats()
        lines.append(f"Fix success rate: {stats.fix_success_rate:.0%}")
        if stats.top_recurring_patterns:
            lines.append("Recurring patterns:")
            for rp in stats.top_recurring_patterns[:3]:
                lines.append(f"  - {rp['pattern']['name']} ({rp['occurrences']}x)")
        lines.append("")

        # Include most recent incidents
        recent = sorted(self.incidents, key=lambda n: n.created_at, reverse=True)[:max_entries]
        for node in recent:
            patterns_str = ", ".join(p.name for p in node.patterns[:3])
            lines.append(
                f"- [{node.severity}] {node.title}: {node.root_cause_summary[:100]}... "
                f"Patterns: {patterns_str}. Fix: {node.fix_strategy[:80]}..."
            )

        return "\n".join(lines)

    @staticmethod
    def _pattern_similarity(a: IncidentPattern, b: IncidentPattern) -> float:
        """Compute similarity between two patterns."""
        if a.category != b.category:
            return 0.0
        sig_sim = SequenceMatcher(None, a.signature.lower(), b.signature.lower()).ratio()
        name_sim = SequenceMatcher(None, a.name.lower(), b.name.lower()).ratio()
        return 0.6 * sig_sim + 0.4 * name_sim

    @staticmethod
    def generate_pattern_id(name: str, category: str) -> str:
        """Generate a deterministic pattern ID."""
        raw = f"{category}:{name}".lower()
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
