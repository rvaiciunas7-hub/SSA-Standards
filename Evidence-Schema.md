# Evidence Schema

## 1. Overview

The Evidence Schema defines how evidence is structured, validated, bound, and audited within SSA-governed semantic states.  
Evidence is not optional: it is a mandatory component of deterministic admissibility and capability issuance.

The schema ensures that evidence is:

- complete  
- validated  
- bound to governed propositions  
- auditable  
- reproducible  
- drift‑free  

Evidence is the backbone of trust in governed execution.

---

## 2. Evidence Primitives

Evidence is composed of the following primitives:

### **2.1 Evidence Item**
A single unit of evidence containing:
- value  
- provenance  
- validation status  
- binding target  
- timestamp  

### **2.2 Evidence Set**
A collection of evidence items required to validate a governed proposition.

### **2.3 Evidence Binding**
A deterministic link between:
- a governed proposition  
- its supporting evidence items  
- validation results  

### **2.4 Evidence Gate**
A validation checkpoint that determines whether evidence is:
- complete  
- valid  
- correctly bound  
- reproducible  

---

## 3. Provenance Structure

Each evidence item must include:

- origin  
- method of acquisition  
- authority of source  
- timestamp  
- integrity checksum  
- reproducibility conditions  

Provenance ensures that evidence can be trusted across systems and jurisdictions.

---

## 4. Validation Gates

Evidence must pass the following gates:

### **4.1 Completeness Gate**
All required evidence items must be present.

### **4.2 Integrity Gate**
Evidence must be unaltered and verifiable.

### **4.3 Provenance Gate**
Source must be authoritative and traceable.

### **4.4 Binding Gate**
Evidence must be correctly linked to governed propositions.

### **4.5 Reproducibility Gate**
Evidence must produce identical validation results across implementations.

Failure at any gate triggers suspension.

---

## 5. Completeness Rules

Evidence is complete when:

- all required items exist  
- all items pass validation  
- all bindings are correct  
- no contradictory evidence exists  
- provenance is fully traceable  

Incomplete evidence → **Suspended State**  
Contradictory evidence → **Invalid State**

---

## 6. Auditability

Evidence must be fully auditable:

- every item traceable  
- every validation step reproducible  
- every binding deterministic  
- every provenance chain intact  

Auditability ensures governed execution can be externally verified.

---

## 7. Integration with RA‑1

Evidence integrates with RA‑1 through:

- governed propositions  
- authoritative conditions  
- dependency resolution  
- capability issuance  
- admissibility evaluation  

Evidence is not an external layer — it is a core component of governed meaning.

