"""Deterministic Markdown and self-contained HTML reports for Faber Proof."""

# ruff: noqa: E501 -- report markup remains legible as complete deterministic fragments.

from __future__ import annotations

import html
import re
from collections.abc import Mapping

from faber.canonical_json import canonical_json
from faber.proof_planning import ProofPlanningRequest, ProofPlanningResult
from faber.proof_workflow import LOCAL_ISOLATION_DISCLOSURE, ProofWorkflowResult
from faber.proofs import ProofClaim, ProofEvidence, ProofTemplateSelection
from faber.redaction import default_sensitive_patterns

REPORT_REDACTION = "[redacted report value]"
_EXTRA_SECRET_PATTERNS = (
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b"),
    re.compile(
        r"(?i)\b(?:[a-z][a-z0-9_-]*[_-])?(?:api[_-]?key|authorization|password|secret|token)"
        r"\s*[:=]\s*[^\s,;]{8,}"
    ),
)


def _safe_text(value: object, field_name: str = "value") -> str:
    text = str(value)
    for pattern in default_sensitive_patterns():
        if pattern.matches(field_name, text):
            return REPORT_REDACTION
    if any(pattern.search(text) for pattern in _EXTRA_SECRET_PATTERNS):
        return REPORT_REDACTION
    return text


def _safe_json(value: object, field_name: str = "value") -> str:
    def visit(item: object, name: str) -> object:
        if isinstance(item, Mapping):
            return {str(key): visit(nested, str(key)) for key, nested in item.items()}
        if isinstance(item, tuple | list):
            return [visit(nested, name) for nested in item]
        if isinstance(item, str):
            return _safe_text(item, name)
        return item

    return canonical_json(visit(value, field_name))


def _claim_map(result: ProofPlanningResult) -> dict[str, ProofClaim]:
    return {claim.id: claim for claim in result.plan.claims}


def _first_failed_evidence(workflow: ProofWorkflowResult | None) -> ProofEvidence | None:
    if workflow is None:
        return None
    failed_ids = set(workflow.decision.failed_claim_ids)
    for evidence in workflow.evidence:
        if evidence.claim_id in failed_ids or evidence.status == "failed":
            return evidence
    return None


def _counts(
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
) -> dict[str, int]:
    required = sum(1 for claim in planning.plan.claims if claim.evidence_required)
    if workflow is None:
        return {
            "required": required,
            "passed": 0,
            "failed": 0,
            "missing": 0,
            "uncovered": len(planning.plan.uncovered_claim_ids),
        }
    decision = workflow.decision
    return {
        "required": required,
        "passed": len(decision.passed_claim_ids),
        "failed": len(decision.failed_claim_ids),
        "missing": len(decision.missing_claim_ids),
        "uncovered": len(decision.uncovered_claim_ids),
    }


def _reason(workflow: ProofWorkflowResult | None) -> str:
    if workflow is None:
        return "Planning and catalog validation succeeded; proof obligations were not executed."
    decision = workflow.decision
    if decision.verdict == "pass":
        return "Every required proof obligation has accepted authoritative evidence."
    if decision.verdict == "block":
        return "Authoritative evidence demonstrated that at least one required claim is false."
    return "Evidence is missing, uncertain, contradictory, or otherwise requires human review."


def _verdict_label(workflow: ProofWorkflowResult | None) -> str:
    if workflow is None:
        return "DRY RUN — NO VERDICT"
    return workflow.decision.verdict.replace("_", " ").upper()


def _model_label(planning: ProofPlanningResult) -> str:
    model = planning.model_run.returned_model_id or planning.model_run.requested_model_id
    return f"{_safe_text(model, 'model')} · {planning.model_run.mode.upper()} · ADVISORY"


def _failed_focus(
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
) -> tuple[str | None, str | None]:
    evidence = _first_failed_evidence(workflow)
    if evidence is None:
        return None, None
    claim = _claim_map(planning).get(evidence.claim_id)
    claim_text = claim.statement if claim else evidence.claim_id
    counterexample = evidence.counterexample_summary
    if counterexample is None:
        counterexample = {
            "expected": evidence.expected_summary,
            "observed": evidence.observed_summary,
        }
    return _safe_text(claim_text, "failed_claim"), _safe_json(counterexample, "counterexample")


