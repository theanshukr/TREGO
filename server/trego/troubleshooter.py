"""Troubleshooting Engine for TREGO implementing adaptive diagnosis and recovery."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.trego.diagnostics import DiagnosticEngine, DiagnosticResult


@dataclass
class RecoveryPlan:
    cause: str
    proposed_action: str
    command: str | None = None
    requires_permission: bool = False
    source: str = "diagnostic_engine"  # "diagnostic_engine" | "knowledge_base" | "llm_reasoning"
    confidence: float = 0.85


class Troubleshooter:
    def __init__(self):
        self.diagnostic_engine = DiagnosticEngine()

    def troubleshoot(
        self,
        error_output: str,
        goal_context: str = "",
        computer: Any = None,
        db_client: Any = None,
    ) -> RecoveryPlan:
        """Run the complete troubleshooting diagnostic loop.
        
        1. Collect evidence from error_output
        2. Identify probable causes via DiagnosticEngine
        3. Query Postgres + pgvector Knowledge Base for known similar solutions
        4. Select safe fix with risk classification
        """
        # Step 1: Rule-based fast diagnostic
        diag_res = self.diagnostic_engine.diagnose_error(error_output)
        if diag_res:
            return RecoveryPlan(
                cause=diag_res.probable_cause,
                proposed_action=diag_res.suggested_fix,
                command=diag_res.command_to_fix,
                requires_permission=diag_res.requires_permission,
                source="diagnostic_engine",
                confidence=diag_res.confidence,
            )

        # Step 2: Semantic vector search against pgvector Knowledge Base
        kb_matches = []
        if db_client:
            try:
                search_query = f"{goal_context} {error_output[:200]}"
                kb_matches = db_client.search_similar(search_query, top_k=2)
            except Exception as e:
                print(f"[troubleshooter] KB search error: {e}")

        if kb_matches and kb_matches[0].score > 0.80:
            top = kb_matches[0]
            steps_desc = ", ".join(f"{s.action.name}" for s in top.record.steps)
            return RecoveryPlan(
                cause=f"Matched known solution in Knowledge Base ({top.record.problem_summary})",
                proposed_action=f"Apply verified troubleshooting steps: {steps_desc}",
                source="knowledge_base",
                confidence=top.score,
            )

        # Step 3: Generic fallback recovery plan
        return RecoveryPlan(
            cause="General execution failure",
            proposed_action="Inspect logs, verify dependencies, and retry with adjusted environment configuration.",
            source="llm_reasoning",
            confidence=0.60,
        )
