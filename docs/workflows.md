# Lifecycle Workflows & State Machines
**Ministry of Tribal Affairs | AI-Enabled Scholarship & Fellowship Management System**

---

## 1. Application Lifecycle State Machine

The system enforces strict state transition guards. Illegal state jumps are rejected by `status_transitions.py`.

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Applicant creates draft
    DRAFT --> SUBMITTED : Applicant final submit
    
    state "Verification Subsystem" as Verif {
        SUBMITTED --> UNDER_AI_VERIFICATION : Queue dispatch (Phase 1+)
        SUBMITTED --> UNDER_MANUAL_REVIEW : Direct desk routing
        UNDER_AI_VERIFICATION --> VERIFIED : Passed OCR & rules
        UNDER_AI_VERIFICATION --> DEFICIENT : AI flags discrepancy
        UNDER_AI_VERIFICATION --> UNDER_MANUAL_REVIEW : Edge cases / low confidence
        UNDER_MANUAL_REVIEW --> VERIFIED : Officer approved
        UNDER_MANUAL_REVIEW --> DEFICIENT : Officer flags deficiency
        DEFICIENT --> RESUBMITTED : Applicant uploads fresh doc
        RESUBMITTED --> UNDER_AI_VERIFICATION
        RESUBMITTED --> UNDER_MANUAL_REVIEW
    }

    state "Evaluation & Selection" as Eval {
        VERIFIED --> SHORTLISTED : Scored & threshold passed
        VERIFIED --> MERIT_RANKED : Direct merit indexing
        SHORTLISTED --> MERIT_RANKED : Ranking algorithms applied
        MERIT_RANKED --> SELECTED : Final Committee Approval
        MERIT_RANKED --> WAITLISTED : Secondary pool
        WAITLISTED --> SELECTED : Waitlist vacancy fill
    }

    SELECTED --> FELLOWSHIP_ACTIVE : Direct award / Joining reported
    
    SUBMITTED --> REJECTED : Ineligible
    UNDER_MANUAL_REVIEW --> REJECTED : Fraudulent / Ineligible
    MERIT_RANKED --> REJECTED : Quota exhausted
    WAITLISTED --> REJECTED : Final window closed

    FELLOWSHIP_ACTIVE --> [*]
    REJECTED --> [*]
```

---

## 2. Document Deficiency Resolution Workflow

When a certificate (e.g. Income Certificate expired or ST Certificate mismatch) is flagged:

1. **Detection**:
   - Automated AI/OCR check or Officer manual inspection identifies missing or inconsistent information.
   - Status updated to `FLAGGED` or `RESUBMISSION_REQUIRED`.
2. **Deficiency Notice Generation**:
   - Record created in `deficiencies` table with actionable guidance for the tribal applicant.
   - Application status moved to `DEFICIENT`.
   - In-app notification and SMS/Email notification triggered to applicant.
3. **Applicant Resubmission**:
   - Applicant logs into portal, reviews deficiency note, and uploads updated document.
   - Application status transitions to `RESUBMITTED`.
4. **Re-Verification & Audit**:
   - Re-entered into verification queue.
   - Full event lineage recorded in `audit_logs`.

---

## 3. Post-Selection Fellowship Management Workflow

For candidates transitioning to `FELLOWSHIP_ACTIVE` (e.g. NFST Fellows):

1. **Award Letter Issuance**: Formal digital letter generated with unique award number.
2. **Joining Verification**: University guide / registrar verifies joining date.
3. **Disbursement Tracking**: Integration with DBT (Direct Benefit Transfer) / PFMS.
4. **Annual Renewal Cycle**:
   - Scholar submits `RenewalSubmission` with annual university progress report.
   - Desk officer approves continuation for Year 2, 3, 4, 5.
   - `ProgressReport` archived for compliance.