def _audit_digests(
    request: ProofPlanningRequest,
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
    artifact_digests: Mapping[str, str],
) -> dict[str, str]:
    values = {
        "task contract": request.task_contract_digest,
        "attempt": request.attempt_digest,
        "source diff": request.diff_digest,
        "redacted diff": request.redacted_diff_digest,
        "proof catalog": request.proof_catalog_digest,
        "planning request": request.digest(),
        "structured response": planning.structured_response_digest,
        "proof plan": planning.plan.digest(),
        "model run": planning.model_run.digest(),
    }
    if workflow is not None:
        values.update(
            {
                "evidence set": workflow.decision.digest(),
                "proof decision": workflow.decision.digest(),
                "execution policy": workflow.execution_policy_digest,
                "workspace": workflow.workspace_digest,
            }
        )
    for path, digest in sorted(artifact_digests.items()):
        values[f"artifact {path}"] = digest
    return values


def render_markdown_report(
    *,
    task_title: str,
    request: ProofPlanningRequest,
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
    reproduction_command: str,
    artifact_digests: Mapping[str, str],
) -> str:
    """Render a portable report whose verdict comes only from the decision record."""

    verdict = _verdict_label(workflow)
    counts = _counts(planning, workflow)
    failed_claim, counterexample = _failed_focus(planning, workflow)
    lines = [
        "# Faber Proof",
        "",
        f"## {verdict}",
        "",
        f"**Task:** {_safe_text(task_title, 'task_title')}",
        "",
        f"**Candidate:** `{request.candidate_revision}`",
        "",
        f"**Reason:** {_reason(workflow)}",
        "",
    ]
    if failed_claim is not None:
        lines.extend(
            [
                f"**Failed claim:** {failed_claim}",
                "",
                f"**Counterexample:** `{counterexample}`",
                "",
            ]
        )
    lines.extend(
        [
            f"**Model:** {_model_label(planning)}",
            "",
            (
                "**Coverage:** "
                f"required {counts['required']} · passed {counts['passed']} · "
                f"failed {counts['failed']} · missing {counts['missing']} · "
                f"uncovered {counts['uncovered']}"
            ),
            "",
            "**Reproduce:**",
            "",
            "```text",
            _safe_text(reproduction_command, "reproduction_command"),
            "```",
            "",
            "## Model analysis — ADVISORY",
            "",
            "Model decomposition and rationale identify what to test. They are not proof.",
            "",
        ]
    )
    selection_by_claim: dict[str, list[ProofTemplateSelection]] = {}
    for selection in planning.plan.selections:
        selection_by_claim.setdefault(selection.claim_id, []).append(selection)
    for claim in planning.plan.claims:
        lines.extend(
            [
                f"### {_safe_text(claim.id, 'claim_id')} — {_safe_text(claim.statement, 'statement')}",
                "",
                f"- Severity: `{claim.severity}`",
                f"- Requirements: `{_safe_json(list(claim.requirement_refs), 'requirement_refs')}`",
                f"- Risk: {_safe_text(claim.risk_rationale or 'Not supplied.', 'risk_rationale')}",
            ]
        )
        selections = selection_by_claim.get(claim.id, [])
        if not selections:
            lines.append("- Approved proof selection: none")
        for selection in selections:
            lines.extend(
                [
                    f"- Approved proof selection: `{selection.template_id}@{selection.template_version}`",
                    f"- Parameters: `{_safe_json(selection.parameters, 'parameters')}`",
                    f"- Rationale: {_safe_text(selection.rationale, 'rationale')}",
                ]
            )
        lines.append("")
    if planning.uncertainty_notes:
        lines.extend(["### Uncertainty", ""])
        lines.extend(
            f"- {_safe_text(note, 'uncertainty_note')}" for note in planning.uncertainty_notes
        )
        lines.append("")
    lines.extend(["## Authoritative evidence", ""])
    if workflow is None:
        lines.extend(["No proof obligations were executed in dry-run mode.", ""])
    else:
        for evidence in workflow.evidence:
            evidence_claim = _claim_map(planning).get(evidence.claim_id)
            statement = evidence_claim.statement if evidence_claim else evidence.claim_id
            lines.extend(
                [
                    f"### {evidence.status.upper()} — {_safe_text(statement, 'evidence_claim')}",
                    "",
                    f"- Verifier: `{evidence.verifier_id}@{evidence.verifier_version}`",
                    f"- Expected: `{_safe_json(evidence.expected_summary, 'expected')}`",
                    f"- Observed: `{_safe_json(evidence.observed_summary, 'observed')}`",
                    f"- Counterexample: `{_safe_json(evidence.counterexample_summary, 'counterexample')}`",
                    f"- Reason codes: `{_safe_json(list(evidence.failure_reason_codes), 'reason_codes')}`",
                    f"- Evidence digest: `{evidence.digest()}`",
                    f"- Verifier-run digest: `{evidence.verifier_run_digest}`",
                    f"- Receipt digest: `{evidence.verification_receipt_digest}`",
                    "",
                ]
            )
    lines.extend(
        [
            "## Audit metadata",
            "",
            f"- Prompt version: `{request.prompt_template_version}`",
            f"- Response schema: `{request.response_schema_version}`",
            f"- Replay validation: `{'validated' if planning.model_run.mode == 'replay' else 'not applicable'}`",
            f"- Redaction summary: `{_safe_json(request.redaction_summary, 'redaction_summary')}`",
            f"- Model input tokens: `{planning.model_run.input_tokens}`",
            f"- Model output tokens: `{planning.model_run.output_tokens}`",
            f"- Model latency ms: `{planning.model_run.latency_ms}`",
            "- Model cost: `not reported by the provider record`",
            "",
        ]
    )
    for label, digest in _audit_digests(request, planning, workflow, artifact_digests).items():
        lines.append(f"- {label}: `{digest}`")
    lines.extend(
        [
            "",
            "## Runtime boundary",
            "",
            LOCAL_ISOLATION_DISCLOSURE,
            "",
            "Replay needs no API key, account, network request, or hosted service.",
            "",
        ]
    )
    return "\n".join(lines)


