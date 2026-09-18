# Glossary (Working Draft)

## 1. Overview

The SSA Glossary defines authoritative terminology used across all SSA semantic-governance standards.  
It ensures that meaning remains stable, drift‑free, and interoperable across documents, implementations, and jurisdictions.

This glossary is a working draft and will expand as additional SSA standards mature.

---

## 2. Semantic Terms

### **Governed Proposition**  
A meaning-bearing statement encoded into the RA‑1 semantic state.

### **Semantic State**  
The complete governed meaning structure consisting of propositions, dependencies, authoritative conditions, and evidence bindings.

### **Semantic Drift**  
A divergence between encoded meaning and governed meaning. Drift triggers suspension.

### **Dependency Graph**  
A deterministic structure defining how governed propositions rely on one another.

---

## 3. Governance Terms

### **Authoritative Condition**  
A rule that must be satisfied for a semantic state to be considered authoritative.

### **Governed Execution**  
Execution that follows deterministic, drift‑free rules defined by SSA standards.

### **Suspended State**  
A protective state where execution halts due to uncertainty, incomplete evidence, or drift.

### **Invalid State**  
A corrupted or irrecoverable semantic state requiring reconstruction.

---

## 4. Execution Terms

### **Admissibility**  
A deterministic evaluation of whether an action or transition is permitted.

### **Admissibility Pipeline**  
The runtime process that evaluates admissibility using RA‑1 and supporting models.

### **Deterministic Execution**  
Execution that produces identical outcomes from identical semantic states.

### **Capability**  
A bounded, authoritative permission issued after admissibility is confirmed.

---

## 5. Evidence Terms

### **Evidence Item**  
A single unit of evidence with provenance, validation status, and binding target.

### **Evidence Set**  
A collection of evidence items required to validate a governed proposition.

### **Evidence Binding**  
A deterministic link between evidence and governed propositions.

### **Validation Gate**  
A checkpoint determining whether evidence is complete, valid, and reproducible.

---

## 6. Capability Terms

### **Capability Scope**  
The boundaries defining what a capability allows and what it cannot exceed.

### **Temporal Bounds**  
The time period during which a capability is valid.

### **Jurisdictional Bounds**  
The regulatory or geographic domain in which a capability applies.

### **Audience Bounds**  
The set of actors permitted to use a capability.

---

## 7. Cross‑Model Alignment

### **RA‑1**  
The core semantic-governance specification.

### **Runtime Admissibility Model**  
Defines how RA‑1 states are evaluated at runtime.

### **Suspension State Diagram**  
Defines how and when execution must halt.

### **Evidence Schema**  
Defines how evidence is structured and validated.

### **Capability Issuance Model**  
Defines how capabilities are deterministically produced.

