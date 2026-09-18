"""TREGO Main Orchestrator State Machine.

Coordinates the complete 10-phase pipeline:
Understand -> Inspect -> Diagnose -> Clarify -> Plan -> Ask Permission -> Act -> Troubleshoot -> Verify -> Voice
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable

from server.trego.clarification import ClarificationManager
from server.trego.diagnostics import DiagnosticEngine
from server.trego.goal import GoalInterpreter, GoalObjective
from server.trego.inspector import EnvironmentInspector
from server.trego.modules import get_module
from server.trego.permissions import PermissionManager
from server.trego.troubleshooter import Troubleshooter
from server.trego.verifier import VerificationEngine
from server.trego.voice import ElevenLabsVoice
from shared.command_policy import CommandRisk, evaluate_command
from shared.protocol import AgentEvent, UserMessage

EmitFn = Callable[[AgentEvent], None]


class TregoOrchestrator:
    def __init__(self):
        self.goal_interpreter = GoalInterpreter()
        self.inspector = EnvironmentInspector()
        self.diagnostic_engine = DiagnosticEngine()
        self.clarification_manager = ClarificationManager()
        self.permission_manager = PermissionManager()
        self.troubleshooter = Troubleshooter()
        self.verifier = VerificationEngine()
        self.voice = ElevenLabsVoice()

    def run_pipeline(
        self,
        user_message: UserMessage,
        computer: Any,
        emit: EmitFn,
        *,
        cancel_event: threading.Event | None = None,
        interrupt_event: threading.Event | None = None,
        permission_event: threading.Event | None = None,
        permission_state: dict[str, Any] | None = None,
        db_client: Any = None,
    ) -> dict[str, Any]:
        """Execute the full TREGO workflow."""

        def _is_cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        def _emit_voice(phase: str, details: dict[str, Any]) -> None:
            speech_text = self.voice.craft_speech_message(phase, details)
            if speech_text:
                voice_res = self.voice.synthesize_speech(speech_text)
                emit(AgentEvent(kind="voice_audio", payload=voice_res))

        if _is_cancelled():
            return {"success": False, "summary": "Task cancelled by user."}

        # ------------------------------------------------------------------
        # Phase 1: UNDERSTAND
        # ------------------------------------------------------------------
        emit(AgentEvent(kind="status", payload={"phase": "understand", "msg": "Interpreting user goal..."}))
        goal: GoalObjective = self.goal_interpreter.interpret(user_message.text)
        
        emit(AgentEvent(kind="goal_interpreted", payload={
            "target_stack": goal.target_stack,
            "category": goal.category,
            "target_state": goal.target_state,
            "verification_criteria": goal.verification_criteria,
        }))
        _emit_voice("goal_understood", {"goal": goal.target_stack if goal.target_stack != "general" else "your request"})

        if _is_cancelled():
            return {"success": False, "summary": "Task cancelled by user."}

        # If it's a general GUI/computer-use task without a dedicated dev stack,
        # we can delegate to the classic VLM agent loop or proceed with GUI actions
        if goal.target_stack == "general":
            emit(AgentEvent(kind="status", payload={"phase": "act", "msg": "Executing computer-use action loop..."}))
            # Fallback to standard VLM loop
            from server.agent.agent import run_agent
            cid = getattr(computer, "client_id", "default")
            sol = run_agent(
                user_message,
                emit,
                cancel_event=cancel_event,
                interrupt_event=interrupt_event,
                keyboard_approved_event=permission_event,
                client_id=cid,
            )
            return {
                "success": getattr(sol, "success", True),
                "summary": getattr(sol, "problem_summary", str(sol)),
            }

        # ------------------------------------------------------------------
        # Phase 2: INSPECT
        # ------------------------------------------------------------------
        emit(AgentEvent(kind="status", payload={"phase": "inspect", "msg": f"Inspecting system for {goal.target_stack} environment..."}))
        module_status = self.inspector.inspect_module(goal.target_stack, computer)
        
        emit(AgentEvent(kind="inspection_result", payload={
            "module": goal.target_stack,
            "is_installed": module_status.is_installed,
            "version": module_status.version,
            "healthy": module_status.healthy,
            "issues": module_status.issues,
        }))

        # ------------------------------------------------------------------
        # Phase 3: DIAGNOSE & Phase 4: CLARIFY
        # ------------------------------------------------------------------
        clarification_req = self.clarification_manager.evaluate_ambiguity(goal, module_status)
        if clarification_req:
            emit(AgentEvent(kind="clarification_required", payload={
                "id": clarification_req.id,
                "question": clarification_req.question,
                "options": clarification_req.options,
                "default_option": clarification_req.default_option,
                "context": clarification_req.context,
            }))
            _emit_voice("clarification", {"question": clarification_req.question})

            # In interactive mode, if we already have healthy installation and user just asked to setup,
            # we can verify the existing setup directly if it's already healthy
            if module_status.healthy:
                emit(AgentEvent(kind="status", payload={
                    "phase": "verify",
                    "msg": f"Existing {module_status.version} detected and healthy. Proceeding to verify.",
                }))
                verif_res = self.verifier.verify_environment(goal.target_stack, computer)
                if verif_res.verified:
                    _emit_voice("verified", {"summary": verif_res.evidence, "stack": goal.target_stack})
                    emit(AgentEvent(kind="verification_result", payload={
                        "verified": True,
                        "checks_passed": verif_res.checks_passed,
                        "evidence": verif_res.evidence,
                    }))
                    return {"success": True, "summary": f"{module_status.version} is installed and verified working."}

        # ------------------------------------------------------------------
        # Phase 5: PLAN
        # ------------------------------------------------------------------
        emit(AgentEvent(kind="status", payload={"phase": "plan", "msg": "Generating goal execution plan..."}))
        mod = get_module(goal.target_stack)
        plan_steps = mod.plan(module_status) if mod else []

        plan_payload = [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "command": s.command,
                "requires_permission": s.requires_permission,
                "what": s.what,
                "why": s.why,
                "impact": s.impact,
            }
            for s in plan_steps
        ]
        emit(AgentEvent(kind="plan_created", payload={"steps": plan_payload}))

        # ------------------------------------------------------------------
        # Phase 6: PERMISSION GATE & Phase 7: ACT & Phase 8: TROUBLESHOOT
        # ------------------------------------------------------------------
        for step in plan_steps:
            if _is_cancelled():
                return {"success": False, "summary": "Task cancelled by user."}

            if step.command:
                # Permission check
                perm_prompt = self.permission_manager.evaluate_step(step.command, purpose=step.why or step.description)
                if perm_prompt:
                    emit(AgentEvent(kind="permission_required", payload={
                        "id": perm_prompt.id,
                        "what": perm_prompt.what,
                        "why": perm_prompt.why,
                        "impact": perm_prompt.impact,
                        "command": perm_prompt.command,
                        "risk_level": perm_prompt.risk_level,
                    }))
                    _emit_voice("permission", {"what": perm_prompt.what, "why": perm_prompt.why})

                    # If permission is gated, wait on permission_event
                    if permission_event is not None and not permission_event.is_set():
                        # Pause until user approves or denies
                        emit(AgentEvent(kind="status", payload={"phase": "waiting_permission", "msg": "Waiting for user permission..."}))
                        while not permission_event.is_set():
                            if _is_cancelled():
                                return {"success": False, "summary": "Cancelled while waiting for permission."}
                            time.sleep(0.2)

                # Execute action via Computer-Use Core
                emit(AgentEvent(kind="status", payload={"phase": "act", "msg": f"Executing: {step.title}"}))
                exec_res = computer.run_dev_cmd(step.command, timeout=90)

                # Observe result & Troubleshoot if failed
                if not exec_res.get("ok") or exec_res.get("exit_code") != 0:
                    err_text = exec_res.get("stderr") or exec_res.get("stdout") or exec_res.get("error", "")
                    emit(AgentEvent(kind="status", payload={"phase": "troubleshoot", "msg": f"Action failed, diagnosing: {err_text[:100]}"}))
                    
                    rec_plan = self.troubleshooter.troubleshoot(
                        error_output=err_text,
                        goal_context=f"{goal.target_stack} setup",
                        computer=computer,
                        db_client=db_client,
                    )
                    emit(AgentEvent(kind="troubleshoot_step", payload={
                        "cause": rec_plan.cause,
                        "proposed_action": rec_plan.proposed_action,
                        "source": rec_plan.source,
                        "confidence": rec_plan.confidence,
                    }))
                    _emit_voice("troubleshooting", {"cause": rec_plan.cause})

                    # If troubleshooter produced an executable recovery command, attempt it
                    if rec_plan.command:
                        emit(AgentEvent(kind="status", payload={"phase": "act", "msg": f"Applying recovery fix: {rec_plan.proposed_action}"}))
                        computer.run_dev_cmd(rec_plan.command, timeout=60)

        # ------------------------------------------------------------------
        # Phase 9: VERIFICATION (Mandatory)
        # ------------------------------------------------------------------
        emit(AgentEvent(kind="status", payload={"phase": "verify", "msg": f"Running verification tests for {goal.target_stack}..."}))
        verif_res = self.verifier.verify_environment(goal.target_stack, computer, project_dir=goal.project_path)

        emit(AgentEvent(kind="verification_result", payload={
            "verified": verif_res.verified,
            "checks_passed": verif_res.checks_passed,
            "checks_failed": verif_res.checks_failed,
            "evidence": verif_res.evidence,
            "error_message": verif_res.error_message,
        }))

        # ------------------------------------------------------------------
        # Phase 10: VOICE & RESULT REPORT
        # ------------------------------------------------------------------
        if verif_res.verified:
            _emit_voice("verified", {"summary": verif_res.evidence, "stack": goal.target_stack})
            return {
                "success": True,
                "summary": f"{goal.target_stack.upper()} environment setup and verified successfully. {verif_res.evidence}",
            }
        else:
            _emit_voice("error", {"msg": verif_res.error_message or "Verification checks failed."})
            return {
                "success": False,
                "summary": f"Verification failed: {verif_res.error_message}",
            }
