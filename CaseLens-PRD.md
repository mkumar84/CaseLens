# CaseLens — Agentic Evidence Triage Copilot
### Product Requirements Document (Portfolio Prototype v1)
**Author:** Mahesh Kumar | **Target Role:** Product Management Lead, AI — Magnet Forensics | **Date:** July 16, 2026

---

## Problem Statement

Digital forensic examiners and DFIR analysts manually sift through massive, heterogeneous case files — device extractions, documents, and communications — to find the artifacts that matter, build a defensible timeline, and write a report that will survive legal scrutiny. This is slow, cognitively taxing, and inconsistent across examiners. The cost of getting it wrong isn't a bad user experience — it's a missed lead, a flawed timeline, or evidence that doesn't hold up in court. Any AI introduced into this workflow has to earn trust at a higher bar than typical enterprise software: every output must be traceable, auditable, and overridable by a human examiner.

CaseLens is a prototype demonstrating how an agentic AI system can accelerate triage and reporting for DFIR work **without** compromising evidentiary integrity — built to show the same trust-first, governance-native product thinking the Magnet Forensics Agentic AI role calls for.

**Architectural stance:** trust gates in CaseLens are enforced at the control-plane level via **agentgateway** (Linux Foundation AAIF), not left to application code alone. Every inter-agent handoff — Triage → Timeline → Report → "case-ready" status — passes through a CEL-based `AgentgatewayPolicy` that can independently block, allow, or require human approval, regardless of what the calling agent claims about its own output. This is the same governance pattern used in the AI & ML Governance Command Centre and the agentgateway insurance-policy build, applied here to DFIR's higher evidentiary bar. The product argument: a unified policy layer that governs *every* agent uniformly is more defensible than N agents each enforcing their own rules — a fragmented control plane is exactly the failure mode DFIR tooling can't afford.

## Goals

1. Demonstrate an end-to-end agentic workflow (triage → timeline → report → audit) that reduces manual review time on a mixed case file
2. Show a working autonomy model: agents suggest and draft, humans approve and can override at every stage
3. Prove every agent output is traceable to a source artifact — zero unsourced claims in generated reports
4. Produce a complete, tamper-evident audit log of every agent decision and human action for legal defensibility
5. Enforce every trust gate (approval-required, citation-completeness, case-ready status) as an **agentgateway CEL policy** at the control-plane level — independent of and unbypassable by individual agent behavior
6. Package this as a portfolio artifact demonstrating agentic product management: architecture, autonomy design, evaluation gates, and governance — mapped explicitly to the Frame-Prove-Earn Loop

## Non-Goals

- **Real evidentiary data or real case integration** — this is a synthetic, illustrative prototype, not a certified forensic tool. Rationale: no access to real case data or Magnet's actual extraction formats; synthetic data proves the workflow pattern without legal/compliance exposure.
- **Court-admissibility certification** — out of scope for a portfolio prototype. Rationale: requires legal review and forensic accreditation beyond a v1 build.
- **Multi-examiner collaboration / case management system** — out of scope. Rationale: this prototype is about the agentic triage-to-report pipeline, not case workflow software.
- **Integration with real forensic tools (Cellebrite, Magnet AXIOM, etc.)** — out of scope for v1. Rationale: no API access; would be a natural "Earn the scale" phase-2 direction.
- **Model fine-tuning** — out of scope. Rationale: prototype uses prompted Claude agents with structured outputs; fine-tuning is a scale investment, not a v1 proof point.

## User Stories

**As a forensic examiner**, I want the system to flag investigatively relevant artifacts from a mixed case file so that I don't have to manually review every document, message, and file.

**As a forensic examiner**, I want to see *why* an artifact was flagged (with a confidence rationale) so that I can quickly judge whether to trust or dismiss it.

**As a forensic examiner**, I want a reconstructed timeline built from flagged artifacts so that I can see the sequence of events without manually cross-referencing timestamps.

**As a forensic examiner**, I want to approve, edit, or reject any agent-flagged artifact or timeline entry before it flows into the report so that I retain full control over what becomes part of the case record.

**As a forensic examiner**, I want a first-draft report generated with inline citations back to source artifacts so that I save drafting time without losing traceability.

**As a case reviewer / supervisor**, I want a complete audit log of every agent action and every human override so that the investigative process is defensible in court.

**As a case reviewer**, I want to see a quality/confidence gate before any report is marked "case-ready" so that I know it has passed a minimum evaluation bar before relying on it.

## Requirements

### Must-Have (P0)
- **Triage Agent**: ingests a synthetic mixed case file (documents + device extraction + comms) and flags relevant artifacts with a rationale and confidence score
  - *Acceptance:* Given a synthetic case file, when the Triage Agent runs, then every flagged artifact has a rationale, confidence score, and source reference; no artifact is flagged without a traceable source
- **Timeline Agent**: reconstructs a chronological event sequence from flagged artifacts only
  - *Acceptance:* Given approved flagged artifacts, when the Timeline Agent runs, then every timeline entry links back to its source artifact and timestamp
- **Report Drafting Agent**: generates a first-pass report with inline citations to approved artifacts only
  - *Acceptance:* Given approved artifacts and timeline, when the Report Agent runs, then every factual claim in the draft cites a specific source artifact; no claim exists without a citation
