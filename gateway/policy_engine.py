"""Loads AgentgatewayPolicy YAML resources and evaluates their CEL rules.

This is the enforcement core of the control plane: every policy's `rule.cel`
expression is compiled with celpy (a real CEL implementation, the same
expression language agentgateway's AgentgatewayPolicy CRDs use) and evaluated
against a resource snapshot the gateway fetches itself. Agents never see or
influence this evaluation — they only get an allow/deny response.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import celpy
import yaml
from celpy import celtypes

POLICIES_DIR = Path(__file__).parent / "policies"


@dataclass
class Policy:
    name: str
    target: dict
    cel_expr: str
    deny_reason: str
    include_unsourced_claims: bool = False
    rollback_on_deny: bool = False


class PolicyEngine:
    def __init__(self, policies_dir: Path = POLICIES_DIR):
        self._env = celpy.Environment()
        self.policies: dict[str, Policy] = {}
        self._programs: dict[str, Any] = {}
        for path in sorted(policies_dir.glob("*.yaml")):
            doc = yaml.safe_load(path.read_text())
            spec = doc["spec"]
            name = doc["metadata"]["name"]
            on_deny = spec.get("onDeny", {})
            policy = Policy(
                name=name,
                target=spec["target"],
                cel_expr=spec["rule"]["cel"],
                deny_reason=on_deny.get("reason", "Denied by policy."),
                include_unsourced_claims=on_deny.get("includeUnsourcedClaims", False),
                rollback_on_deny=on_deny.get("rollbackOnDeny", False),
            )
            self.policies[name] = policy
            self._programs[name] = self._env.program(self._env.compile(policy.cel_expr))

    def evaluate(
        self,
        policy_name: str,
        resource: dict | None = None,
        request: dict | None = None,
        extra_activation: dict | None = None,
        functions: dict[str, Callable] | None = None,
    ) -> bool:
        policy = self.policies[policy_name]
        activation: dict[str, Any] = {}
        if resource is not None:
            activation["resource"] = celpy.json_to_cel(resource)
        if request is not None:
            activation["request"] = celpy.json_to_cel(request)
        if extra_activation:
            activation.update(extra_activation)

        program = self._env.program(self._env.compile(policy.cel_expr), functions=functions) if functions else self._programs[policy_name]
        result = program.evaluate(activation)
        return bool(result)

    def reason(self, policy_name: str) -> str:
        return self.policies[policy_name].deny_reason

    def include_unsourced_claims(self, policy_name: str) -> bool:
        return self.policies[policy_name].include_unsourced_claims


engine = PolicyEngine()
