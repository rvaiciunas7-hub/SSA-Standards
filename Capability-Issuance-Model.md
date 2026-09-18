# Capability Issuance Model

## 1. Overview

The Capability Issuance Model defines how governed capabilities are produced from admissible RA‑1 semantic states.  
A capability is a bounded, authoritative permission to perform an action, transition, or operation within a governed system.

Capabilities are not inferred.  
They are deterministically issued only when all admissibility conditions are satisfied.

---

## 2. Capability Definition

A capability consists of:

- capability type  
- scope  
- temporal bounds  
- jurisdictional bounds  
- audience bounds  
- evidence linkage  
- revocation conditions  
- issuance authority  

Capabilities must be:

- deterministic  
- bounded  
- auditable  
- reproducible  
- drift‑free  

---

## 3. Scope Constraints

Capabilities must define their scope explicitly:

### **3.1 Action Scope**
What the capability allows.

### **3.2 Semantic Scope**
Which governed propositions it depends on.

### **3.3 Operational Scope**
Which system components it applies to.

### **3.4 Boundary Scope**
What the capability cannot exceed.

Scope constraints prevent uncontrolled or ambiguous execution.

---

## 4. Temporal, Jurisdictional, and Audience Bounds

Capabilities must include:

### **4.1 Temporal Bounds**
- valid from  
- valid until  
- renewal conditions  

### **4.2 Jurisdictional Bounds**
- geographic or regulatory domain  
- authority of issuance  
- cross‑jurisdiction rules  

### **4.3 Audience Bounds**
- who may use the capability  
- who may not  
- delegation rules  

These bounds ensure capabilities remain governed and context‑appropriate.

---

## 5. Issuance Conditions

A capability may be issued only when:

- RA‑1 state is complete and authoritative  
- admissibility pipeline returns *Admissible*  
- evidence passes all validation gates  
- authority conditions are satisfied  
- scope constraints are respected  
- no suspension triggers are active  

Issuance must be deterministic and reproducible.

---

## 6. Lifecycle

Capabilities follow a governed lifecycle:

1. **Issued**  
   Deterministic creation from admissible state.

2. **Active**  
   Capability may be used within its bounds.

3. **Suspended**  
   Triggered by evidence failure, drift, or authority mismatch.

4. **Revoked**  
   Capability permanently invalidated.

5. **Expired**  
   Temporal bounds reached.

Lifecycle transitions must be deterministic and auditable.

---

## 7. Revocation

Capabilities must define revocation conditions:

- evidence invalidation  
- authority withdrawal  
- boundary violation  
- drift detection  
- jurisdictional change  
- temporal expiry  

Revocation must be:

- deterministic  
- auditable  
- reproducible  

Revoked capabilities cannot be restored without re‑issuance.

---

## 8. Evidence Linkage

Every capability must bind to:

- the evidence set that justified admissibility  
- the governed propositions that define its meaning  
- the authority conditions that enabled issuance  

Evidence linkage ensures capabilities remain trustworthy and verifiable.