- **Audit Agent**: logs every agent action, confidence score, and human override with timestamp
  - *Acceptance:* Given any agent or human action, when it occurs, then it is written to an immutable audit log viewable in a Findings & Audit panel
- **Agentgateway control plane**: all inter-agent handoffs are routed through agentgateway; agents cannot call one another directly
  - *Acceptance:* Given the Triage, Timeline, Report, and Audit Agents, when any agent attempts a handoff, then the call is intercepted and evaluated by an `AgentgatewayPolicy` before proceeding
- **Policy: Human-approval gate** (`AgentgatewayPolicy`, CEL): blocks Timeline Agent from consuming any artifact not marked `approved` by a human
  - *Acceptance:* Given a flagged artifact with status `pending` or `rejected`, when the Timeline Agent requests it, then agentgateway denies the request and logs the denial
- **Policy: Citation-completeness gate** (`AgentgatewayPolicy`, CEL): blocks any report from transitioning to `case-ready` status unless citation coverage = 100%
  - *Acceptance:* Given a draft report with citation coverage < 100%, when a status-change request to `case-ready` is made, then agentgateway denies the transition and returns a specific reason (which claims are unsourced)
- **Policy: Audit-completeness gate** (`AgentgatewayPolicy`, CEL): denies any agent action that would not produce a corresponding audit log entry
  - *Acceptance:* Given any agent call routed through agentgateway, when the call completes, then a corresponding audit log entry exists; if logging fails, the action itself is rolled back, not just flagged after the fact
- **Policy enforcement is provably independent of agent behavior**: a deliberately "misbehaving" agent (e.g. one prompted to skip citations) is still blocked at the gateway
  - *Acceptance:* Given a Report Agent variant that omits citations, when it attempts to mark a report `case-ready`, then the gateway still blocks it — demonstrating the gate does not rely on the agent's own compliance

### Nice-to-Have (P1)
- Confidence-based visual flagging (high/medium/low) on triage results
- Ability to re-run Timeline Agent after mid-review artifact edits
- Policy simulation mode: preview what a policy change would have blocked/allowed against historical audit log data
- Exportable audit log (PDF/CSV) for the case file

### Future Considerations (P2)
- Multi-case pattern library (recurring entity/behavior detection across cases)
- Real forensic tool integration (API-based ingestion)
- Multi-examiner review and sign-off workflow

## Success Metrics

**Leading indicators**
- Citation completeness rate: 100% of report claims sourced (hard gate, not just measured)
- Artifact review time: examiner reviews a flagged artifact set in materially less time than raw manual review (illustrative target for demo: 70% reduction on synthetic file)
- Override rate: track how often examiners reject Triage Agent flags (signal for tuning, not a "success" metric alone — a very low override rate could indicate over-trust, which is itself a governance signal worth surfacing)
- Gateway denial rate: count of policy denials at each gate — a non-zero, explainable denial rate is evidence the control plane is doing real work, not rubber-stamping

**Lagging indicators (framed for a real deployment, illustrative here)**
- Reduction in time-to-first-draft-report per case
- Examiner trust/confidence rating in agent-flagged artifacts over time
- Audit log completeness under legal review simulation

## Open Questions

- What does Magnet's actual extraction data schema look like, and how would Triage Agent prompting change to match it? *(engineering/data — not blocking for prototype, relevant for "Earn the scale" narrative in interview)*
- What confidence threshold should trigger mandatory human review vs. optional review? *(product — can set an illustrative default for v1, revisit with real usage data)*
- Should the Audit Agent log be cryptographically tamper-evident (hash chain) even in prototype form, to better demonstrate the trust bar? *(product/engineering — worth doing if time allows, strong signal for this specific role)*
- Should gateway policies be versioned and diffable (so a policy change itself is auditable), or is a single active policy set sufficient for v1? *(product/engineering — versioned policies are a stronger governance story but add build time)*

## Timeline Considerations

- No external deadline; this is a portfolio build. Suggested phasing:
  - **Phase 1 (this PRD → build):** Triage + Timeline Agents, agentgateway routing scaffolded, human-approval policy live
  - **Phase 2:** Report Agent + citation-completeness policy + case-ready gate
  - **Phase 3:** Audit Agent + audit-completeness policy + Findings/Audit panel
  - **Phase 4:** "Misbehaving agent" demo scenario + policy denial log walkthrough for interview narrative
- Target: complete before next round of conversations with Magnet Forensics contacts, so the Frame-Prove-Earn Loop narrative can be shown live rather than described

---

## Frame-Prove-Earn Loop Mapping (for interview narrative)

| Step | Applied to CaseLens |
|---|---|
| **Frame** | The problem is examiner triage time and evidentiary defensibility — not "add AI to forensics." Users are examiners and reviewers; constraint is zero-tolerance for unsourced claims. |
| **Design with intent** | Autonomy is capped at "suggest and draft" — agents never finalize; humans gate every stage. Trust gates are enforced at the agentgateway control-plane level, not left to individual agent compliance — matching actual legal risk, not ambition. |
| **Prove it, don't assume it** | Citation-completeness and human-approval are hard `AgentgatewayPolicy` gates before status changes — demonstrated by showing a deliberately non-compliant agent still get blocked at the gateway. |
| **Earn the scale** | Multi-case pattern library, real tool integration, and versioned/diffable policies are explicitly P2/future — earned only after the single-case pipeline proves out, not pitched as v1. |
