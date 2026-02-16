# Activation Lexicon → Operational Mapping

## Purpose

This document provides a canonical governance mapping between activation-stage symbolic language and concrete operational validators.

The goals are to:

- clarify enforcement semantics;
- reduce authority ambiguity;
- anchor symbolic vocabulary to auditable validation surfaces;
- preserve substrate-first framing;
- prevent doctrine/runtime drift.

This document is governance infrastructure. It does **not** change runtime behavior.

## Scope and Non-Authority Disclaimer

This document:

- defines semantic intent for governance review;
- points to operational anchors and evidence surfaces;
- supports proposal-only review posture.

This document does **not**:

- create new execution pathways;
- modify validator implementations;
- grant operator, agent, or runtime authority;
- override repository policy, validator outputs, or accepted governance contracts.

Normative authority remains with accepted governance artifacts and validator gates in the Sentinel standards/contracts layer.

## Lexicon Mapping

| Activation lexicon term | Governance meaning | Operational anchor | Enforcement surface | Expected audit artifact |
|---|---|---|---|---|
| **Activation** | Transition of a proposal-defined control from draft intent to validator-gated readiness. | Registry entry and associated proposal metadata. | Sentinel validation checks and merge gating policy. | Validation run logs, proposal/PR record, accepted registry state. |
| **Anchor** | Canonical linkage between symbolic term and machine-verifiable control point. | Canonical identifiers and immutable references in governance artifacts. | Contract/schema validation and reference integrity checks. | Artifact digest, schema/contract check output. |
| **Seal** | Evidence that a governance condition was satisfied at a point in time. | Validator result set for a specific artifact/version. | Deterministic validator execution and pass/fail outputs. | Signed or stored validation transcript; CI logs. |
| **Gate** | Mandatory control boundary that must pass before progression. | Required validators listed by policy or checklist. | CI required checks and repository branch protections. | Required-check status history and run identifiers. |
| **Doctrine** | Canonical standards language that implementation must consume. | Sentinel governance docs, standards, and contracts. | Review + validator confirmation against doctrine artifacts. | Merged governance artifact with traceable commit history. |
| **Substrate-first** | Governance definitions precede runtime implementation details. | Sentinel proposal and contract artifacts. | Separation-of-layers review criteria in governance process. | Linked proposal chain showing doctrine-before-runtime sequence. |
| **Drift** | Divergence between symbolic governance language and executable validation behavior. | Periodic comparison of doctrine artifacts and validator outputs. | Drift detection in governance review and validation checklist execution. | Drift review note, remediation PR linkage, updated checklist evidence. |

## Enforcement Semantics

1. Symbolic terms are valid for governance use only when mapped to explicit operational anchors.
2. Operational anchors are enforceable only through declared validator surfaces.
3. Validator outcomes are the authoritative readiness signal for progression through gates.
4. Runtime repositories consume accepted governance outputs; they do not define canonical governance semantics.

## Audit Clarification

For governance review, sufficient evidence should include:

- immutable artifact references (commit SHA, digest, or version tag where applicable);
- validator command and outcome traces;
- clear linkage between lexicon term, anchor, and enforcement surface;
- PR/proposal history showing doctrine-first sequence when runtime changes follow.

## Layering Note

Sentinel is the canonical location for this mapping because it is the standards/contracts/validation doctrine layer.

Runtime systems (for example, CodexVault execution services) should consume these governance definitions and implement against them, without redefining semantic authority.
