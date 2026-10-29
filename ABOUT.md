SSA Antinomy Conflict Analyzer represents explicitly encoded rule conflicts, retains blocking originals and separate governance records, and exports semantic evidence. A separately invoked adapter performs only a bounded evidence digest; representation, resolution and decision authority remain distinct.

## How it works
- **Conflict representation** — compares 2–100 rules using exact-Context applicability, supplied actor/action, jurisdiction, conditions, exceptions, definitions and inclusive dates. An evidence-anchored obligation/prohibition contradiction with complete metadata is REGULATORY_ANTINOMY; unresolved cases remain POTENTIAL_CONFLICT. NO_CONFLICT is not clearance.
- **Governance** — verifies signed records against a once-pinned subject policy. New distinct-state transitions follow SSA-RM-1 §7.1; initial registration is CREATED or terminal REJECTED only, before lifecycle history. Recorded lifecycle identity remains separate from safety suspension. Material changes preserve MODIFIED while requiring a fresh version-bound evaluation.
- **Explicit execution** — only EVIDENCE_DIGEST_V1 is permitted: SHA-256 of verified canonical evaluation evidence, at most 1 MiB, with empty parameters. A fresh evidenced ADMISSIBLE evaluation, separately signed scoped decision, current approval/ACTIVE and exact original/version/evidence/record/head bindings remain mandatory. Computation and receipt verification precede the append-only Execution Event. No detection, import, decision or conformity result triggers production execution.
- **Conformity** — all 26 frozen mandatory CR-11–CR-15/Annex A tests remain applicable. Independent fixtures cover every lifecycle state and 110 distinct-state transitions. Execution positives perform the actual bounded operation in isolated stores. Regression negatives check wrong roles, missing/stale evidence, changed versions, replay and operation failure, including no event after role failure. Historical reports and governance records remain unchanged.
- **Semantic evidence** — RDFLib exports JSON-LD/Turtle; independent reconstruction and graph isomorphism check the mapped projection. pySHACL uses the SHACL 1.0 Recommendation, without imports, entailment or advanced rules, against a draft local v1.0.0 profile. Magnus Opus A/B and SSA-RM-1 §10 inform the mapping. RA-1 is reference-only, without canonical equivalence or inferred lifecycle/Hold assignments. Original JSON preserves unmapped and missing fields; false and zero remain distinct.

## Authority roles
| Signed record | Explicit required pinned role |
|---|---|
| ADMISSIBILITY_EVALUATION | ADMISSIBILITY_EVALUATION |
| GOVERNANCE_DECISION | GOVERNANCE_DECISION |
| LIFECYCLE_REGISTRATION | GOVERNANCE_DECISION |
| LIFECYCLE_ATTESTATION, including APPROVED and ACTIVE | GOVERNANCE_DECISION |
| CONTROLLED_EXECUTION_REQUEST | EXECUTION_OPERATOR |

These are local technical permissions, not new normative SSA entities. Approval and activation remain attributable §7 governance acts, checked by exact record type and state, never a generic fallback. EXECUTION_OPERATOR alone cannot create evaluations, decisions or lifecycle records; GOVERNANCE_DECISION alone cannot invoke execution. Fixtures use separate single-role keys. Permissions are not inferred: existing pinned policies lacking EXECUTION_OPERATOR remain blocked and are never silently upgraded or replaced.

## Parameters
| Parameter | Default | Meaning / constraint |
|---|---|---|
| Input method; rules | File; fabricated example | Guided forms, JSON file or editor; 2–100 unique rule IDs and exact statements. |
| Evidence bundle | Fabricated example | Documents with source_id, authority, reference and text; replace demo evidence for real assessments. |
| Subject ID; details | Blank | Real assessments need a stable ID; details are versioned. |
| Shared Context | Illustrative narrative | Applicability declarations bind to this exact text, not inferred meaning. |
| Rule metadata | Blank | Supplied authority/reference/source, conditions, exceptions, jurisdiction, effective wording, modality, actor, positive action and definitions. Modalities: obligation/prohibition/permission. Missing fields stay missing. |
| Start/end dates | Blank | Optional inclusive YYYY-MM-DD; effective-period wording is not parsed. |
| Outcome/authority/applicability/pair filters | All; first pair | Display only; exports retain every pair. |
| Semantic target | Latest original | Selects an immutable assessment, not unsaved inputs or substituted current lifecycle; read-only export. |
| Governance case/operation/document source | Latest; refresh; paste | Inspect history or validate JSON trust policy/signed record; file input available. Templates are unsigned. |
| Version/change operation/domain/description/reference | Current; refresh; SUBJECT; blank | External material changes require description and evidence locator; eight domains. |
| Conformity evidence/filters | Local probes; all; first test | Replay needs exact corroborated local capture; filters do not change aggregation. |
| Execution request | Blank | Externally signed, one-use JSON envelope requiring explicit EXECUTION_OPERATOR permission. Private keys stay outside the tool. |
| Operation/parameters | EVIDENCE_DIGEST_V1; empty object | Decision independently signs operation, canonical evidence-array SHA-256 and empty-parameters SHA-256; no other action is accepted. |
| Execution freshness | Request ≤300 s; authority chain ≤3600 s | Fixed fail-closed limits; keys remain valid. Every ledger change requires a fresh request. Each execution decision is consumed once. |

## Outputs and limits
- **Audit evidence** — immutable reports provide test IDs, criteria, locators, hashes, changed-file inventories, role map, regression results and preservation counts. Semantic ZIPs retain RDF, shapes, original JSON, omissions and synthetic examples. Receipts describe actual digest computation, not external enforcement.
- **Authority boundary** — a user-provisioned policy is not independent institutional certification; content hashes do not prove legal truth. Separate permissions do not establish separate human identities. Full CL-3 certification, inherited CL-1/CL-2 conformity, key rotation/revocation infrastructure and certified WORM storage remain outside scope.
- **Execution boundary** — no network, shell, arbitrary paths or destructive operation is available. A process failure after pure computation but before commit may leave an unrecorded computation, never a false success event; no exactly-once external side-effect guarantee is claimed. Automatic execution remains blocked. Synthetic fixtures are illustrative.
