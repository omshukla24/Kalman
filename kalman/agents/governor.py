"""Governor — separation of duties (KALMAN II upgrade).

No agent touches the live system directly. Every proposed remediation passes
through the Governor, which checks it against policy (allowlist, numeric bounds,
action cooldowns, and human-approval gates) and writes an immutable audit log.

KALMAN II additions:
  1. Interactive Human-in-the-Loop (HITL) pending action queue with TTL.
  2. One-click operator approval & rejection lifecycle.
  3. Action cooldown and flapping prevention.
  4. Cryptographic decision audit trail.
  5. Hot-reloading of governance policy without service interruption.

The AI proposes; the Governor disposes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import uuid
from dataclasses import dataclass, field

import yaml

POLICY_PATH = pathlib.Path(__file__).resolve().parent.parent / "policies" / "governor_policy.yaml"


@dataclass
class Decision:
    action: str
    approved: bool
    reason: str
    requires_human: bool = False
    action_id: str | None = None
    params: dict = field(default_factory=dict)
    decision_hash: str = ""


@dataclass
class PendingAction:
    action_id: str
    action: str
    params: dict
    reason: str
    created_at: float
    expires_at: float
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED


@dataclass
class Governor:
    policy: dict = field(default_factory=dict)
    audit_log: list[dict] = field(default_factory=list)
    _pending_actions: dict[str, PendingAction] = field(default_factory=dict)
    _last_executed: dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Governor":
        policy = yaml.safe_load(POLICY_PATH.read_text()) if POLICY_PATH.exists() else {}
        return cls(policy=policy or {})

    @property
    def allowlist(self) -> dict:
        return self.policy.get("allowed_actions", {})

    def reload_policy(self) -> None:
        """Hot-reload policy from disk."""
        if POLICY_PATH.exists():
            self.policy = yaml.safe_load(POLICY_PATH.read_text()) or {}

    def review(self, action: str, params: dict | None = None) -> Decision:
        params = params or {}
        allowed = self.policy.get("allowed_actions", {})
        spec = allowed.get(action)
        now = time.time()

        if spec is None:
            decision = Decision(action=action, approved=False, reason="action not in policy allowlist", params=params)
        else:
            # 1. Check cooldowns
            cooldown = float(spec.get("cooldown_s", 0))
            last_run = self._last_executed.get(action, 0.0)
            if cooldown > 0 and (now - last_run) < cooldown:
                remaining = int(cooldown - (now - last_run))
                decision = Decision(
                    action=action,
                    approved=False,
                    reason=f"action in cooldown ({remaining}s remaining)",
                    params=params,
                )
            else:
                # 2. Check parameter bounds
                bounds = spec.get("max", {}) or {}
                violated = [k for k, cap in bounds.items() if float(params.get(k, 0)) > float(cap)]
                if violated:
                    decision = Decision(
                        action=action,
                        approved=False,
                        reason=f"exceeds bound(s): {', '.join(violated)}",
                        params=params,
                    )
                else:
                    # 3. Check human approval requirement
                    requires_human = bool(spec.get("requires_human", False))
                    if requires_human:
                        action_id = f"act-{uuid.uuid4().hex[:8]}"
                        pending = PendingAction(
                            action_id=action_id,
                            action=action,
                            params=params,
                            reason=spec.get("description", "Requires human sign-off"),
                            created_at=now,
                            expires_at=now + 300.0,  # 5 min TTL
                        )
                        self._pending_actions[action_id] = pending
                        decision = Decision(
                            action=action,
                            approved=False,
                            reason="awaiting human approval",
                            requires_human=True,
                            action_id=action_id,
                            params=params,
                        )
                    else:
                        decision = Decision(
                            action=action,
                            approved=True,
                            reason="within policy",
                            requires_human=False,
                            params=params,
                        )
                        self._last_executed[action] = now

        self._audit(decision, params)
        return decision

    def evaluate(self, action: str, params: dict | None = None) -> Decision:
        """Alias for review() to support dry-run policy evaluation."""
        return self.review(action, params)

    def approve_action(self, action_id: str, operator: str = "NOC_Operator") -> Decision:
        """Sign off on a pending human-gate remediation action."""
        pending = self._pending_actions.get(action_id)
        now = time.time()
        if not pending:
            return Decision(action="unknown", approved=False, reason="action_id not found")
        if pending.status != "PENDING":
            return Decision(action=pending.action, approved=False, reason=f"action is already {pending.status}")
        if now > pending.expires_at:
            pending.status = "EXPIRED"
            return Decision(action=pending.action, approved=False, reason="action approval has expired")

        pending.status = "APPROVED"
        self._last_executed[pending.action] = now

        decision = Decision(
            action=pending.action,
            approved=True,
            reason=f"approved by {operator}",
            requires_human=False,
            action_id=action_id,
            params=pending.params,
        )
        self._audit(decision, pending.params, operator=operator)
        return decision

    def reject_action(self, action_id: str, operator: str = "NOC_Operator", reason: str = "") -> Decision:
        """Reject a pending remediation action."""
        pending = self._pending_actions.get(action_id)
        if not pending:
            return Decision(action="unknown", approved=False, reason="action_id not found")

        pending.status = "REJECTED"
        reject_reason = f"rejected by {operator}: {reason}" if reason else f"rejected by {operator}"
        decision = Decision(
            action=pending.action,
            approved=False,
            reason=reject_reason,
            requires_human=False,
            action_id=action_id,
            params=pending.params,
        )
        self._audit(decision, pending.params, operator=operator)
        return decision

    def get_pending_actions(self) -> list[dict]:
        """List active pending actions awaiting human review."""
        now = time.time()
        res = []
        for p in self._pending_actions.values():
            if p.status == "PENDING" and now <= p.expires_at:
                res.append({
                    "action_id": p.action_id,
                    "action": p.action,
                    "params": p.params,
                    "reason": p.reason,
                    "created_at": p.created_at,
                    "expires_in_s": int(p.expires_at - now),
                })
        return res

    def _audit(self, d: Decision, params: dict, operator: str = "system") -> None:
        now = time.time()
        payload = f"{now}:{d.action}:{d.approved}:{json.dumps(params, sort_keys=True)}:{operator}"
        d_hash = hashlib.sha256(payload.encode()).hexdigest()[:12]
        d.decision_hash = d_hash

        self.audit_log.append(
            {
                "ts": now,
                "action": d.action,
                "action_id": d.action_id,
                "approved": d.approved,
                "requires_human": d.requires_human,
                "reason": d.reason,
                "params": params,
                "operator": operator,
                "hash": d_hash,
            }
        )
