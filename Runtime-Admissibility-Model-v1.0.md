# Runtime Admissibility Evaluation Model v1.0

## 1. Overview

The Runtime Admissibility Evaluation Model defines how a governed semantic state (as specified in RA‑1) is evaluated at runtime to determine whether an action, capability, or state transition is admissible.  
The model ensures that admissibility outcomes are deterministic, reproducible, and fully evidence-backed.

The evaluation model does not interpret meaning.  
It operates strictly on the governed semantic state produced by RA‑1.

---

## 2. Input State Requirements

A runtime evaluation requires a complete and authoritative RA‑1 semantic state, consisting of:

- governed propositions  
- dependency graph  
- authoritative conditions  
- evidence bindings  
- capability constraints (if applicable)

The state must be:

- complete  
- drift‑free  
- validated  
- reproducible  

If any of these conditions fail, the runtime evaluation must suspend (see Suspension State Diagram v1.0).

---

## 3. Admissibility Stages

Runtime admissibility is evaluated through a deterministic pipeline:

1. **State Integrity Check**  
   Ensures the RA‑1 state is complete, validated, and drift‑free.

2. **Dependency Resolution**  
   Resolves all governed propositions in deterministic order.

3. **Authority Verification**  
   Confirms that all authoritative conditions are satisfied.

4. **Evidence Validation**  
   Ensures evidence is complete, valid, and correctly bound.

5. **Capability Boundary Check**  
   Confirms that requested actions fall within governed capability limits.

6. **Outcome Determination**  
   Produces a deterministic admissibility result:
   - *Admissible*  
   - *Not Admissible*  
   - *Suspended*  

---

## 4. Deterministic Execution Rules

The runtime model guarantees:

- identical RA‑1 states always produce identical outcomes  
- no hidden variables or external heuristics  
- no probabilistic interpretation  
- no runtime drift  
- full reproducibility across implementations  

Execution must be:

- deterministic  
- auditable  
- bounded  
- governed  

---

## 5. Capability Output

If admissible, the runtime produces a governed capability output:

- capability type  
- scope  
- temporal bounds  
- jurisdictional bounds  
- audience bounds  
- evidence linkage  
- revocation conditions  

This output is defined by the Capability Issuance Model.

---

## 6. Evidence Integration

Evidence must be:

- complete  
- validated  
- bound to propositions  
- auditable  
- reproducible  

Incomplete or invalid evidence triggers suspension.

Evidence structure is defined in the SSA Evidence Schema.

---

## 7. Failure Modes

The runtime may produce:

- **Not Admissible** — semantic or authority conditions fail  
- **Suspended** — evidence or state integrity fails  
- **Invalid State** — RA‑1 state is incomplete or corrupted  

Suspension and invalid states follow the Suspension State Diagram v1.0.

---

## 8. Reproducibility Requirements

Every admissibility outcome must be:

- reproducible from the same RA‑1 state  
- auditable through evidence  
- explainable through dependency resolution  
- stable across implementations  

This ensures governed meaning behaves consistently across all runtimes.

