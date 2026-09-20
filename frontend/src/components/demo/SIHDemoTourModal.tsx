import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  X,
  FileText,
  Users,
  Zap,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { authService } from '../../services/authService';

interface TourStep {
  stepNumber: number;
  title: string;
  phaseBadge: string;
  role: 'ADMIN' | 'APPLICANT' | 'OFFICER' | 'COMMITTEE';
  targetRoute: string;
  dossierRef: string;
  personaName: string;
  headline: string;
  narrative: string;
  jurySpeakingPoint: string;
  technicalHighlight: string;
  actionButtonText: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    stepNumber: 1,
    title: 'Declarative Scheme Engine & Dynamic Rules',
    phaseBadge: 'Phase 1 Scheme Architecture',
    role: 'ADMIN',
    targetRoute: '/',
    dossierRef: 'DEMO-NFST & DEMO-NOS',
    personaName: 'Ministry Administrator (admin@demo.gov.in)',
    headline: 'Multi-versioned schemes configured via declarative JSON rules without code deploys.',
    narrative:
      'The National Fellowship for ST Students (DEMO-NFST) defines strict income ceilings (<= 6.0 LPA), minimum academic cutoffs (55%), and required document verification rules. When guidelines evolve, new versions (v1.1) coexist alongside immutable locked versions without disrupting active scholar cohorts.',
    jurySpeakingPoint:
      '"Our declarative rules engine eliminates hardcoded business logic. Ministry officials can update eligibility parameters with version-locked immutability, ensuring zero retroactive disruption to ongoing cohorts."',
    technicalHighlight: 'Version-locked SchemeVersion entities, declarative operator evaluation (equals, in, gte, lte).',
    actionButtonText: 'Switch to Admin & Explore Schemes',
  },
  {
    stepNumber: 2,
    title: 'Scholar Self-Service & Intelligent Pre-Screening',
    phaseBadge: 'Phase 2 Application Portal',
    role: 'APPLICANT',
    targetRoute: '/applicant/dashboard',
    dossierRef: 'DEMO-APP-2026-002',
    personaName: 'Rahul Munda, M.Tech Metallurgical Eng (NIT Jamshedpur)',
    headline: 'Real-time client-side eligibility self-check prevents ineligible submissions.',
    narrative:
      'Tribal scholars experience a transparent application workflow. The portal validates qualifications, checks income certificates, and enforces 5 MB document constraints with automated MIME detection before entering the processing queue.',
    jurySpeakingPoint:
      '"Tribal applicants immediately discover why they qualify or what certificates are missing through our instant self-check pre-screener, reducing rejected applications by over 60%."',
    technicalHighlight: 'Client-side rules execution preview matching backend validation constraints.',
    actionButtonText: 'Switch to Rahul Munda & View Portal',
  },
  {
    stepNumber: 3,
    title: 'AI/OCR Document Verification & Confidence Badges',
    phaseBadge: 'Phase 3 Automated Verification',
    role: 'OFFICER',
    targetRoute: '/officer/dashboard',
    dossierRef: 'DEMO-APP-2026-002',
    personaName: 'Verification Officer (officer@demo.gov.in)',
    headline: 'Deterministic OCR extraction with 98% field-level confidence matching.',
    narrative:
      'Rahul Munda’s Jharkhand State Caste Certificate was scanned and processed by the OCR pipeline. Candidate name, community (ST - Munda), and issuing authority were extracted and cross-referenced with application form fields with high confidence.',
    jurySpeakingPoint:
      '"Instead of manual paperwork, officers review side-by-side comparisons where AI highlights matching entities and flags potential forgery, drastically accelerating file turnaround."',
    technicalHighlight: 'Standalone OCR pipeline with field-level confidence scores and structured flags.',
    actionButtonText: 'Switch to Officer & Open OCR Desk',
  },
  {
    stepNumber: 4,
    title: 'Human Officer Scrutiny & Discrepancy Desk',
    phaseBadge: 'Phase 4 Human-in-the-Loop',
    role: 'OFFICER',
    targetRoute: '/officer/dashboard',
    dossierRef: 'DEMO-APP-2026-003',
    personaName: 'Priya Marandi, M.A. Anthropology (Visva-Bharati)',
    headline: 'Human-in-the-loop oversight with full audit trail for flagged discrepancies.',
    narrative:
      'Priya Marandi’s application reported Rs 2,50,000 annual income, but the OCR extracted Rs 4,50,000 from the revenue document. The discrepancy was automatically flagged for officer scrutiny, allowing an officer to verify, remark, or override with justification.',
    jurySpeakingPoint:
      '"AI never makes unilateral rejection decisions in our system. Any detected anomaly triggers a human officer discrepancy queue with mandatory reason logging and tamper-proof audit trails."',
    technicalHighlight: 'DocumentVerification flags JSONB array, officer_decision state, ai_override audit logging.',
    actionButtonText: 'Switch to Officer & Inspect Flagged Dossier',
  },
  {
    stepNumber: 5,
    title: 'Deficiency Management & Replacement Lineage',
    phaseBadge: 'Phase 5 Deficiency Resolution',
    role: 'APPLICANT',
    targetRoute: '/applicant/dashboard',
    dossierRef: 'DEMO-APP-2026-004',
    personaName: 'Amit Oraon, M.Sc. Physics (Central Univ of Jharkhand)',
    headline: 'Document illegibility flagged with 14-day cure window and immutable version lineage.',
    narrative:
      'Amit Oraon’s semester 4 marksheet was flagged as blurred. Instead of outright rejection, the system issued an automated deficiency notice with actionable guidance, allowing upload of version 2 while preserving version 1 for audit compliance.',
    jurySpeakingPoint:
      '"We replaced bureaucratic rejection with a compassionate 14-day deficiency cure cycle. Scholars upload replacement documents while the historical document tree remains fully traceable."',
    technicalHighlight: 'Deficiency cycle counter, parent_document_id and superseded_by_id foreign-key pointers.',
    actionButtonText: 'Switch to Amit Oraon & View Deficiency',
  },
  {
    stepNumber: 6,
    title: 'Double-Blind Committee Merit Scoring',
    phaseBadge: 'Phase 6 Committee Scoring',
    role: 'COMMITTEE',
    targetRoute: '/committee/batch',
    dossierRef: 'DEMO-APP-2026-005',
    personaName: 'National Selection Committee Member (committee@demo.gov.in)',
    headline: 'Anonymized scoring queue protects against bias in national fellowship awards.',
    narrative:
      'Pooja Santhal’s application is presented in the committee queue with applicant PII stripped. Evaluators score research proposals and academic merit strictly against standardized rubric matrices.',
    jurySpeakingPoint:
      '"Our double-blind committee desk ensures absolute objectivity. Committee members evaluate academic merit without visibility into candidate names, gender, or state quotas until scoring is locked."',
    technicalHighlight: 'PII redaction middleware, multi-criterion weighted scoring formulas, batch locks.',
    actionButtonText: 'Switch to Committee & Score Batch',
  },
  {
    stepNumber: 7,
    title: 'Merit List Finalization & Selection Quota Matrix',
    phaseBadge: 'Phase 6 Merit Selection',
    role: 'ADMIN',
    targetRoute: '/admin/analytics',
    dossierRef: 'DEMO-APP-2026-006',
    personaName: 'Vikram Gond, Merit Rank #1 (Score: 92.5)',
    headline: 'Deterministic ranking calculation with quota slot fulfillment and committee sign-off.',
    narrative:
      'The SIH 2026 evaluation batch DEMO-SIH-BATCH-2026 completed evaluation. Vikram Gond achieved top rank with an aggregate score of 92.5 (Academic: 48.5, Category: 19.0, Financial: 15.0, Interview: 10.0), locking the selection roster.',
    jurySpeakingPoint:
      '"Once committee scoring completes, our ranking engine applies quota rules deterministically and seals the batch. No unauthorized edits can occur post-finalization."',
    technicalHighlight: 'SelectionResult records linked to finalized CommitteeEvaluationBatch.',
    actionButtonText: 'Switch to Admin & View Selection Results',
  },
  {
    stepNumber: 8,
    title: 'Fellowship Sanction & 1-Click DBT Dispatch',
    phaseBadge: 'Phase 8 Post-Selection & DBT',
    role: 'ADMIN',
    targetRoute: '/admin/disbursements',
    dossierRef: 'DEMO-APP-2026-008 & DEMO-APP-2026-007',
    personaName: 'Ministry Administrator / Finance Desk',
    headline: '5-year fellowship tenure, annual progress validation, and simulated DBT transfers.',
    narrative:
      'Dr. Ananya Bodo (IIT Guwahati) has Year 1 fellowship disbursement settled (Rs 3,82,000, UTR: DEMO-PFMS-UTR-20260901). Rajeshwar Bhil (MLSU Udaipur) is in APPROVED_FOR_PAYMENT status, ready for live 1-click mock payment dispatch by the jury!',
    jurySpeakingPoint:
      '"We manage the entire post-award lifecycle. Annual renewal, progress reports, and Direct Benefit Transfer (DBT) payments are executed with row-locking idempotency and immutable financial ledgers."',
    technicalHighlight: 'FellowshipRecord 5-year tenure tracking, row-level locking, payment idempotency keys.',
    actionButtonText: 'Switch to Admin & Execute Live DBT',
  },
];

