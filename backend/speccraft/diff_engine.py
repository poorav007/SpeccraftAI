"""Specification Diff Engine for SpecCraft AI.

Compares two OpenAPI 3.0 specification documents (Baseline S1 vs Target S2),
identifies added, removed, and modified endpoints, parameters, and schemas,
and deterministically classifies each change into Breaking vs Non-Breaking.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import yaml

from speccraft.models import ChangeType, DiffChangeRecord, DiffReport, DiffSummary


class SpecDiffEngine:
    """Deterministic comparison engine for OpenAPI 3.0 specifications."""

    @staticmethod
    def _parse_spec_input(spec_input: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Normalize spec input into a clean Python dictionary."""
        if isinstance(spec_input, dict):
            return spec_input

        if isinstance(spec_input, str):
            text = spec_input.strip()
            if text.startswith("{") or text.startswith("["):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
            try:
                parsed = yaml.safe_load(text)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        raise ValueError("Invalid specification input. Must be a valid JSON or YAML object.")

    @staticmethod
    def _normalize_operations(
        spec_dict: Dict[str, Any]
    ) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Map all operations in an OpenAPI spec into a dictionary keyed by (path, method_lower)."""
        operations: Dict[Tuple[str, str], Dict[str, Any]] = {}
        paths = spec_dict.get("paths", {})
        if not isinstance(paths, dict):
            return operations

        http_methods = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}

        for path_str, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method_str, op_dict in path_item.items():
                m_lower = method_str.lower()
                if m_lower in http_methods and isinstance(op_dict, dict):
                    operations[(path_str, m_lower)] = op_dict

        return operations

    def compare(
        self,
        baseline_input: Union[Dict[str, Any], str],
        target_input: Union[Dict[str, Any], str],
    ) -> DiffReport:
        """Compare baseline (S1) against target (S2) and generate a DiffReport."""
        baseline = self._parse_spec_input(baseline_input)
        target = self._parse_spec_input(target_input)

        baseline_ops = self._normalize_operations(baseline)
        target_ops = self._normalize_operations(target)

        baseline_keys: Set[Tuple[str, str]] = set(baseline_ops.keys())
        target_keys: Set[Tuple[str, str]] = set(target_ops.keys())

        changes: List[DiffChangeRecord] = []
        added_endpoints = 0
        removed_endpoints = 0
        modified_endpoints = 0

        # 1. Removed Endpoints (Present in S1, missing from S2 -> BREAKING)
        removed_keys = sorted(baseline_keys - target_keys)
        for path, method in removed_keys:
            removed_endpoints += 1
            op = baseline_ops[(path, method)]
            op_id = op.get("operationId") or f"{method}_{path}"
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.ENDPOINT_REMOVED,
                    path=path,
                    method=method,
                    is_breaking=True,
                    description=f"Endpoint '{method.upper()} {path}' was removed from the API.",
                    location=f"paths.{path}.{method}",
                    details={
                        "operation_id": op_id,
                        "summary": op.get("summary", ""),
                    },
                )
            )

        # 2. Added Endpoints (Missing from S1, present in S2 -> NON-BREAKING)
        added_keys = sorted(target_keys - baseline_keys)
        for path, method in added_keys:
            added_endpoints += 1
            op = target_ops[(path, method)]
            op_id = op.get("operationId") or f"{method}_{path}"
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.ENDPOINT_ADDED,
                    path=path,
                    method=method,
                    is_breaking=False,
                    description=f"New endpoint '{method.upper()} {path}' was added to the API.",
                    location=f"paths.{path}.{method}",
                    details={
                        "operation_id": op_id,
                        "summary": op.get("summary", ""),
                    },
                )
            )

        # 3. Modified Endpoints (Present in both S1 and S2)
        shared_keys = sorted(baseline_keys & target_keys)
        for path, method in shared_keys:
            b_op = baseline_ops[(path, method)]
            t_op = target_ops[(path, method)]

            endpoint_changes = self._compare_operation(path, method, b_op, t_op)
            if endpoint_changes:
                modified_endpoints += 1
                changes.extend(endpoint_changes)

        # Compute summary
        breaking_count = sum(1 for c in changes if c.is_breaking)
        non_breaking_count = len(changes) - breaking_count

        summary = DiffSummary(
            total_changes=len(changes),
            breaking_changes=breaking_count,
            non_breaking_changes=non_breaking_count,
            added_endpoints=added_endpoints,
            removed_endpoints=removed_endpoints,
            modified_endpoints=modified_endpoints,
        )

        return DiffReport(summary=summary, changes=changes)

    def _compare_operation(
        self,
        path: str,
        method: str,
        b_op: Dict[str, Any],
        t_op: Dict[str, Any],
    ) -> List[DiffChangeRecord]:
        """Deep comparison between two versions of the same operation."""
        changes: List[DiffChangeRecord] = []

        # A. Parameters Comparison
        changes.extend(self._compare_parameters(path, method, b_op, t_op))

        # B. Request Body Comparison
        changes.extend(self._compare_request_body(path, method, b_op, t_op))

        # C. Responses Comparison
        changes.extend(self._compare_responses(path, method, b_op, t_op))

        # D. Deprecation & Metadata
        b_dep = b_op.get("deprecated", False)
        t_dep = t_op.get("deprecated", False)
        if not b_dep and t_dep:
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.METADATA_MODIFIED,
                    path=path,
                    method=method,
                    is_breaking=False,
                    description=f"Endpoint '{method.upper()} {path}' was marked as deprecated.",
                    location=f"paths.{path}.{method}.deprecated",
                    details={"deprecated": True},
                )
            )

        return changes

    def _compare_parameters(
        self,
        path: str,
        method: str,
        b_op: Dict[str, Any],
        t_op: Dict[str, Any],
    ) -> List[DiffChangeRecord]:
        """Compare parameter sets of an operation."""
        changes: List[DiffChangeRecord] = []

        b_params = {
            (p.get("name"), p.get("in", "query")): p
            for p in b_op.get("parameters", [])
            if isinstance(p, dict) and p.get("name")
        }
        t_params = {
            (p.get("name"), p.get("in", "query")): p
            for p in t_op.get("parameters", [])
            if isinstance(p, dict) and p.get("name")
        }

        b_keys = set(b_params.keys())
        t_keys = set(t_params.keys())

        # Removed parameters -> BREAKING if required or path
        for name, loc in sorted(b_keys - t_keys):
            p = b_params[(name, loc)]
            was_required = p.get("required", False) or loc == "path"
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.PARAMETER_REMOVED,
                    path=path,
                    method=method,
                    is_breaking=was_required,
                    description=f"Parameter '{name}' in {loc} was removed.",
                    location=f"paths.{path}.{method}.parameters.{name}",
                    details={"name": name, "in": loc, "was_required": was_required},
                )
            )

        # Added parameters -> BREAKING if required=True
        for name, loc in sorted(t_keys - b_keys):
            p = t_params[(name, loc)]
            is_required = p.get("required", False) or loc == "path"
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.PARAMETER_ADDED,
                    path=path,
                    method=method,
                    is_breaking=is_required,
                    description=(
                        f"New required parameter '{name}' in {loc} was added."
                        if is_required
                        else f"New optional parameter '{name}' in {loc} was added."
                    ),
                    location=f"paths.{path}.{method}.parameters.{name}",
                    details={"name": name, "in": loc, "is_required": is_required},
                )
            )

        # Modified parameters
        for name, loc in sorted(b_keys & t_keys):
            b_p = b_params[(name, loc)]
            t_p = t_params[(name, loc)]

            # Check required change
            b_req = b_p.get("required", False) or loc == "path"
            t_req = t_p.get("required", False) or loc == "path"
            if not b_req and t_req:
                changes.append(
                    DiffChangeRecord(
                        change_type=ChangeType.PARAMETER_MODIFIED,
                        path=path,
                        method=method,
                        is_breaking=True,
                        description=f"Parameter '{name}' in {loc} changed from optional to required.",
                        location=f"paths.{path}.{method}.parameters.{name}.required",
                        details={"name": name, "in": loc, "previous": False, "current": True},
                    )
                )

            # Check type change
            b_type = (b_p.get("schema") or {}).get("type")
            t_type = (t_p.get("schema") or {}).get("type")
            if b_type and t_type and b_type != t_type:
                changes.append(
                    DiffChangeRecord(
                        change_type=ChangeType.PARAMETER_MODIFIED,
                        path=path,
                        method=method,
                        is_breaking=True,
                        description=f"Parameter '{name}' in {loc} changed type from '{b_type}' to '{t_type}'.",
                        location=f"paths.{path}.{method}.parameters.{name}.schema.type",
                        details={"name": name, "in": loc, "previous_type": b_type, "current_type": t_type},
                    )
                )

        return changes

    def _compare_request_body(
        self,
        path: str,
        method: str,
        b_op: Dict[str, Any],
        t_op: Dict[str, Any],
    ) -> List[DiffChangeRecord]:
        """Compare request bodies of an operation."""
        changes: List[DiffChangeRecord] = []

        b_body = b_op.get("requestBody")
        t_body = t_op.get("requestBody")

        if not b_body and t_body:
            is_req = t_body.get("required", False)
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.REQUEST_BODY_MODIFIED,
                    path=path,
                    method=method,
                    is_breaking=is_req,
                    description=(
                        f"Mandatory request body added to '{method.upper()} {path}'."
                        if is_req
                        else f"Optional request body added to '{method.upper()} {path}'."
                    ),
                    location=f"paths.{path}.{method}.requestBody",
                    details={"is_required": is_req},
                )
            )
        elif b_body and not t_body:
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.REQUEST_BODY_MODIFIED,
                    path=path,
                    method=method,
                    is_breaking=False,
                    description=f"Request body removed from '{method.upper()} {path}'.",
                    location=f"paths.{path}.{method}.requestBody",
                )
            )
        elif b_body and t_body:
            b_req = b_body.get("required", False)
            t_req = t_body.get("required", False)
            if not b_req and t_req:
                changes.append(
                    DiffChangeRecord(
                        change_type=ChangeType.REQUEST_BODY_MODIFIED,
                        path=path,
                        method=method,
                        is_breaking=True,
                        description=f"Request body on '{method.upper()} {path}' changed from optional to required.",
                        location=f"paths.{path}.{method}.requestBody.required",
                        details={"previous": False, "current": True},
                    )
                )

        return changes

    def _compare_responses(
        self,
        path: str,
        method: str,
        b_op: Dict[str, Any],
        t_op: Dict[str, Any],
    ) -> List[DiffChangeRecord]:
        """Compare responses status codes of an operation."""
        changes: List[DiffChangeRecord] = []

        b_resps = b_op.get("responses", {})
        t_resps = t_op.get("responses", {})

        b_codes = set(str(k) for k in b_resps.keys()) if isinstance(b_resps, dict) else set()
        t_codes = set(str(k) for k in t_resps.keys()) if isinstance(t_resps, dict) else set()

        # Removed status codes
        for code in sorted(b_codes - t_codes):
            is_breaking = code.startswith("2")  # Removing success response is breaking
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.RESPONSE_CODE_REMOVED,
                    path=path,
                    method=method,
                    is_breaking=is_breaking,
                    description=f"Response status code '{code}' was removed from '{method.upper()} {path}'.",
                    location=f"paths.{path}.{method}.responses.{code}",
                    details={"status_code": code, "is_success_code": is_breaking},
                )
            )

        # Added status codes -> Non-breaking
        for code in sorted(t_codes - b_codes):
            changes.append(
                DiffChangeRecord(
                    change_type=ChangeType.RESPONSE_CODE_ADDED,
                    path=path,
                    method=method,
                    is_breaking=False,
                    description=f"New response status code '{code}' added to '{method.upper()} {path}'.",
                    location=f"paths.{path}.{method}.responses.{code}",
                    details={"status_code": code},
                )
            )

        return changes

