"""Independent acceptance comparisons for the frozen CP1 scope key.

Run from the repository root with this repository first on PYTHONPATH.  The default
mode inspects only the explicitly supplied clean candidate tree and retained run
artifacts; ``--instrument-only`` exercises grammar fixtures and makes no qualification
claim.  Instrument fixtures are never chain evidence.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

KEY_RELATIVE = Path("cases/cp1-scope-acceptance/expected.json")
KEY_SHA256 = "1be79cecd12f1727b2e583ef85867a491a4d80a6d5fa0dcb38f6173340f04d53"
NUMERIC_KEY_RELATIVE = Path("cases/cp1-chain/expected.json")
NUMERIC_KEY_SHA256 = "b31b0fc8c3828097087d88873526eaf2d5853d3a8577daf77b3add742e595b2b"
API_NAME = "_verify_financial_scope"
REQUIRED_API_PARAMETERS = {"financial", "provenance", "oracle", "store"}
TARGET_RELATIVE = Path("work/cp1-chain-runtime/audit.py")
DEFAULT_RUNS = (
    Path(
        "artifacts/model-testing/issuer-pdf-20261103/issuer-pdf-sol-medium-tdg-fy2024-20261103-e4240d40c8"
    ),
    Path(
        "artifacts/model-testing/issuer-pdf-20261103/issuer-pdf-sol-medium-tdg-fy2024-20261103-6522e7ec93"
    ),
)
REQUIRED_FINANCIAL_CALLERS = {
    "_actual_period_crosswalk",
    "_audit_profile_maps",
    "_audit_periods",
    "_audit_financial_rows",
    "_audit_delivered_cp1",
    "_cp1_t410_targets",
    "_audit_cp2_causality",
    "_audit_financial_bridge",
}


class VerificationError(ValueError):
    """A key, candidate, retained run, or required comparison is invalid or absent."""


@dataclass(frozen=True)
class Counts:
    required: int
    evaluated: int
    correct: int
    failed: int
    missing: int

    def as_dict(self) -> dict[str, int]:
        return {
            "required": self.required,
            "evaluated": self.evaluated,
            "correct": self.correct,
            "failed": self.failed,
            "missing": self.missing,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_tree(directory: Path) -> str:
    """Hash retained read-only inputs by relative path and bytes; reject links/non-files."""
    if not directory.is_dir() or directory.is_symlink():
        raise VerificationError(f"retained input directory is missing or unsafe: {directory}")
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise VerificationError(f"retained input contains a symbolic link: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise VerificationError(f"retained input contains a non-file entry: {path}")
        relative = path.relative_to(directory).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def load_key(repo: Path) -> tuple[dict[str, Any], str]:
    path = repo / KEY_RELATIVE
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != KEY_SHA256:
        raise VerificationError(f"frozen scope key hash mismatch: {digest}")
    key = json.loads(raw)
    if key.get("schema") != "cp1-scope-acceptance-oracle/1":
        raise VerificationError("unsupported scope key schema")
    return key, digest


def load_numeric_key(repo: Path) -> tuple[dict[str, Any], str]:
    path = repo / NUMERIC_KEY_RELATIVE
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != NUMERIC_KEY_SHA256:
        raise VerificationError(f"unchanged numeric oracle hash mismatch: {digest}")
    return json.loads(raw), digest


def normalize_scope(value: str) -> str:
    """Apply only the key's case/whitespace and one optional final-period rules."""
    if not isinstance(value, str):
        raise VerificationError("scope text must be a string")
    normalized = " ".join(value.split()).casefold()
    if normalized.endswith("."):
        normalized = normalized[:-1].rstrip()
    return normalized


def scope_text_matches(value: str, parent: str, key: dict[str, Any]) -> bool:
    candidate = normalize_scope(value)
    templates = key["accepted_scope_templates"]
    expected = {normalize_scope(template.replace("<parent>", parent)) for template in templates}
    return candidate in expected


def normalize_identity(value: str) -> str:
    """Normalize an authenticated identity with only keyed case/whitespace rules."""
    if not isinstance(value, str):
        raise VerificationError("source identity must be a string")
    return " ".join(value.split()).casefold()


def instrument_cases(
    key: dict[str, Any],
) -> tuple[list[tuple[str, str, bool]], list[tuple[str, str, bool]]]:
    parent = key["source_derived_identity"]["parent_name"]
    first, second = key["accepted_scope_templates"]
    good_texts = [
        first.replace("<parent>", parent),
        second.replace("<parent>", parent),
        first.replace("<parent>", parent).upper(),
        "  ".join(first.replace("<parent>", parent).split()),
        first.replace("<parent>", parent) + ".",
        second.replace("<parent>", parent) + ".",
    ]
    good = [(f"instrument-good-{i + 1}", text, True) for i, text in enumerate(good_texts)]
    bad: list[tuple[str, str, bool]] = []
    for item in key["negative_controls"]:
        text = item.get("example_input")
        if isinstance(text, str):
            bad.append((item["id"], text, False))
        else:
            # Missing-evidence classes have no scope text in the frozen key. The empty
            # instrument value tests only that absent text is not accepted as grammar;
            # it does not simulate their retained-evidence refusal behavior.
            bad.append((f"missing-text-{item['id']}", "", False))
    bad.extend(
        [
            ("multiple-final-periods", first.replace("<parent>", parent) + "..", False),
            (
                "internal-punctuation-mutation",
                first.replace(";", ",").replace("<parent>", parent),
                False,
            ),
            ("inserted-text", first.replace("<parent>", parent) + " extra", False),
            ("deleted-required-clause", parent, False),
            (
                "reordered-clauses",
                second.replace("; ", " | ").replace(";", "; ").replace("<parent>", parent),
                False,
            ),
        ]
    )
    # Some evidence controls have no standalone scope string; they are exercised against
    # actual retained evidence when the candidate API is available.
    return good, bad


def evaluate_instrument_cases(key: dict[str, Any]) -> Counts:
    good, bad = instrument_cases(key)
    all_cases = good + bad
    correct = sum(
        scope_text_matches(text, key["source_derived_identity"]["parent_name"], key) == expect
        for _, text, expect in all_cases
    )
    failed = len(all_cases) - correct
    return Counts(len(all_cases), len(all_cases), correct, failed, 0)


def load_candidate(path: Path) -> ModuleType:
    if not path.is_file() or path.is_symlink():
        raise VerificationError("candidate audit source is missing or not a regular file")
    spec = importlib.util.spec_from_file_location("cp1_candidate_audit", path)
    if spec is None or spec.loader is None:
        raise VerificationError("cannot load explicitly selected candidate audit source")
    candidate_src = str(path.parents[2] / "src")
    if candidate_src not in sys.path:
        sys.path.insert(0, candidate_src)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _has_required_api(module: ModuleType) -> tuple[Any | None, str | None]:
    function = getattr(module, API_NAME, None)
    if not callable(function):
        return None, f"candidate API missing: {API_NAME}"
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError) as error:
        return None, f"candidate API signature unavailable: {type(error).__name__}"
    parameters = signature.parameters
    missing = REQUIRED_API_PARAMETERS - set(parameters)
    if missing:
        return None, f"candidate API lacks required named parameters: {', '.join(sorted(missing))}"
    positional_only = sorted(
        name
        for name in REQUIRED_API_PARAMETERS
        if parameters[name].kind == inspect.Parameter.POSITIONAL_ONLY
    )
    if positional_only:
        return (
            None,
            f"candidate API inputs cannot be passed by required names: {', '.join(positional_only)}",
        )
    if any(
        parameters[name].default is not inspect.Parameter.empty for name in REQUIRED_API_PARAMETERS
    ):
        return None, "candidate API makes required evidence inputs optional"
    return function, None