interface SIHDemoTourModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SIHDemoTourModal: React.FC<SIHDemoTourModalProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'tour' | 'pitch' | 'dossiers'>('tour');
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isSwitchingRole, setIsSwitchingRole] = useState<boolean>(false);
  const [switchFeedback, setSwitchFeedback] = useState<string | null>(null);

  if (!isOpen) return null;

  const currentStep = TOUR_STEPS[currentStepIndex];

  const handleRoleSwitchAndNavigate = async (step: TourStep) => {
    try {
      setIsSwitchingRole(true);
      setSwitchFeedback(`Authenticating as ${step.role}...`);
      const user = await authService.demoLogin(step.role);
      window.dispatchEvent(new Event('auth-changed'));
      setSwitchFeedback(`Authenticated as ${user.email} (${user.role})! Navigating...`);
      setTimeout(() => {
        setIsSwitchingRole(false);
        setSwitchFeedback(null);
        navigate(step.targetRoute);
        onClose();
      }, 700);
    } catch (err) {
      console.error('Demo role switch failed:', err);
      setIsSwitchingRole(false);
      setSwitchFeedback('Authentication failed. Please retry.');
    }
  };

  const handleQuickPersonaLogin = async (role: 'APPLICANT' | 'OFFICER' | 'COMMITTEE' | 'ADMIN', route: string) => {
    try {
      setIsSwitchingRole(true);
      setSwitchFeedback(`Logging in as ${role}...`);
      await authService.demoLogin(role);
      window.dispatchEvent(new Event('auth-changed'));
      setTimeout(() => {
        setIsSwitchingRole(false);
        setSwitchFeedback(null);
        navigate(route);
        onClose();
      }, 600);
    } catch (err) {
      console.error('Persona login failed:', err);
      setIsSwitchingRole(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-900 via-slate-900 to-indigo-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-400/30 flex items-center justify-center text-teal-300">
              <Compass className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">
                  Smart India Hackathon 2026 Evaluation Tour
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  GRAND FINALE READY
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Ministry of Tribal Affairs | End-to-End Architecture Walkthrough (Phases 1 through 8)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="bg-slate-950/80 px-6 py-2 border-b border-slate-800 flex items-center gap-4 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('tour')}
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'tour'
                ? 'bg-teal-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            8-Step Guided Journey
          </button>
          <button
            onClick={() => setActiveTab('pitch')}
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'pitch'
                ? 'bg-teal-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            5-Minute Jury Pitch Notes
          </button>
          <button
            onClick={() => setActiveTab('dossiers')}
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
              activeTab === 'dossiers'
                ? 'bg-teal-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            Synthetic Test Dossiers
          </button>
        </div>

        {/* Synthetic Environment Disclaimer */}
        <div className="bg-amber-950/40 border-b border-amber-900/50 px-6 py-2 flex items-center justify-between text-[11px] text-amber-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>
              <strong>Demonstration Environment Notice:</strong> All applicant identities, bank account details, and DBT
              settlement UTRs are synthetic test fixtures (<code className="bg-amber-900/60 px-1 rounded font-mono">DEMO-*</code>). No real banking or government funds are manipulated.
            </span>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {activeTab === 'tour' && (
            <div className="space-y-6">
              {/* Step Progress Pills */}
              <div className="grid grid-cols-8 gap-1 bg-slate-950 p-1.5 rounded-xl border border-slate-800">
                {TOUR_STEPS.map((step, idx) => (
                  <button
                    key={step.stepNumber}
                    onClick={() => setCurrentStepIndex(idx)}
                    className={`py-1.5 px-1 rounded-lg text-center transition-all ${
                      currentStepIndex === idx
                        ? 'bg-teal-600 text-white font-bold shadow'
                        : idx < currentStepIndex
                        ? 'bg-slate-800 text-teal-400 font-medium'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <div className="text-[10px] uppercase tracking-wider">Step {step.stepNumber}</div>
                    <div className="text-[9px] truncate font-mono">{step.role}</div>
                  </button>
                ))}
              </div>

              {/* Active Step Card */}
              <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-6 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-900 text-teal-200 border border-teal-700">
                        {currentStep.phaseBadge}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        Dossier: {currentStep.dossierRef}
                      </span>
                    </div>
                    <h3 className="text-xl font-bold text-white">{currentStep.title}</h3>
                    <p className="text-xs text-teal-400 mt-0.5 font-medium">{currentStep.headline}</p>
                  </div>

                  <div className="text-right shrink-0">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Active Persona</span>
                    <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-white text-xs font-semibold inline-block mt-1">
                      {currentStep.personaName}
                    </span>
                  </div>
                </div>

                {/* Narrative & Jury Talking Point */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="bg-slate-900/90 border border-slate-700/50 p-4 rounded-xl space-y-2">
                    <div className="flex items-center gap-1.5 text-teal-300 font-semibold uppercase tracking-wider text-[10px]">
                      <FileText className="w-3.5 h-3.5" />
                      Lifecycle Walkthrough
                    </div>
                    <p className="text-slate-300 leading-relaxed">{currentStep.narrative}</p>
                  </div>

                  <div className="bg-indigo-950/40 border border-indigo-800/40 p-4 rounded-xl space-y-2">
                    <div className="flex items-center gap-1.5 text-indigo-300 font-semibold uppercase tracking-wider text-[10px]">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      30-Second Jury Speaking Point
                    </div>
                    <p className="text-slate-200 italic leading-relaxed">{currentStep.jurySpeakingPoint}</p>
                  </div>
                </div>

                {/* Technical Architecture Highlight */}
                <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg flex items-center gap-2 text-xs text-slate-400">
                  <Zap className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>
                    <strong>Architecture Note:</strong> {currentStep.technicalHighlight}
                  </span>
                </div>

                {/* Actions & Feedback */}
                {switchFeedback && (
                  <div className="p-2.5 rounded-lg bg-teal-950 border border-teal-800 text-teal-200 text-xs text-center animate-pulse">
                    {switchFeedback}
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-slate-700/50">
                  <div className="flex items-center gap-2">
                    <button
                      disabled={currentStepIndex === 0}
                      onClick={() => setCurrentStepIndex((prev) => prev - 1)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 disabled:opacity-40"
                    >
                      <ArrowLeft className="w-3.5 h-3.5" />
                      Previous Step
                    </button>
                    <button
                      disabled={currentStepIndex === TOUR_STEPS.length - 1}
                      onClick={() => setCurrentStepIndex((prev) => prev + 1)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 disabled:opacity-40"
                    >
                      Next Step
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <button
                    disabled={isSwitchingRole}
                    onClick={() => handleRoleSwitchAndNavigate(currentStep)}
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-semibold text-xs shadow-lg flex items-center gap-2 transition-all disabled:opacity-50"
                  >
                    {isSwitchingRole ? (
                      <span>Switching Persona & Authenticating...</span>
                    ) : (
                      <>
                        <span>{currentStep.actionButtonText}</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'pitch' && (
            <div className="space-y-5 text-xs text-slate-300">
              <div className="bg-slate-800/60 border border-slate-700 p-5 rounded-xl space-y-3">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-teal-400" />
                  5-Minute SIH Grand Finale Pitch Timeline
                </h4>
                <div className="space-y-3">
                  <div className="border-l-2 border-teal-500 pl-3">
                    <div className="font-semibold text-white">Minute 1: The Problem & Architecture</div>
                    <p className="text-slate-400 mt-0.5">
                      Paperwork bottlenecks in tribal scholarship delivery. Showcase our declarative scheme engine,
                      version locking, and client-side pre-screener that eliminates non-eligible submissions.
                    </p>
                  </div>
                  <div className="border-l-2 border-indigo-500 pl-3">
                    <div className="font-semibold text-white">Minute 2: Deterministic AI/OCR Scrutiny</div>
                    <p className="text-slate-400 mt-0.5">
                      Demonstrate Rahul Munda’s 98% confidence matching. Pivot to Priya Marandi’s income anomaly,
                      proving that our system empowers human officers rather than making opaque algorithmic decisions.
                    </p>
                  </div>
                  <div className="border-l-2 border-amber-500 pl-3">
                    <div className="font-semibold text-white">Minute 3: Deficiency Compassion & Double-Blind Merit</div>
                    <p className="text-slate-400 mt-0.5">
                      Highlight Amit Oraon’s 14-day document cure cycle (version 1 preserved for audit). Show the
                      selection committee scoring queue with all PII redacted for objective fairness.
                    </p>
                  </div>
                  <div className="border-l-2 border-emerald-500 pl-3">
                    <div className="font-semibold text-white">Minute 4: Fellowship Post-Award & 1-Click Simulated DBT</div>
                    <p className="text-slate-400 mt-0.5">
                      Show Vikram Gond’s merit list lock. Open the Admin Disbursement Desk: show Dr. Ananya Bodo’s Year 1
                      settled grant and trigger the live 1-click DBT execution for Rajeshwar Bhil!
                    </p>
                  </div>
                  <div className="border-l-2 border-cyan-500 pl-3">
                    <div className="font-semibold text-white">Minute 5: Enterprise Hardening & Q&A Defense</div>
                    <p className="text-slate-400 mt-0.5">
                      Point out PostgreSQL transactional integrity, row-locking idempotency, rate limiting, and 141
                      automated tests running in a hardened non-root container deployment.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'dossiers' && (
            <div className="space-y-4">
              <p className="text-xs text-slate-400">
                The database is populated with 8 synthetic scholar dossiers mapped across every lifecycle state:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {[
                  {
                    code: 'DEMO-APP-2026-001',
                    name: 'Sunita Soren (Santhal, Odisha)',
                    status: 'SUBMITTED',
                    role: 'APPLICANT',
                    detail: 'Fresh submission pending initial OCR ingestion.',
                  },
                  {
                    code: 'DEMO-APP-2026-002',
                    name: 'Rahul Munda (Munda, Jharkhand)',
                    status: 'UNDER_AI_VERIFICATION',
                    role: 'OFFICER',
                    detail: 'Caste certificate OCR verified at 98% confidence.',
                  },
                  {
                    code: 'DEMO-APP-2026-003',
                    name: 'Priya Marandi (Santhal, WB)',
                    status: 'UNDER_MANUAL_REVIEW',
                    role: 'OFFICER',
                    detail: 'Income mismatch flagged for officer scrutiny.',
                  },
                  {
                    code: 'DEMO-APP-2026-004',
                    name: 'Amit Oraon (Oraon, Chhattisgarh)',
                    status: 'DEFICIENT',
                    role: 'APPLICANT',
                    detail: 'Marksheet blurred; awaiting replacement upload v2.',
                  },
                  {
                    code: 'DEMO-APP-2026-005',
                    name: 'Pooja Santhal (Santhal, Jharkhand)',
                    status: 'VERIFIED',
                    role: 'COMMITTEE',
                    detail: 'Pending double-blind committee scoring.',
                  },
                  {
                    code: 'DEMO-APP-2026-006',
                    name: 'Vikram Gond (Gond, MP)',
                    status: 'SELECTED',
                    role: 'ADMIN',
                    detail: 'Merit Rank #1, Score: 92.5. Finalized in batch.',
                  },
                  {
                    code: 'DEMO-APP-2026-007',
                    name: 'Dr. Ananya Bodo (Bodo, Assam)',
                    status: 'FELLOWSHIP_ACTIVE',
                    role: 'ADMIN',
                    detail: 'IIT Guwahati; Year 1 DBT settled (Rs 3,82,000).',
                  },
                  {
                    code: 'DEMO-APP-2026-008',
                    name: 'Rajeshwar Bhil (Bhil, Rajasthan)',
                    status: 'FELLOWSHIP_ACTIVE',
                    role: 'ADMIN',
                    detail: 'MLSU Udaipur; Year 1 ready for 1-click DBT execution.',
                  },
                ].map((d) => (
                  <div key={d.code} className="bg-slate-800/80 border border-slate-700/80 p-3 rounded-lg space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-teal-400">{d.code}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 font-semibold">
                        {d.status}
                      </span>
                    </div>
                    <div className="font-semibold text-white">{d.name}</div>
                    <div className="text-slate-400 text-[11px]">{d.detail}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Quick Persona Switcher */}
        <div className="bg-slate-950 px-6 py-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Quick Persona Switch:</span>
            <button
              onClick={() => handleQuickPersonaLogin('APPLICANT', '/applicant/dashboard')}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
            >
              Scholar
            </button>
            <button
              onClick={() => handleQuickPersonaLogin('OFFICER', '/officer/dashboard')}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
            >
              Officer
            </button>
            <button
              onClick={() => handleQuickPersonaLogin('COMMITTEE', '/committee/batch')}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
            >
              Committee
            </button>
            <button
              onClick={() => handleQuickPersonaLogin('ADMIN', '/admin/disbursements')}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold transition-colors"
            >
              Admin (DBT)
            </button>
          </div>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium transition-colors"
          >
            Close Tour
          </button>
        </div>
      </div>
    </div>
  );
};