def render_html_report(
    *,
    task_title: str,
    request: ProofPlanningRequest,
    planning: ProofPlanningResult,
    workflow: ProofWorkflowResult | None,
    reproduction_command: str,
    artifact_digests: Mapping[str, str],
) -> str:
    """Render a single-file, script-free report with the decisive evidence first."""

    verdict = _verdict_label(workflow)
    verdict_class = "dry" if workflow is None else workflow.decision.verdict
    counts = _counts(planning, workflow)
    failed_claim, counterexample = _failed_focus(planning, workflow)

    def esc(value: object, field: str = "value") -> str:
        return html.escape(_safe_text(value, field), quote=True)

    focus = ""
    if failed_claim is not None:
        focus = (
            '<section class="counterexample" aria-label="Blocking counterexample">'
            f"<h2>Failed claim</h2><p>{esc(failed_claim, 'failed_claim')}</p>"
            f"<h2>Concrete counterexample</h2><pre>{esc(counterexample, 'counterexample')}</pre>"
            "</section>"
        )
    claims: list[str] = []
    selections_by_claim: dict[str, list[ProofTemplateSelection]] = {}
    for selection in planning.plan.selections:
        selections_by_claim.setdefault(selection.claim_id, []).append(selection)
    for claim in planning.plan.claims:
        selections = selections_by_claim.get(claim.id, [])
        selection_html = "<p>No approved proof selection.</p>"
        if selections:
            rows = "".join(
                "<tr>"
                f"<td><code>{esc(selection.template_id)}@{esc(selection.template_version)}</code></td>"
                f"<td><code>{esc(_safe_json(selection.parameters, 'parameters'))}</code></td>"
                f"<td>{esc(selection.rationale, 'rationale')}</td>"
                "</tr>"
                for selection in selections
            )
            selection_html = (
                "<table><thead><tr><th>Approved template</th><th>Parameters</th>"
                f"<th>Rationale</th></tr></thead><tbody>{rows}</tbody></table>"
            )
        claims.append(
            '<article class="card">'
            f"<h3>{esc(claim.id, 'claim_id')} — {esc(claim.statement, 'statement')}</h3>"
            f"<p><strong>Severity:</strong> {esc(claim.severity)}</p>"
            f"<p><strong>Requirement links:</strong> <code>{esc(_safe_json(list(claim.requirement_refs)))}</code></p>"
            f"<p><strong>Risk:</strong> {esc(claim.risk_rationale or 'Not supplied.', 'risk_rationale')}</p>"
            f"{selection_html}</article>"
        )
    evidence_cards: list[str] = []
    if workflow is None:
        evidence_cards.append('<p class="notice">No obligations were executed in dry-run mode.</p>')
    else:
        claim_by_id = _claim_map(planning)
        for evidence in workflow.evidence:
            evidence_claim = claim_by_id.get(evidence.claim_id)
            statement = evidence_claim.statement if evidence_claim else evidence.claim_id
            evidence_cards.append(
                '<article class="card evidence">'
                f"<h3>{esc(evidence.status.upper())} — {esc(statement, 'evidence_claim')}</h3>"
                '<dl class="facts">'
                f"<dt>Verifier</dt><dd><code>{esc(evidence.verifier_id)}@{esc(evidence.verifier_version)}</code></dd>"
                f"<dt>Expected</dt><dd><code>{esc(_safe_json(evidence.expected_summary, 'expected'))}</code></dd>"
                f"<dt>Observed</dt><dd><code>{esc(_safe_json(evidence.observed_summary, 'observed'))}</code></dd>"
                f"<dt>Counterexample</dt><dd><code>{esc(_safe_json(evidence.counterexample_summary, 'counterexample'))}</code></dd>"
                f"<dt>Reason codes</dt><dd><code>{esc(_safe_json(list(evidence.failure_reason_codes)))}</code></dd>"
                f"<dt>Evidence digest</dt><dd><code>{evidence.digest()}</code></dd>"
                f"<dt>Verifier-run digest</dt><dd><code>{esc(evidence.verifier_run_digest)}</code></dd>"
                f"<dt>Receipt digest</dt><dd><code>{esc(evidence.verification_receipt_digest)}</code></dd>"
                "</dl></article>"
            )
    digest_rows = "".join(
        f"<tr><th>{esc(label)}</th><td><code>{esc(digest)}</code></td></tr>"
        for label, digest in _audit_digests(request, planning, workflow, artifact_digests).items()
    )
    uncertainty = (
        "".join(f"<li>{esc(note, 'uncertainty_note')}</li>" for note in planning.uncertainty_notes)
        or "<li>None recorded.</li>"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Faber Proof — {esc(verdict)}</title>
<style>
:root{{--ink:#172033;--muted:#526078;--paper:#f7f8fb;--card:#fff;--line:#d7dce5;--pass:#126b42;--block:#a3212b;--review:#745300;--dry:#45536b}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1120px;margin:auto;padding:28px}} .hero{{background:var(--card);border:1px solid var(--line);border-top:12px solid var(--dry);padding:26px;border-radius:14px;box-shadow:0 8px 28px #1f293714}}
.hero.pass{{border-top-color:var(--pass)}} .hero.block{{border-top-color:var(--block)}} .hero.human_review{{border-top-color:var(--review)}}
.verdict{{font-size:clamp(2.4rem,8vw,5.8rem);line-height:.95;margin:.15em 0;letter-spacing:-.045em}} .lede{{font-size:1.2rem;max-width:75ch}}
.counterexample{{margin:22px 0;padding:18px 22px;background:#fff1f1;border:3px solid var(--block);border-radius:12px}} .counterexample h2{{font-size:1rem;text-transform:uppercase;letter-spacing:.08em;margin:.2rem 0}} .counterexample p{{font-size:1.25rem;font-weight:700}}
.metrics{{display:grid;grid-template-columns:repeat(5,minmax(95px,1fr));gap:10px;margin:20px 0}} .metric{{border:1px solid var(--line);border-radius:10px;padding:10px;background:#fafbfc}} .metric strong{{display:block;font-size:1.7rem}}
.model{{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:6px 12px;font-weight:700}} pre,code{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;white-space:pre-wrap}} pre{{background:#111827;color:#f9fafb;padding:14px;border-radius:8px}}
h2{{margin-top:2.2rem}} .label{{text-transform:uppercase;letter-spacing:.08em;font-weight:800;color:var(--muted)}} .card{{background:var(--card);border:1px solid var(--line);padding:18px;margin:14px 0;border-radius:10px}} table{{width:100%;border-collapse:collapse;background:var(--card)}} th,td{{border:1px solid var(--line);padding:9px;text-align:left;vertical-align:top}} .facts{{display:grid;grid-template-columns:minmax(150px,220px) 1fr;gap:8px}} .facts dt{{font-weight:700}} .facts dd{{margin:0}} .notice{{padding:18px;background:#fff8dc;border:1px solid #d5bd62}} footer{{margin:40px 0;color:var(--muted);font-size:.92rem}}
@media(max-width:720px){{main{{padding:14px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.facts{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}}main{{max-width:none}}.hero,.card{{box-shadow:none}}}}
</style>
</head>
<body><main>
<section class="hero {verdict_class}" aria-labelledby="verdict">
<div class="label">Faber Proof decision</div>
<h1 class="verdict" id="verdict">{esc(verdict)}</h1>
<p class="lede"><strong>{esc(task_title, "task_title")}</strong><br>{esc(_reason(workflow))}</p>
<p><strong>Candidate:</strong> <code>{request.candidate_revision}</code></p>
{focus}
<div class="metrics" aria-label="Proof obligation counts">
<div class="metric"><strong>{counts["required"]}</strong>required</div><div class="metric"><strong>{counts["passed"]}</strong>passed</div><div class="metric"><strong>{counts["failed"]}</strong>failed</div><div class="metric"><strong>{counts["missing"]}</strong>missing</div><div class="metric"><strong>{counts["uncovered"]}</strong>uncovered</div>
</div>
<p class="model">{esc(_model_label(planning))}</p>
<p><strong>Reproduce:</strong></p><pre>{esc(reproduction_command, "reproduction_command")}</pre>
</section>
<section><h2>Model analysis</h2><p class="label">Advisory — not proof</p><p>The model decomposes risk and selects only repository-approved data templates. Its rationale cannot decide the verdict.</p>{"".join(claims)}<h3>Uncertainty and critic findings</h3><ul>{uncertainty}</ul></section>
<section><h2>Authoritative evidence</h2><p class="label">Receipt-bound verifier outcomes</p>{"".join(evidence_cards)}</section>
<section><h2>Audit metadata</h2><table><tbody>{digest_rows}<tr><th>Prompt version</th><td><code>{esc(request.prompt_template_version)}</code></td></tr><tr><th>Response schema</th><td><code>{esc(request.response_schema_version)}</code></td></tr><tr><th>Replay validation</th><td>{"validated" if planning.model_run.mode == "replay" else "not applicable"}</td></tr><tr><th>Redaction summary</th><td><code>{esc(_safe_json(request.redaction_summary))}</code></td></tr><tr><th>Token usage</th><td>input {esc(planning.model_run.input_tokens)} · output {esc(planning.model_run.output_tokens)}</td></tr><tr><th>Model latency</th><td>{esc(planning.model_run.latency_ms)} ms</td></tr><tr><th>Model cost</th><td>not reported by the provider record</td></tr></tbody></table></section>
<section><h2>Runtime boundary</h2><p>{esc(LOCAL_ISOLATION_DISCLOSURE)}</p><p><strong>No-key replay:</strong> replay needs no API key, account, network request, or hosted service.</p></section>
<footer>Faber Proof · Model analysis is advisory; verifier evidence and deterministic policy are authoritative.</footer>
</main></body></html>
"""