def _verify_static_callers(source: str) -> list[str]:
    """Verify scope evidence at authentication boundaries and retain safe call paths."""
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

    def enclosing_function(node: ast.AST) -> str | None:
        current = parents.get(node)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return current.name
            current = parents.get(current)
        return None

    def defaults_by_name(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> dict[str, ast.expr | None]:
        positional = (*node.args.posonlyargs, *node.args.args)
        defaults: dict[str, ast.expr | None] = (
            {
                arg.arg: default
                for arg, default in zip(positional[-len(node.args.defaults) :], node.args.defaults)
            }
            if node.args.defaults
            else {}
        )
        defaults.update(
            {arg.arg: default for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults)}
        )
        return defaults

    def mandatory(node: ast.FunctionDef | ast.AsyncFunctionDef, names: set[str]) -> list[str]:
        positional = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        available = {arg.arg for arg in positional}
        defaults = defaults_by_name(node)
        errors: list[str] = []
        for name in sorted(names):
            if name not in available:
                errors.append(f"{node.name} lacks required {name} input")
            elif name in defaults and defaults[name] is not None:
                errors.append(f"{node.name} makes {name} input optional")
        return errors

    def call_bindings(
        call: ast.Call, target: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> dict[str, ast.expr]:
        positional = (*target.args.posonlyargs, *target.args.args)
        bound: dict[str, ast.expr] = {
            parameter.arg: value for parameter, value in zip(positional, call.args)
        }
        bound.update({item.arg: item.value for item in call.keywords if item.arg is not None})
        return bound

    def call_matches(
        call: ast.Call,
        target: ast.FunctionDef | ast.AsyncFunctionDef,
        expected_names: set[str],
    ) -> bool:
        actual = call_bindings(call, target)
        for name in expected_names:
            expression = actual.get(name)
            if not isinstance(expression, ast.Name) or expression.id != name:
                return False
        return True

    def calls_in(node: ast.FunctionDef | ast.AsyncFunctionDef, target_name: str) -> list[ast.Call]:
        return [
            child
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == target_name
            and enclosing_function(child) == node.name
        ]

    errors: list[str] = []
    required_signatures = {
        API_NAME: {"financial", "provenance", "oracle", "store"},
        "_require_verified_financial_scope": {
            "financial",
            "provenance",
            "oracle",
            "store",
            "scope",
        },
        "_verify_perimeter": {"financial", "provenance", "oracle", "store", "scope"},
        "_actual_period_crosswalk": {"financial", "provenance", "oracle", "store", "scope"},
        "_audit_profile_maps": {"financial", "provenance", "oracle", "store", "scope"},
        "_audit_periods": {"financial", "provenance", "oracle", "store", "scope"},
        "_cp1_t410_targets": {"financial", "provenance", "oracle", "store", "scope"},
        "_audit_cp2_causality": {"financial", "provenance", "oracle", "store", "scope"},
        "_audit_financial_bridge": {"financial", "provenance", "oracle", "store", "scope"},
    }
    for name, names in required_signatures.items():
        node = functions.get(name)
        if node is None:
            errors.append(f"required scope boundary missing: {name}")
        else:
            errors.extend(mandatory(node, names))

    required_calls = {
        "_verify_perimeter": {
            "_require_verified_financial_scope": {
                "financial",
                "provenance",
                "oracle",
                "store",
                "scope",
            },
        },
        "_actual_period_crosswalk": {
            "_require_verified_financial_scope": {
                "financial",
                "provenance",
                "oracle",
                "store",
                "scope",
            },
            "_verify_perimeter": {"financial", "provenance", "oracle", "store", "scope"},
        },
        "_audit_profile_maps": {
            "_require_verified_financial_scope": {
                "financial",
                "provenance",
                "oracle",
                "store",
                "scope",
            },
        },
        "_audit_periods": {
            "_actual_period_crosswalk": {"financial", "provenance", "oracle", "store", "scope"},
        },
        "_cp1_t410_targets": {
            "_verify_perimeter": {"financial", "provenance", "oracle", "store", "scope"},
        },
        "_audit_cp2_causality": {
            "_cp1_t410_targets": {"financial", "provenance", "oracle", "store", "scope"},
        },
        "_audit_financial_bridge": {
            "_require_verified_financial_scope": {
                "financial",
                "provenance",
                "oracle",
                "store",
                "scope",
            },
            "_audit_profile_maps": {"financial", "provenance", "oracle", "store", "scope"},
            "_audit_periods": {"financial", "provenance", "oracle", "store", "scope"},
            "_audit_financial_rows": {"financial", "oracle"},
        },
    }
    for caller_name, targets in required_calls.items():
        caller = functions.get(caller_name)
        if caller is None:
            continue
        for target_name, required_names in targets.items():
            target = functions.get(target_name)
            found = calls_in(caller, target_name)
            if target is None or not found:
                errors.append(f"{caller_name} does not enforce through {target_name}")
            elif not any(call_matches(call, target, required_names) for call in found):
                errors.append(f"{caller_name} omits mandatory evidence passing to {target_name}")

    allowed_callers = {
        "_verify_financial_scope": {"audit_run", "_require_verified_financial_scope"},
        "_require_verified_financial_scope": {
            "_verify_perimeter",
            "_actual_period_crosswalk",
            "_audit_profile_maps",
            "_audit_financial_bridge",
        },
        "_verify_perimeter": {"_actual_period_crosswalk", "_cp1_t410_targets"},
        "_actual_period_crosswalk": {"_audit_periods"},
        "_audit_profile_maps": {"_audit_financial_bridge"},
        "_audit_periods": {"_audit_financial_bridge"},
        "_audit_financial_rows": {"_audit_financial_bridge"},
        "_audit_delivered_cp1": {"audit_run"},
        "_cp1_t410_targets": {"_audit_cp2_causality"},
        "_audit_cp2_causality": {"audit_run"},
        "_audit_financial_bridge": {"audit_run"},
    }
    for target_name, callers in allowed_callers.items():
        target = functions.get(target_name)
        if target is None:
            continue
        call_nodes = [
            child
            for child in ast.walk(tree)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == target_name
        ]
        if not call_nodes:
            errors.append(f"required production call missing: {target_name}")
        for call in call_nodes:
            callsite_owner = enclosing_function(call)
            if callsite_owner not in callers:
                errors.append(f"unauthenticated call path to {target_name} from {callsite_owner}")

    audit = functions.get("audit_run")
    scope_mint_calls = calls_in(audit, API_NAME) if audit else []
    verifier_node = functions.get(API_NAME)
    if (
        audit is None
        or verifier_node is None
        or not any(
            call_matches(call, verifier_node, {"financial", "provenance", "oracle", "store"})
            for call in scope_mint_calls
        )
    ):
        errors.append("audit_run does not authenticate the retained financial scope")
    elif audit is not None:
        assignment_names = {
            target.id
            for call in scope_mint_calls
            for parent in [parents.get(call)]
            if isinstance(parent, ast.Assign)
            for target in parent.targets
            if isinstance(target, ast.Name)
        }
        scope_variable = "scope" if "scope" in assignment_names else "verified_scope"
        if scope_variable not in assignment_names:
            errors.append("audit_run discards the verified financial scope witness")
        else:
            for downstream in ("_audit_financial_bridge", "_audit_cp2_causality"):
                target = functions.get(downstream)
                calls = calls_in(audit, downstream)
                if (
                    target is None
                    or not calls
                    or not any(
                        call_matches(
                            call,
                            target,
                            {"financial", "provenance", "oracle", "store", scope_variable},
                        )
                        for call in calls
                    )
                ):
                    errors.append(f"audit_run omits verified scope/provenance at {downstream}")
            delivery_calls = calls_in(audit, "_audit_delivered_cp1")
            if not delivery_calls or not any(
                call.lineno > scope_mint_calls[0].lineno for call in delivery_calls
            ):
                errors.append(
                    "audit_run reaches delivered CP-1 projection before scope authentication"
                )

    return errors


def _static_omission_refused(errors: list[str], caller_name: str) -> bool:
    """Count the negative fixture only when the named caller's omission is detected."""
    prefixes = (
        f"{caller_name} lacks required ",
        f"{caller_name} makes ",
        f"{caller_name} does not enforce through ",
    )
    return any(error.startswith(prefixes) for error in errors)


def _acceptance_controls_pass(counts: Counts, required: int) -> bool:
    return (
        counts.required == required
        and counts.evaluated == required
        and counts.correct == required
        and counts.failed == 0
        and counts.missing == 0
    )


def _current_input_hashes(repo: Path, run_dirs: list[Path]) -> dict[str, Any]:
    hashes: dict[str, Any] = {
        "scope_key": sha256_bytes((repo / KEY_RELATIVE).read_bytes()),
        "numeric_key": sha256_bytes((repo / NUMERIC_KEY_RELATIVE).read_bytes()),
        "instrument": sha256_bytes(Path(__file__).read_bytes()),
    }
    for run_dir in run_dirs:
        try:
            hashes[str(run_dir)] = hash_tree(run_dir)
        except (OSError, VerificationError) as error:
            hashes[str(run_dir)] = f"MISSING_OR_UNSAFE:{type(error).__name__}"
    return hashes


def _read_candidate_snapshot(candidate_path: Path) -> tuple[ModuleType, str, Any]:
    before = sha256_bytes(candidate_path.read_bytes())
    module = load_candidate(candidate_path)
    source = candidate_path.read_text(encoding="utf-8")
    after = sha256_bytes(candidate_path.read_bytes())
    if before != after:
        raise VerificationError("candidate source changed while it was being inspected")
    function, api_error = _has_required_api(module)
    if api_error:
        raise VerificationError(api_error)
    if function is None:
        raise VerificationError("candidate scope verifier is unavailable")
    errors = _verify_static_callers(source)
    if errors:
        raise VerificationError("; ".join(errors))
    return module, after, function


def _make_real_arguments(
    module: ModuleType,
    run_dir: Path,
    repo: Path,
    oracle: dict[str, Any],
    expected_control: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    """Use existing read-only owner/raw replay helpers to load genuine accepted evidence."""
    try:
        meta, model_calls = module.read_run(run_dir)
        store = module.Execution(run_dir / "execution")
        snapshot = store.read()
        if snapshot.run.run_id != meta.run_id:
            raise VerificationError("retained run and execution store identities differ")
        financial_attempts = [
            (attempt, step)
            for attempt in snapshot.attempts
            if attempt.module_id == "CP-1"
            for step in attempt.steps
            if step.step_id == "financials" and step.status == "valid"
        ]
        if len(financial_attempts) != 1:
            raise VerificationError("retained execution lacks one unique valid CP-1 financial step")
        financial_attempt, step = financial_attempts[0]
        submission_dir = store.directory / "owner-run-audit" / "submissions"
        accepted: list[Any] = []
        for path in sorted(submission_dir.iterdir()):
            if path.is_symlink() or not path.is_file():
                raise VerificationError("retained submission archive has a link or non-file entry")
            candidate_submission = module.OwnerSubmission.model_validate_json(path.read_bytes())
            if (
                candidate_submission.content_hash() != path.name
                or candidate_submission.step_sha256 != step.content_hash()
                or candidate_submission.stored_payload_sha256 != step.payload_sha256
                or candidate_submission.step_output_sha256 != step.output_sha256
                or candidate_submission.binding.binding.ticket_id != financial_attempt.ticket_id
                or candidate_submission.binding.binding.attempt != financial_attempt.number
                or candidate_submission.disposition != "valid"
            ):
                continue
            accepted.append(candidate_submission)
        if len(accepted) != 1:
            raise VerificationError(
                "current financial step does not select one unique retained genuine submission"
            )
        submission = accepted[0]
        current_heads = [head for head in snapshot.heads if head.module_id == "CP-1"]
        if len(current_heads) > 1:
            raise VerificationError("retained execution has conflicting current CP-1 heads")
        required_head_match = re.search(
            r"current restricted head ([0-9a-f]{64})",
            str(expected_control.get("retained_evidence", "")),
        )
        if required_head_match and not current_heads:
            raise VerificationError("keyed current CP-1 head is missing")
        if current_heads:
            if financial_attempt.status != "finished":
                raise VerificationError(
                    "current CP-1 head is not backed by the accepted finished financial attempt"
                )
            module._assert_current_financial_submission(submission, store, current_heads[0])
            if required_head_match and current_heads[0].result_sha256 != required_head_match.group(
                1
            ):
                raise VerificationError(
                    "current CP-1 head differs from the independent retained key"
                )
        elif financial_attempt.status not in {"pending", "stopped"}:
            raise VerificationError(
                "headless CP-1 financial source component has an invalid attempt state"
            )
        payload = json.loads(store.payload(submission.stored_payload_sha256))
        financial = payload.get("financial") if isinstance(payload, dict) else None
        if not isinstance(financial, dict):
            raise VerificationError("retained accepted submission lacks its financial review")
        calls = module._owner_calls_for_submission(store, submission)
        maps, raw_replay = module._raw_financial_maps(submission, store, run_dir, model_calls)
        provenance = {
            "submission": submission,
            "maps": maps,
            "calls": calls,
            "source_calls_verified": len(calls),
            "raw_replay": raw_replay,
            "extracted_tables": module._source_tables(store, submission),
            "source_page_hashes": module._source_page_hashes(store, submission),
        }
        binding = submission.binding.binding
        attempts = [
            attempt
            for attempt in snapshot.attempts
            if attempt.ticket_id == binding.ticket_id and attempt.number == binding.attempt
        ]
        if len(attempts) != 1:
            raise VerificationError(
                "retained accepted submission lacks its unique authentic attempt"
            )
        context_steps = [
            step
            for step in attempts[0].steps
            if step.step_id == "source_context" and step.status == "valid"
        ]
        if len(context_steps) != 1:
            raise VerificationError(
                "retained accepted submission lacks its unique valid source-context step"
            )
        context_step = context_steps[0]
        context_model = __import__(
            "deploy_vii.source_context", fromlist=["SourceContextReview"]
        ).SourceContextReview
        binding_model = __import__(
            "deploy_vii.context_binding", fromlist=["FinancialContextBinding"]
        ).FinancialContextBinding
        context_review = context_model.model_validate_json(
            store.payload(context_step.payload_sha256)
        )
        context_binding = binding_model.model_validate_json(json.dumps(payload["binding"]))
        provenance.update(
            {
                "context_review": context_review,
                "context_binding": context_binding,
                "context_step_sha256": context_step.content_hash(),
                "submission_payload_sha256": submission.stored_payload_sha256,
            }
        )
        return financial, provenance, store
    except VerificationError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise VerificationError(
            f"cannot load genuine retained financial evidence ({type(error).__name__})"
        ) from None


def evaluate_retained_positive(
    module: ModuleType,
    verifier: Any,
    repo: Path,
    run_dir: Path,
    expected_control: dict[str, Any],
    oracle: dict[str, Any],
    numeric_oracle: dict[str, Any],
) -> dict[str, Any]:
    financial, provenance, store = _make_real_arguments(
        module, run_dir, repo, oracle, expected_control
    )
    refusal = _require_refusal_type(module)
    try:
        result = verifier(financial=financial, provenance=provenance, oracle=oracle, store=store)
    except refusal as error:
        raise VerificationError(
            f"retained scope positive refused: {run_dir.name} ({type(error).__name__})"
        ) from None
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        raise VerificationError(
            f"retained scope positive failed: {run_dir.name} ({type(error).__name__})"
        ) from None
    except Exception as error:  # noqa: BLE001
        raise VerificationError(
            f"retained scope positive failed: {run_dir.name} ({type(error).__name__}: {error})"
        ) from None
    if result is None:
        raise VerificationError("candidate scope verifier returned no authenticated result")
    if type(result).__name__ != "VerifiedFinancialScope":
        raise VerificationError("candidate did not return the typed VerifiedFinancialScope witness")
    parent = getattr(result, "legal_parent", None)
    expected_parent = oracle["source_derived_identity"]["parent_name"]
    if not isinstance(parent, str) or normalize_identity(parent) != normalize_identity(
        expected_parent
    ):
        raise VerificationError(
            "candidate verified scope did not return the independently derived parent identity"
        )
    books = financial.get("books")
    book_scope = (
        books[0].get("entity_perimeter")
        if isinstance(books, list) and books and isinstance(books[0], dict)
        else None
    )
    if (
        not isinstance(book_scope, str)
        or not isinstance(parent, str)
        or not scope_text_matches(book_scope, parent, oracle)
    ):
        raise VerificationError(
            "candidate verified scope does not contain an exact accepted full-string scope"
        )
    bridge = _evaluate_financial_bridge(
        module, financial, provenance, result, store, numeric_oracle
    )
    t410 = _evaluate_t410_if_available(module, financial, provenance, result, store, numeric_oracle)
    return {"financial_source_bridge": bridge, "t4_10": t410}


def _evaluate_financial_bridge(
    module: ModuleType,
    financial: dict[str, Any],
    provenance: dict[str, Any],
    witness: Any,
    store: Any,
    oracle: dict[str, Any],
) -> dict[str, Any]:
    """Run the existing source/profile/cell bridge against its separate unchanged key."""
    bridge = getattr(module, "_audit_financial_bridge", None)
    if not callable(bridge):
        raise VerificationError("candidate financial source bridge is missing")
    values = {
        "financial": financial,
        "provenance": provenance,
        "oracle": oracle,
        "store": store,
        "scope": witness,
        "verified_scope": witness,
    }
    signature = inspect.signature(bridge)
    kwargs: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if name in values:
            kwargs[name] = values[name]
        elif parameter.default is inspect.Parameter.empty and parameter.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise VerificationError(
                f"financial bridge has an unsupported required parameter: {name}"
            )
    try:
        profile_counts, row_crosswalk, period_crosswalk, census = bridge(**kwargs)
    except module.AuditRefused as error:
        raise VerificationError(
            f"keyed financial source bridge refused ({type(error).__name__})"
        ) from None
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        raise VerificationError(
            f"keyed financial source bridge failed ({type(error).__name__})"
        ) from None
    except Exception as error:  # noqa: BLE001
        raise VerificationError(
            f"keyed financial source bridge failed ({type(error).__name__}: {error})"
        ) from None
    counts = oracle.get("count_summary", {})
    expected_profiles: dict[str, int] = {}
    for row in oracle.get("financial_rows", []):
        statement = row.get("statement")
        if not isinstance(statement, str):
            raise VerificationError("unchanged numeric oracle has a malformed statement row")
        expected_profiles[statement] = expected_profiles.get(statement, 0) + 1
    expected_periods = oracle.get("fiscal_policy", {}).get("periods", {})
    period_count = len(expected_periods.get("BS", [])) + len(expected_periods.get("duration", []))
    if (
        profile_counts != expected_profiles
        or not isinstance(row_crosswalk, dict)
        or len(row_crosswalk) != counts.get("full_rows")
        or not isinstance(period_crosswalk, dict)
        or len(period_crosswalk) != period_count
        or not isinstance(census, dict)
        or census.get("rows") != counts.get("full_rows")
        or census.get("cells") != counts.get("full_cells")
        or census.get("printed_nil_cells") != counts.get("reference_nil_count")
    ):
        raise VerificationError(
            "financial source/profile/cell census differs from unchanged numeric key"
        )
    return {
        "profile_counts": profile_counts,
        "rows": census["rows"],
        "cells": census["cells"],
        "printed_nil_cells": census["printed_nil_cells"],
        "periods": period_count,
    }


def _evaluate_t410_if_available(
    module: ModuleType,
    financial: dict[str, Any],
    provenance: dict[str, Any],
    witness: Any,
    store: Any,
    oracle: dict[str, Any],
) -> dict[str, Any]:
    """Compare actual current T4.10 targets with source-row amounts in the numeric key."""
    heads = [head for head in store.read().heads if head.module_id == "CP-1"]
    if not heads:
        return {"status": "NOT_APPLICABLE_NO_CP1_HEAD", "full_chain_qualification": False}
    if len(heads) != 1:
        raise VerificationError("retained execution has conflicting current CP-1 heads")
    helper = getattr(module, "_cp1_t410_targets", None)
    if not callable(helper):
        raise VerificationError("candidate T4.10 source-target verifier is missing")
    values = {
        "cp1": store.head_module(heads[0]),
        "oracle": oracle,
        "financial": financial,
        "store": store,
        "provenance": provenance,
        "scope": witness,
        "verified_scope": witness,
    }
    kwargs: dict[str, Any] = {}
    for name, parameter in inspect.signature(helper).parameters.items():
        if name in values:
            kwargs[name] = values[name]
        elif parameter.default is inspect.Parameter.empty and parameter.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise VerificationError(f"T4.10 verifier has an unsupported required parameter: {name}")
    try:
        actual = helper(**kwargs)
    except module.AuditRefused as error:
        raise VerificationError(
            f"candidate T4.10 source comparison refused ({type(error).__name__})"
        ) from None
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        raise VerificationError(
            f"candidate T4.10 source comparison failed ({type(error).__name__})"
        ) from None
    except Exception as error:  # noqa: BLE001
        raise VerificationError(
            f"candidate T4.10 source comparison failed ({type(error).__name__}: {error})"
        ) from None
    targets = {
        "revenue": ("IS", "NET SALES", "page:106", "FY2024"),
        "cash_closing": ("BS", "CASH AND CASH EQUIVALENTS", "page:105", "FY2024_END"),
    }
    expected_amounts: dict[str, Any] = {}
    expected_rows: dict[str, dict[str, Any]] = {}
    for metric, (statement, label, locator, period_id) in targets.items():
        matches = [
            row
            for row in oracle.get("financial_rows", [])
            if row.get("statement") == statement
            and " ".join(str(row.get("label", "")).split()).casefold() == label.casefold()
            and row.get("unit") == "USD millions"
            and row.get("amount_position", {}).get("locator") == locator
        ]
        if len(matches) != 1:
            raise VerificationError(f"numeric key does not uniquely identify T4.10 {metric}")
        cells = [cell for cell in matches[0].get("cells", []) if cell.get("period_id") == period_id]
        if len(cells) != 1:
            raise VerificationError(f"numeric key does not uniquely identify T4.10 {metric} period")
        expected_amounts[metric] = Decimal(str(cells[0]["normalized_value"]))
        expected_rows[metric] = matches[0]
    if not isinstance(actual, dict) or set(actual) != set(targets):
        raise VerificationError(
            "candidate T4.10 target set differs from independent source metrics"
        )
    periods = oracle.get("fiscal_policy", {}).get("periods", {}).get("duration", [])
    fy2024 = [period for period in periods if period.get("fiscal_year") == 2024]
    if len(fy2024) != 1:
        raise VerificationError("numeric key lacks a unique FY2024 duration identity")
    books = financial.get("books")
    if not isinstance(books, list) or len(books) != 1 or not isinstance(books[0], dict):
        raise VerificationError("retained financial review lacks its unique keyed book")
    book = books[0]
    perimeter = book.get("entity_perimeter") if isinstance(book, dict) else None
    actual_summary: dict[str, dict[str, Any]] = {}
    for metric, expected_amount in expected_amounts.items():
        fact = actual[metric]
        if (
            getattr(fact, "amount", None) != expected_amount
            or getattr(fact, "status", None) != "known"
            or (getattr(fact, "unit", None), getattr(fact, "currency", None)) != ("MILLIONS", "USD")
            or getattr(fact, "scale", None) != Decimal(1000000)
            or not isinstance(getattr(fact, "period", None), str)
            or fy2024[0]["start_date"] not in fact.period
            or fy2024[0]["end_date"] not in fact.period
            or not isinstance(perimeter, str)
            or not isinstance(getattr(fact, "basis", None), str)
            or perimeter.casefold() not in fact.basis.casefold()
            or getattr(fact, "source_amount", None) is not None
        ):
            raise VerificationError(
                f"candidate T4.10 {metric} differs from keyed value/unit/status"
            )
        allowed_quotes = {
            expected_rows[metric]["amount_position"]["raw_source_line"],
            str(expected_rows[metric].get("reference_label", "")),
        }
        citations = getattr(fact, "citations", ())
        locator = targets[metric][2]
        if not any(
            getattr(citation, "source_id", None)
            == expected_rows[metric].get("amount_position", {}).get("source_id")
            and getattr(citation, "source_sha256", None)
            == expected_rows[metric].get("amount_position", {}).get("source_sha256")
            and getattr(citation, "locator", None) == locator
            and getattr(citation, "quote", None) in allowed_quotes
            for citation in citations
        ):
            raise VerificationError(
                f"candidate T4.10 {metric} citation differs from keyed source row"
            )
        actual_summary[metric] = {
            "amount": str(fact.amount),
            "unit": f"{fact.currency} {fact.unit.lower()}",
            "status": fact.status,
            "period": fact.period,
            "basis": fact.basis,
            "citations": [
                {
                    "source_id": citation.source_id,
                    "source_sha256": citation.source_sha256,
                    "locator": citation.locator,
                    "quote": citation.quote,
                }
                for citation in citations
            ],
        }
    return {
        "status": "PASS",
        "expected_source_amounts": {k: str(v) for k, v in expected_amounts.items()},
        "actual": actual_summary,
    }


def _call_helper_with_evidence(
    helper: Any,
    financial: dict[str, Any],
    provenance: dict[str, Any],
    witness: Any,
    store: Any,
    oracle: dict[str, Any],
) -> Any:
    """Bind an existing private helper by its declared names; never guess positional order."""
    signature = inspect.signature(helper)
    values = {
        "financial": financial,
        "provenance": provenance,
        "oracle": oracle,
        "verified_scope": witness,
        "scope": witness,
        "store": store,
    }
    kwargs: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if name in values:
            kwargs[name] = values[name]
        elif parameter.default is inspect.Parameter.empty and parameter.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise VerificationError(f"scope consumer has an unsupported required parameter: {name}")
    if not {"provenance"} <= kwargs.keys() or not ({"verified_scope", "scope"} & kwargs.keys()):
        raise VerificationError("scope consumer does not require witness and provenance inputs")
    return helper(**kwargs)


def _expect_audit_refusal(module: ModuleType, operation: Any, label: str) -> None:
    refusal = _require_refusal_type(module)
    try:
        operation()
    except refusal:
        return
    except (KeyboardInterrupt, SystemExit):
        raise
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        raise VerificationError(
            f"{label} raised unexpected {type(error).__name__}: {error}"
        ) from None
    except Exception as error:  # noqa: BLE001
        raise VerificationError(
            f"{label} raised unexpected {type(error).__name__}: {error}"
        ) from None
    raise VerificationError(f"{label} was accepted instead of refused")


def _require_refusal_type(module: ModuleType) -> type[Exception]:
    refusal = getattr(module, "AuditRefused", None)
    if not isinstance(refusal, type) or not issubclass(refusal, Exception):
        raise VerificationError(
            "candidate does not expose its documented AuditRefused refusal type"
        )
    return refusal


def _metadata_forgery_checks(
    module: ModuleType,
    verifier: Any,
    repo: Path,
    run_dir: Path,
    expected_control: dict[str, Any],
    oracle: dict[str, Any],
) -> list[tuple[str, bool, str | None]]:
    """Replay the exact retained-metadata forgeries adopted by the controller."""
    financial, provenance, store = _make_real_arguments(
        module, run_dir, repo, oracle, expected_control
    )
    refusal = _require_refusal_type(module)
    try:
        witness = verifier(financial=financial, provenance=provenance, oracle=oracle, store=store)
    except refusal as error:
        raise VerificationError(
            f"metadata forgery baseline positive refused ({type(error).__name__})"
        ) from None
    except Exception as error:  # noqa: BLE001
        raise VerificationError(
            f"metadata forgery baseline positive failed ({type(error).__name__}: {error})"
        ) from None

    bad_step_provenance = _zero_step_hash_provenance(provenance)
    bad_step_consume_provenance = _zero_step_hash_provenance(provenance)
    outcomes: list[tuple[str, bool, str | None]] = []

    def check(case_id: str, label: str, operation: Any) -> None:
        try:
            _expect_audit_refusal(module, operation, label)
        except VerificationError as error:
            outcomes.append((case_id, False, str(error)))
        else:
            outcomes.append((case_id, True, None))

    check(
        "zeroed-step-hash",
        "zeroed OwnerSubmission.step_sha256 forgery",
        lambda: verifier(
            financial=financial, provenance=bad_step_provenance, oracle=oracle, store=store
        ),
    )
    helper = getattr(module, "_require_verified_financial_scope", None)
    if not callable(helper):
        raise VerificationError("candidate scope consumer helper is missing")
    check(
        "zeroed-step-hash-consume",
        "genuine witness with zeroed-step-hash provenance at consume",
        lambda: _call_helper_with_evidence(
            helper, financial, bad_step_consume_provenance, witness, store, oracle
        ),
    )

    original_context = provenance["context_review"]
    original_binding = provenance["context_binding"]
    original_submission_json = provenance["submission"].model_dump(mode="json")
    changed_context_data = original_context.model_dump(mode="python")
    changed_context_data["limitations"] = (
        *original_context.limitations,
        "scope verifier metadata forgery",
    )
    changed_context = type(original_context).model_validate(changed_context_data)
    if changed_context.model_dump(mode="python") != changed_context_data:
        raise VerificationError("context forgery changed fields beyond the appended limitation")
    changed_binding_data = original_binding.model_dump(mode="python")
    changed_binding_data["source_context_review_sha256"] = changed_context.content_hash()
    changed_binding = type(original_binding).model_validate(changed_binding_data)
    if changed_binding.model_dump(mode="python") != changed_binding_data:
        raise VerificationError("binding forgery changed fields beyond the rehashed context review")
    forged_provenance = dict(provenance)
    forged_provenance["context_review"] = changed_context
    forged_provenance["context_binding"] = changed_binding
    forged_consume_provenance = dict(provenance)
    forged_consume_provenance["context_review"] = type(original_context).model_validate(
        changed_context_data
    )
    forged_consume_provenance["context_binding"] = type(original_binding).model_validate(
        changed_binding_data
    )
    for forged in (forged_provenance, forged_consume_provenance):
        if (
            forged["submission"] is not provenance["submission"]
            or forged["submission"].model_dump(mode="json") != original_submission_json
        ):
            raise VerificationError(
                "metadata forgery did not preserve the authentic OwnerSubmission object"
            )
    check(
        "rehashed-context-limitation-mint",
        "rehashed context-limitations binding forgery at mint",
        lambda: verifier(
            financial=financial, provenance=forged_provenance, oracle=oracle, store=store
        ),
    )

    check(
        "rehashed-context-limitation-consume",
        "genuine witness with rehashed forged provenance at consume",
        lambda: _call_helper_with_evidence(
            helper, financial, forged_consume_provenance, witness, store, oracle
        ),
    )
    return outcomes


def _zero_step_hash_provenance(provenance: dict[str, Any]) -> dict[str, Any]:
    forged = dict(provenance)
    forged["submission"] = provenance["submission"].model_copy(update={"step_sha256": "0" * 64})
    if forged["submission"].step_sha256 != "0" * 64:
        raise VerificationError("zero-step-hash mutation was not constructed exactly")
    return forged


def _rehashed_context_mutation(provenance: dict[str, Any], mutate: Any) -> dict[str, Any]:
    """Copy typed retained context, apply one mutation, and rebind its canonical content hash."""
    import copy

    forged = copy.copy(provenance)
    context = provenance["context_review"]
    context_data = context.model_dump(mode="python")
    mutate(context_data)
    forged_context = type(context).model_validate(context_data)
    binding = provenance["context_binding"]
    forged_binding = type(binding).model_validate(
        binding.model_dump(mode="python")
        | {"source_context_review_sha256": forged_context.content_hash()}
    )
    forged["context_review"] = forged_context
    forged["context_binding"] = forged_binding
    return forged


def _negative_control_checks(
    module: ModuleType,
    verifier: Any,
    source: str,
    repo: Path,
    run_dir: Path,
    expected_control: dict[str, Any],
    oracle: dict[str, Any],
    numeric_oracle: dict[str, Any],
    foreign_run_dir: Path,
) -> list[dict[str, Any]]:
    """Exercise every frozen negative evidence class from genuine retained inputs."""
    import copy

    financial, provenance, store = _make_real_arguments(
        module, run_dir, repo, oracle, expected_control
    )
    refusal = _require_refusal_type(module)
    try:
        witness = verifier(financial=financial, provenance=provenance, oracle=oracle, store=store)
    except refusal as error:
        raise VerificationError(
            f"negative matrix baseline positive refused ({type(error).__name__})"
        ) from None
    outcomes: list[dict[str, Any]] = []

    def compare(case_id: str, invoke: Any, label: str | None = None) -> None:
        try:
            invoke()
        except refusal as error:
            outcomes.append(
                {
                    "id": case_id,
                    "label": label,
                    "result": "REFUSED",
                    "refusal": type(error).__name__,
                }
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as error:  # noqa: BLE001
            outcomes.append(
                {
                    "id": case_id,
                    "label": label,
                    "result": "FAILED_UNEXPECTED",
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        else:
            outcomes.append({"id": case_id, "label": label, "result": "ACCEPTED_INVALID_EVIDENCE"})

    controls = {item["id"]: item for item in oracle["negative_controls"]}
    scope_ids = {
        "parent-only",
        "restricted-only",
        "carveout",
        "foreign-parent",
        "negation",
        "extra-text",
        "reordered-keywords",
    }
    for case_id in sorted(scope_ids):
        control = controls[case_id]
        bad_financial = copy.deepcopy(financial)
        bad_financial["books"][0]["entity_perimeter"] = control["example_input"]
        compare(
            case_id,
            lambda bad_financial=bad_financial: verifier(
                financial=bad_financial, provenance=provenance, oracle=oracle, store=store
            ),
        )

    missing_context = dict(provenance)
    missing_context.pop("context_review")
    compare(
        "missing-context",
        lambda: verifier(
            financial=financial, provenance=missing_context, oracle=oracle, store=store
        ),
    )

    conflicting = _rehashed_context_mutation(
        provenance,
        lambda data: data.__setitem__(
            "entities",
            (
                dict(data["entities"][0]) | {"name": "Foreign Parent Incorporated"},
                *data["entities"][1:],
            ),
        ),
    )
    compare(
        "conflicting-context",
        lambda: verifier(financial=financial, provenance=conflicting, oracle=oracle, store=store),
    )

    # Exercise the frozen caller omission rule on a mutated static input. This does not
    # count successful instrument fixtures as candidate evidence; the real source is
    # separately rejected if any required caller lacks mandatory evidence.
    caller = min(REQUIRED_FINANCIAL_CALLERS)
    omission_source = source + f"\ndef {caller}(financial, verified_scope):\n    return financial\n"
    omission_errors = _verify_static_callers(omission_source)
    outcomes.append(
        {
            "id": "binding-omission",
            "result": "REFUSED"
            if _static_omission_refused(omission_errors, caller)
            else "ACCEPTED_INVALID_EVIDENCE",
            "detail": omission_errors,
        }
    )

    citation_missing = _rehashed_context_mutation(
        provenance,
        lambda data: data.__setitem__(
            "entities",
            (dict(data["entities"][0]) | {"citations": ()}, *data["entities"][1:]),
        ),
    )
    compare(
        "citation-missing",
        lambda: verifier(
            financial=financial, provenance=citation_missing, oracle=oracle, store=store
        ),
    )

    def remove_parent_citation(data: dict[str, Any]) -> None:
        citations = []
        for item in data["entities"][0]["citations"]:
            citation = dict(item)
            citation["quote"] = "Subsidiaries and consolidated financial statements"
            citations.append(citation)
        data["entities"] = (
            dict(data["entities"][0]) | {"citations": tuple(citations)},
            *data["entities"][1:],
        )

    irrelevant = _rehashed_context_mutation(provenance, remove_parent_citation)
    compare(
        "citation-irrelevant",
        lambda: verifier(financial=financial, provenance=irrelevant, oracle=oracle, store=store),
    )

    wrong_page = copy.deepcopy(oracle)
    wrong_page["source"]["page_text_sha256"]["105"] = "0" * 64
    compare(
        "wrong-page-hash",
        lambda: verifier(
            financial=financial, provenance=provenance, oracle=wrong_page, store=store
        ),
        "keyed-page-105-hash-mismatch",
    )

    stale_mutations: list[tuple[str, dict[str, Any]]] = []
    stale = dict(provenance)
    stale["context_step_sha256"] = "0" * 64
    stale_mutations.append(("context-step-hash", stale))
    for field in ("stored_payload_sha256", "step_output_sha256"):
        altered = dict(provenance)
        altered["submission"] = provenance["submission"].model_copy(update={field: "0" * 64})
        stale_mutations.append((f"submission-{field}", altered))
    altered_ticket = dict(provenance)
    original_submission = provenance["submission"]
    submission_binding = original_submission.binding
    owner_binding = submission_binding.binding
    changed_owner_binding = type(owner_binding).model_validate(
        owner_binding.model_dump(mode="python") | {"ticket_id": "foreign-ticket"}
    )
    changed_submission_binding = type(submission_binding).model_validate(
        submission_binding.model_dump(mode="python") | {"binding": changed_owner_binding}
    )
    altered_ticket["submission"] = type(original_submission).model_validate(
        original_submission.model_dump(mode="python") | {"binding": changed_submission_binding}
    )
    stale_mutations.append(("submission-ticket", altered_ticket))
    altered_attempt = dict(provenance)
    changed_owner_binding = type(owner_binding).model_validate(
        owner_binding.model_dump(mode="python") | {"attempt": owner_binding.attempt + 1}
    )
    changed_submission_binding = type(submission_binding).model_validate(
        submission_binding.model_dump(mode="python") | {"binding": changed_owner_binding}
    )
    altered_attempt["submission"] = type(original_submission).model_validate(
        original_submission.model_dump(mode="python") | {"binding": changed_submission_binding}
    )
    stale_mutations.append(("submission-attempt", altered_attempt))
    altered_disposition = dict(provenance)
    altered_disposition["submission"] = type(original_submission).model_validate(
        original_submission.model_dump(mode="python") | {"disposition": "refused"}
    )
    stale_mutations.append(("submission-disposition", altered_disposition))
    for stale_label, stale_provenance in stale_mutations:
        compare(
            "stale-linkage",
            lambda stale_provenance=stale_provenance: verifier(
                financial=financial, provenance=stale_provenance, oracle=oracle, store=store
            ),
            stale_label,
        )

    foreign_financial, foreign_provenance, foreign_store = _make_real_arguments(
        module, foreign_run_dir, repo, oracle, oracle["positive_controls"][0]
    )
    scope_consumer = getattr(module, "_require_verified_financial_scope", None)
    if not callable(scope_consumer):
        raise VerificationError("candidate scope consumer helper is missing")
    compare(
        "stale-linkage",
        lambda: verifier(
            financial=financial, provenance=foreign_provenance, oracle=oracle, store=store
        ),
        "foreign-run-context-mix",
    )
    compare(
        "stale-linkage",
        lambda: _call_helper_with_evidence(
            scope_consumer,
            financial,
            foreign_provenance,
            witness,
            store,
            oracle,
        ),
        "genuine-witness-with-foreign-context",
    )
    compare(
        "stale-linkage",
        lambda: _call_helper_with_evidence(
            scope_consumer,
            financial,
            provenance,
            _require_original_witness(
                module, verifier, foreign_financial, foreign_provenance, oracle, foreign_store
            ),
            store,
            oracle,
        ),
        "reused-foreign-genuine-witness",
    )

    guessed_parent = _rehashed_context_mutation(
        provenance,
        lambda data: data.__setitem__(
            "entities",
            (dict(data["entities"][0]) | {"citations": ()}, *data["entities"][1:]),
        ),
    )
    compare(
        "guessed-parent",
        lambda: verifier(
            financial=financial, provenance=guessed_parent, oracle=oracle, store=store
        ),
    )

    wrong_header = copy.deepcopy(oracle)
    wrong_header["source"]["page_text_sha256"].pop("107", None)
    compare(
        "header-disagreement",
        lambda: verifier(
            financial=financial, provenance=provenance, oracle=wrong_header, store=store
        ),
        "missing-authenticated-header-page-107-expectation",
    )

    # Keep the existing numeric key as the sole oracle; all three identity axes must
    # independently refuse when the established bridge is run on changed financials.
    numeric_results: list[dict[str, Any]] = []
    numeric_mutations: list[tuple[str, Any]] = [
        ("period", lambda bad: bad["books"][0]["periods"][0].__setitem__("end_date", "2024-08-31")),
        ("unit", lambda bad: bad["books"][0].__setitem__("unit", "THOUSANDS")),
        (
            "entity",
            lambda bad: bad["books"][0].__setitem__("entity_perimeter", "A different parent"),
        ),
    ]
    bridge = getattr(module, "_audit_financial_bridge", None)
    if not callable(bridge):
        raise VerificationError("candidate financial source bridge is missing")
    bridge_values = {
        "financial": financial,
        "provenance": provenance,
        "oracle": numeric_oracle,
        "store": store,
        "scope": witness,
        "verified_scope": witness,
    }
    bridge_kwargs: dict[str, Any] = {}
    for name, parameter in inspect.signature(bridge).parameters.items():
        if name in bridge_values:
            bridge_kwargs[name] = bridge_values[name]
        elif parameter.default is inspect.Parameter.empty and parameter.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise VerificationError(f"financial bridge requires unsupported parameter {name}")
    for axis, mutate in numeric_mutations:
        bad_financial = copy.deepcopy(financial)
        mutate(bad_financial)
        try:
            bridge(**(bridge_kwargs | {"financial": bad_financial}))
        except refusal as error:
            numeric_results.append(
                {"axis": axis, "result": "REFUSED", "detail": type(error).__name__}
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as error:  # noqa: BLE001
            numeric_results.append(
                {
                    "axis": axis,
                    "result": "FAILED_UNEXPECTED",
                    "detail": f"{type(error).__name__}: {error}",
                }
            )
        else:
            numeric_results.append({"axis": axis, "result": "ACCEPTED_INVALID_FINANCIAL"})
    outcomes.append(
        {
            "id": "wrong-period-unit-entity",
            "result": "REFUSED"
            if all(item["result"] == "REFUSED" for item in numeric_results)
            else "FAILED",
            "subchecks": numeric_results,
        }
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for outcome in outcomes:
        grouped.setdefault(outcome["id"], []).append(outcome)
    controls_result = []
    for item in oracle["negative_controls"]:
        if item["id"] not in grouped:
            continue
        result: dict[str, Any] = {
            "id": item["id"],
            "result": "REFUSED"
            if all(check["result"] == "REFUSED" for check in grouped.get(item["id"], []))
            else "FAILED",
            "subchecks": grouped.get(item["id"], []),
        }
        if item["id"] == "header-disagreement":
            result["coverage_limit"] = (
                "Missing authenticated page-107 expectation is evaluated against unchanged retained page bytes. "
                "A physically altered or differing-parent title-page variant is NOT_EVALUATED for this frozen store; "
                "that parser/profile branch requires a separate independently sourced fixture."
            )
        controls_result.append(result)
    if len(controls_result) != len(oracle["negative_controls"]):
        raise VerificationError("negative matrix did not produce one result per frozen control")
    return controls_result


def _require_original_witness(
    module: ModuleType,
    verifier: Any,
    financial: dict[str, Any],
    provenance: dict[str, Any],
    oracle: dict[str, Any],
    store: Any,
) -> Any:
    """Mint a genuine witness from a separately retained positive for the reuse check."""
    try:
        return verifier(financial=financial, provenance=provenance, oracle=oracle, store=store)
    except _require_refusal_type(module) as error:
        raise VerificationError(
            f"foreign positive prerequisite refused ({type(error).__name__})"
        ) from None


def _full_run_refusal_checks(
    module: ModuleType, repo: Path, run_dirs: list[Path]
) -> tuple[dict[str, Any], bool]:
    """Confirm neither retained stopped run can be upgraded to full-chain status."""
    audit = getattr(module, "audit_run", None)
    refusal = _require_refusal_type(module)
    manifest = json.loads((repo / "work/cp1-chain-runtime/manifest.json").read_bytes())
    oracle_path = repo / manifest["oracle_path"]
    context_path = repo / manifest["context_path"]
    outcomes: list[dict[str, Any]] = []
    before_hashes: dict[str, str] = {}
    for run_dir in run_dirs:
        resolved = run_dir if run_dir.is_absolute() else repo / run_dir
        source_path = resolved.parents[3] / manifest["source_path"]
        if not source_path.is_file() or source_path.is_symlink():
            outcomes.append(
                {"run": str(resolved), "result": "MISSING_SOURCE", "source": str(source_path)}
            )
            continue
        before_hashes[str(source_path)] = sha256_bytes(source_path.read_bytes())
        if not callable(audit):
            outcomes.append({"run": str(resolved), "result": "MISSING_AUDIT_RUN"})
            continue
        try:
            audit(resolved, repo, oracle_path, source_path, context_path)
        except refusal as error:
            outcomes.append(
                {
                    "run": str(resolved),
                    "result": "REFUSED_FULL_CHAIN",
                    "refusal": type(error).__name__,
                    "reason": str(error),
                }
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as error:  # noqa: BLE001
            outcomes.append(
                {
                    "run": str(resolved),
                    "result": "FAILED_UNEXPECTED",
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        else:
            outcomes.append({"run": str(resolved), "result": "ACCEPTED_INVALID_FULL_CHAIN"})
    after_hashes: dict[str, str] = {}
    for source_name in before_hashes:
        source_path = Path(source_name)
        after_hashes[source_name] = sha256_bytes(source_path.read_bytes())
    missing_results = {"MISSING_SOURCE", "MISSING_AUDIT_RUN"}
    evaluated = sum(item["result"] not in missing_results for item in outcomes)
    counts = Counts(
        len(run_dirs),
        evaluated,
        sum(item["result"] == "REFUSED_FULL_CHAIN" for item in outcomes),
        sum(item["result"] not in {"REFUSED_FULL_CHAIN", *missing_results} for item in outcomes),
        len(run_dirs) - evaluated,
    )
    intact = before_hashes == after_hashes
    return (
        {
            "counts": counts.as_dict(),
            "full_chain_qualification": False,
            "source_hashes_before": before_hashes,
            "source_hashes_after": after_hashes,
            "source_inputs_unchanged": intact,
            "runs": outcomes,
        },
        counts.correct == counts.required and intact,
    )


def check_candidate_is_clean(candidate_root: Path, target: Path) -> None:
    import subprocess

    try:
        if target.is_symlink():
            raise VerificationError("candidate audit source must not be a symbolic link")
        candidate_root = candidate_root.resolve()
        target = target.resolve()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", str(target.relative_to(candidate_root))],
            cwd=candidate_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except VerificationError:
        raise
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        raise VerificationError(
            f"cannot establish candidate cleanliness ({type(error).__name__})"
        ) from None
    if status.stdout.strip():
        raise VerificationError(
            "candidate audit source is dirty; acceptance requires a clean candidate"
        )


def run_acceptance(
    repo: Path, candidate_root: Path, run_dirs: list[Path]
) -> tuple[dict[str, Any], int]:
    key, key_hash = load_key(repo)
    numeric_oracle, numeric_key_hash = load_numeric_key(repo)
    required_controls = len(key["positive_controls"]) + len(key["negative_controls"]) + 4
    target = candidate_root / TARGET_RELATIVE
    resolved_runs = [path if path.is_absolute() else repo / path for path in run_dirs]
    run_hashes: dict[str, str] = {}
    for run_path in resolved_runs:
        try:
            run_hashes[str(run_path)] = hash_tree(run_path)
        except (OSError, VerificationError) as error:
            run_hashes[str(run_path)] = f"MISSING_OR_UNSAFE:{type(error).__name__}"
    counts = Counts(required_controls, 0, 0, 0, required_controls)
    report: dict[str, Any] = {
        "schema": "cp1-scope-round4-verifier/1",
        "scope_component_only": True,
        "full_chain_qualification": False,
        "key_sha256": key_hash,
        "candidate_source": str(target),
        "candidate_source_sha256": None,
        "instrument_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "numeric_key_sha256": numeric_key_hash,
        "retained_input_tree_sha256": run_hashes,
        "candidate_status": "BLOCKED",
        "controls": counts.as_dict(),
        "retained_positive_runs": [],
        "instrument_only": evaluate_instrument_cases(key).as_dict(),
        "failures": [],
    }
    if len(run_dirs) != len(key["positive_controls"]):
        report["candidate_status"] = "FAIL/BLOCKED"
        report["failures"].append(
            f"required {len(key['positive_controls'])} retained positive run inputs; received {len(run_dirs)}"
        )
        return report, 1
    try:
        check_candidate_is_clean(candidate_root, target)
        report["candidate_source_sha256"] = sha256_bytes(target.read_bytes())
        module, source_hash, verifier = _read_candidate_snapshot(target)
        if source_hash != report["candidate_source_sha256"]:
            raise VerificationError("candidate audit source changed between hashing and loading")
        report["candidate_source_sha256"] = source_hash
    except VerificationError as error:
        failure = str(error)
        try:
            current_hash = sha256_bytes(target.read_bytes())
            if (
                report["candidate_source_sha256"] is not None
                and current_hash != report["candidate_source_sha256"]
            ):
                failure = "candidate audit source changed while acceptance was starting"
        except OSError:
            pass
        report["candidate_status"] = "FAIL/BLOCKED"
        report["failures"].append(failure)
        return report, 1
    evaluated = correct = 0
    failures: list[str] = []
    for expected, run_dir in zip(key["positive_controls"], run_dirs):
        run_path = run_dir if run_dir.is_absolute() else repo / run_dir
        try:
            positive_result = evaluate_retained_positive(
                module, verifier, repo, run_path, expected, key, numeric_oracle
            )
            evaluated += 1
            correct += 1
            report["retained_positive_runs"].append(
                {
                    "id": expected["id"],
                    "result": "PASS_COMPONENT_ONLY",
                    "run": str(run_path),
                    **positive_result,
                }
            )
        except VerificationError as error:
            evaluated += 1
            failures.append(f"{expected['id']}: {error}")
            report["retained_positive_runs"].append(
                {"id": expected["id"], "result": "FAIL", "run": str(run_path), "reason": str(error)}
            )
    metadata_evaluated = metadata_correct = metadata_failed = 0
    metadata_missing = 4
    if correct == len(key["positive_controls"]):
        try:
            evidence_run = run_dirs[-1] if run_dirs[-1].is_absolute() else repo / run_dirs[-1]
            metadata_outcomes = _metadata_forgery_checks(
                module, verifier, repo, evidence_run, key["positive_controls"][-1], key
            )
            metadata_evaluated = len(metadata_outcomes)
            metadata_correct = sum(outcome[1] for outcome in metadata_outcomes)
            metadata_failed = metadata_evaluated - metadata_correct
            metadata_missing = 4 - metadata_evaluated
            report["metadata_forgery_controls"] = {
                "evaluated": metadata_evaluated,
                "correct": metadata_correct,
                "failed": metadata_failed,
                "missing": metadata_missing,
                "cases": [
                    {"id": case_id, "result": "REFUSED" if passed else "FAIL", "detail": detail}
                    for case_id, passed, detail in metadata_outcomes
                ],
            }
        except VerificationError as error:
            report["metadata_forgery_controls"] = {
                "evaluated": 0,
                "correct": 0,
                "failed": 0,
                "missing": 4,
                "cases": [],
                "blocked_by": str(error),
            }
    else:
        report["metadata_forgery_controls"] = {
            "evaluated": 0,
            "correct": 0,
            "failed": 0,
            "missing": 4,
            "blocked_by": "retained positive prerequisite did not pass",
        }
    negative_outcomes: list[dict[str, Any]] = []
    negative_evaluated = negative_correct = negative_failed = 0
    negative_missing = len(key["negative_controls"])
    if correct == len(key["positive_controls"]):
        try:
            negative_run = run_dirs[-1] if run_dirs[-1].is_absolute() else repo / run_dirs[-1]
            negative_outcomes = _negative_control_checks(
                module,
                verifier,
                target.read_text(encoding="utf-8"),
                repo,
                negative_run,
                key["positive_controls"][-1],
                key,
                numeric_oracle,
                run_dirs[0] if run_dirs[0].is_absolute() else repo / run_dirs[0],
            )
            negative_evaluated = len(negative_outcomes)
            negative_correct = sum(item["result"] == "REFUSED" for item in negative_outcomes)
            negative_failed = negative_evaluated - negative_correct
            negative_missing = len(key["negative_controls"]) - negative_evaluated
        except (OSError, VerificationError) as error:
            report["negative_controls"] = {
                "evaluated": 0,
                "correct": 0,
                "failed": 0,
                "missing": negative_missing,
                "blocked_by": str(error),
                "cases": [],
            }
    else:
        report["negative_controls"] = {
            "evaluated": 0,
            "correct": 0,
            "failed": 0,
            "missing": negative_missing,
            "blocked_by": "retained positive prerequisite did not pass",
            "cases": [],
        }
    if negative_outcomes:
        report["negative_controls"] = {
            "evaluated": negative_evaluated,
            "correct": negative_correct,
            "failed": negative_failed,
            "missing": negative_missing,
            "cases": negative_outcomes,
        }
    full_run_result, full_runs_refused = _full_run_refusal_checks(module, repo, resolved_runs)
    report["full_stopped_run_refusals"] = full_run_result
    if not full_runs_refused:
        failures.append("one or more retained stopped runs did not refuse full-chain qualification")
    missing = negative_missing + metadata_missing
    total_evaluated = evaluated + metadata_evaluated + negative_evaluated
    control_counts = Counts(
        required_controls,
        total_evaluated,
        correct + metadata_correct + negative_correct,
        (evaluated - correct) + metadata_failed + negative_failed,
        missing,
    )
    report["controls"] = control_counts.as_dict()
    if not _acceptance_controls_pass(control_counts, required_controls):
        failures.append("scope acceptance controls contain failed or missing comparisons")
    if sha256_bytes(target.read_bytes()) != report["candidate_source_sha256"]:
        failures.append("candidate audit source changed during retained-evidence comparisons")
    try:
        final_hashes = _current_input_hashes(repo, resolved_runs)
        initial_hashes = {
            "scope_key": report["key_sha256"],
            "numeric_key": report["numeric_key_sha256"],
            "instrument": report["instrument_source_sha256"],
            **run_hashes,
        }
        if final_hashes != initial_hashes:
            failures.append("a key, instrument, or retained run input changed during acceptance")
            report["input_hashes_after"] = final_hashes
    except OSError as error:
        failures.append(f"cannot rehash acceptance inputs ({type(error).__name__})")
    try:
        check_candidate_is_clean(candidate_root, target)
    except VerificationError as error:
        failures.append(f"candidate source became dirty during acceptance: {error}")
    report["candidate_status"] = (
        "PASS_COMPONENT_ONLY"
        if not failures and missing == 0 and full_runs_refused
        else "FAIL/BLOCKED"
    )
    report["failures"].extend(failures)
    return report, 0 if report["candidate_status"] == "PASS_COMPONENT_ONLY" else 1


def run_development_probe(
    repo: Path, candidate_root: Path, run_dirs: list[Path], expected_source_sha256: str
) -> tuple[dict[str, Any], int]:
    """Exercise only the real-positive and zeroed-step-hash probe; never qualify a chain."""
    key, key_hash = load_key(repo)
    target = candidate_root / TARGET_RELATIVE
    if len(run_dirs) != 2:
        raise VerificationError("development probe requires both frozen positive run directories")
    numeric_oracle, numeric_key_hash = load_numeric_key(repo)
    instrument_hash = sha256_bytes(Path(__file__).read_bytes())
    check_candidate_is_clean(candidate_root, target)
    source_hash = sha256_bytes(target.read_bytes())
    if source_hash != expected_source_sha256:
        raise VerificationError(f"development candidate source hash mismatch: {source_hash}")
    module = load_candidate(target)
    verifier, api_error = _has_required_api(module)
    if api_error:
        raise VerificationError(api_error)
    if verifier is None:
        raise VerificationError("candidate scope verifier is unavailable")
    refusal = _require_refusal_type(module)
    run_results: list[dict[str, Any]] = []
    evaluated = correct = failed = 0
    for expected, run_dir in zip(key["positive_controls"], run_dirs):
        resolved = run_dir if run_dir.is_absolute() else repo / run_dir
        entry: dict[str, Any] = {"id": expected["id"], "run": str(resolved)}
        try:
            input_hash = hash_tree(resolved)
            financial, provenance, store = _make_real_arguments(
                module, resolved, repo, key, expected
            )
        except (OSError, VerificationError) as error:
            evaluated += 1
            failed += 1
            entry["known_good"] = f"FAIL:{error}"
            entry["zero_step_sha256_forgery"] = {
                "mint": "MISSING_KNOWN_GOOD_FAILED",
                "consume": "MISSING_KNOWN_GOOD_FAILED",
            }
            run_results.append(entry)
            continue
        entry["input_tree_sha256"] = input_hash
        try:
            witness = verifier(financial=financial, provenance=provenance, oracle=key, store=store)
            if type(witness).__name__ != "VerifiedFinancialScope":
                raise VerificationError(
                    "candidate positive did not return a VerifiedFinancialScope"
                )
            book = financial["books"][0]
            if not scope_text_matches(
                book["entity_perimeter"], key["source_derived_identity"]["parent_name"], key
            ):
                raise VerificationError(
                    "retained positive scope text differs from frozen full-string grammar"
                )
            entry["financial_source_bridge"] = _evaluate_financial_bridge(
                module, financial, provenance, witness, store, numeric_oracle
            )
            entry["t4_10"] = _evaluate_t410_if_available(
                module, financial, provenance, witness, store, numeric_oracle
            )
            evaluated += 1
            correct += 1
            positive_status = "PASS_COMPONENT_ONLY"
        except VerificationError as error:
            evaluated += 1
            failed += 1
            positive_status = f"FAIL:{error}"
        except refusal as error:
            evaluated += 1
            failed += 1
            positive_status = f"FAIL:retained positive refused ({type(error).__name__})"
        except Exception as error:  # noqa: BLE001
            evaluated += 1
            failed += 1
            positive_status = f"FAIL:unexpected {type(error).__name__}: {error}"
        entry["known_good"] = positive_status
        if positive_status == "PASS_COMPONENT_ONLY":
            bad_mint_provenance = _zero_step_hash_provenance(provenance)
            bad_consume_provenance = _zero_step_hash_provenance(provenance)
            evaluated += 1
            try:
                verifier(
                    financial=financial, provenance=bad_mint_provenance, oracle=key, store=store
                )
            except refusal:
                correct += 1
                mint_status = "REFUSED"
            except (KeyboardInterrupt, SystemExit):
                raise
            except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
                failed += 1
                mint_status = f"FAILED_UNEXPECTED:{type(error).__name__}:{error}"
            except Exception as error:  # noqa: BLE001
                failed += 1
                mint_status = f"FAILED_UNEXPECTED:{type(error).__name__}:{error}"
            else:
                failed += 1
                mint_status = "ACCEPTED_INVALID_SUBMISSION"
            evaluated += 1
            helper = getattr(module, "_require_verified_financial_scope", None)
            if not callable(helper):
                failed += 1
                consume_status = "MISSING_CONSUMER_HELPER"
            else:
                try:
                    _call_helper_with_evidence(
                        helper, financial, bad_consume_provenance, witness, store, key
                    )
                except refusal:
                    correct += 1
                    consume_status = "REFUSED"
                except (KeyboardInterrupt, SystemExit):
                    raise
                except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
                    failed += 1
                    consume_status = f"FAILED_UNEXPECTED:{type(error).__name__}:{error}"
                except Exception as error:  # noqa: BLE001
                    failed += 1
                    consume_status = f"FAILED_UNEXPECTED:{type(error).__name__}:{error}"
                else:
                    failed += 1
                    consume_status = "ACCEPTED_FORGED_PROVENANCE"
            entry["zero_step_sha256_forgery"] = {"mint": mint_status, "consume": consume_status}
        else:
            entry["zero_step_sha256_forgery"] = {
                "mint": "MISSING_KNOWN_GOOD_FAILED",
                "consume": "MISSING_KNOWN_GOOD_FAILED",
            }
        run_results.append(entry)
    if sha256_bytes(target.read_bytes()) != source_hash:
        failed += 1
    input_hashes_after = _current_input_hashes(
        repo, [path if path.is_absolute() else repo / path for path in run_dirs]
    )
    input_hashes_before = {
        "scope_key": key_hash,
        "numeric_key": numeric_key_hash,
        "instrument": instrument_hash,
        **{entry["run"]: entry.get("input_tree_sha256", "MISSING") for entry in run_results},
    }
    input_changes = input_hashes_after != input_hashes_before
    if input_changes:
        failed += 1
    try:
        check_candidate_is_clean(candidate_root, target)
    except VerificationError:
        failed += 1
    required = 6
    missing = required - evaluated
    report = {
        "schema": "cp1-scope-round4-development-probe/1",
        "candidate_status": "DEVELOPMENT_UNQUALIFIED",
        "scope_component_only": True,
        "full_chain_qualification": False,
        "candidate_source": str(target),
        "candidate_source_sha256": source_hash,
        "key_sha256": key_hash,
        "numeric_key_sha256": numeric_key_hash,
        "instrument_source_sha256": instrument_hash,
        "input_hashes_after": input_hashes_after,
        "input_hashes_changed": input_changes,
        "comparisons": Counts(required, evaluated, correct, failed, missing).as_dict(),
        "runs": run_results,
        "note": "This diagnostic is explicitly unqualified and cannot admit, pass, or qualify a candidate.",
    }
    return report, 0 if failed == 0 and missing == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path.cwd(), help="repository containing the frozen key"
    )
    parser.add_argument(
        "--candidate-root", type=Path, default=Path.cwd(), help="clean candidate source tree"
    )
    parser.add_argument(
        "--run",
        type=Path,
        action="append",
        help="retained genuine run directory; give one per positive control",
    )
    parser.add_argument(
        "--instrument-only",
        action="store_true",
        help="run grammar fixtures only; never qualifies a chain",
    )
    parser.add_argument(
        "--development-probe",
        action="store_true",
        help="run explicitly unqualified positive/zero-step-hash diagnostics",
    )
    parser.add_argument(
        "--expected-candidate-sha256", help="required exact source hash for --development-probe"
    )
    args = parser.parse_args(argv)
    try:
        key, key_hash = load_key(args.repo)
        instrument = evaluate_instrument_cases(key)
        if args.instrument_only:
            output = {
                "schema": "cp1-scope-round4-verifier/1",
                "candidate_status": "INSTRUMENT_ONLY",
                "scope_component_only": True,
                "full_chain_qualification": False,
                "key_sha256": key_hash,
                "instrument_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
                "instrument_only": instrument.as_dict(),
                "note": "Instrument fixtures are not chain evidence and do not qualify a retained run.",
            }
            code = 0 if instrument.failed == 0 else 1
        elif args.development_probe:
            if not args.expected_candidate_sha256:
                raise VerificationError("--development-probe requires --expected-candidate-sha256")
            runs = args.run or [args.repo / path for path in DEFAULT_RUNS]
            output, code = run_development_probe(
                args.repo, args.candidate_root, runs, args.expected_candidate_sha256
            )
        else:
            runs = args.run or [args.repo / path for path in DEFAULT_RUNS]
            output, code = run_acceptance(args.repo, args.candidate_root, runs)
        print(json.dumps(output, sort_keys=True, indent=2))
        return code
    except (OSError, json.JSONDecodeError, VerificationError) as error:
        print(
            json.dumps({"candidate_status": "FAIL/BLOCKED", "failure": str(error)}, sort_keys=True)
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
