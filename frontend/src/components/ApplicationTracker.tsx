import React from 'react';
import {
  CheckCircle2,
  Clock,
  Circle,
  Bot,
  UserCheck,
  Award,
  FileCheck2,
} from 'lucide-react';
import { ApplicationStatus } from '../types/application';

interface Props {
  status: ApplicationStatus;
  submittedAt?: string | null;
  referenceId: string;
}

interface Step {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
}

const LIFECYCLE_STEPS: Step[] = [
  {
    id: 'SUBMITTED',
    label: 'Application Submitted',
    description: 'Applicant completed and submitted the application dossier.',
    icon: FileCheck2,
  },
  {
    id: 'UNDER_AI_VERIFICATION',
    label: 'Under AI Verification',
    description: 'Automated verification queue (Phase 3 OCR & eligibility parsing).',
    icon: Bot,
  },
  {
    id: 'UNDER_MANUAL_REVIEW',
    label: 'Under Manual Review',
    description: 'Scrutiny by assigned MoTA verification officers.',
    icon: UserCheck,
  },
  {
    id: 'SHORTLISTED',
    label: 'Shortlisted & Merit Ranked',
    description: 'Committee evaluation and quota allocation.',
    icon: Award,
  },
  {
    id: 'FINAL_DECISION',
    label: 'Sanction / Final Decision',
    description: 'Final award letter and fellowship activation.',
    icon: CheckCircle2,
  },
];

export const ApplicationTracker: React.FC<Props> = ({
  status,
  submittedAt,
  referenceId,
}) => {
  // Determine index of current status
  const getStepState = (stepIndex: number): 'completed' | 'active' | 'pending' => {
    // If DRAFT, nothing submitted yet
    if (status === 'DRAFT') {
      return 'pending';
    }

    // Current state mappings
    let currentActiveIndex = 1; // Default to UNDER_AI_VERIFICATION when submitted
    if (status === 'SUBMITTED') {
      currentActiveIndex = 0;
    } else if (status === 'UNDER_AI_VERIFICATION') {
      currentActiveIndex = 1;
    } else if (status === 'UNDER_MANUAL_REVIEW' || status === 'DEFICIENT' || status === 'RESUBMITTED') {
      currentActiveIndex = 2;
    } else if (status === 'VERIFIED' || status === 'SHORTLISTED' || status === 'MERIT_RANKED') {
      currentActiveIndex = 3;
    } else if (status === 'SELECTED' || status === 'WAITLISTED' || status === 'REJECTED' || status === 'FELLOWSHIP_ACTIVE') {
      currentActiveIndex = 4;
    }

    if (stepIndex < currentActiveIndex) return 'completed';
    if (stepIndex === currentActiveIndex) return 'active';
    return 'pending';
  };

  const formattedDate = submittedAt
    ? new Date(submittedAt).toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Pending Submission';

  return (
    <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
      <div className="border-b border-slate-100 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
            Application Status Tracker
          </span>
          <h3 className="text-base font-bold text-slate-900 mt-1">
            Application Lifecycle Progress
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 font-mono">
            Reference ID: {referenceId}
          </p>
        </div>

        <div className="text-right">
          <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-blue-50 text-blue-800 border border-blue-200">
            {status.replace(/_/g, ' ')}
          </span>
          <p className="text-[11px] text-slate-400 mt-1">
            Submitted: {formattedDate}
          </p>
        </div>
      </div>

      {/* Stepper Timeline */}
      <div className="relative pl-6 sm:pl-8 space-y-8 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
        {LIFECYCLE_STEPS.map((step, idx) => {
          const state = getStepState(idx);

          return (
            <div key={step.id} className="relative flex items-start gap-4">
              {/* Step indicator node */}
              <div
                className={`absolute -left-6 sm:-left-8 w-7 h-7 rounded-full flex items-center justify-center font-bold transition-all ${
                  state === 'completed'
                    ? 'bg-emerald-600 text-white shadow-sm ring-4 ring-emerald-50'
                    : state === 'active'
                    ? 'bg-blue-600 text-white shadow-md ring-4 ring-blue-100 animate-pulse'
                    : 'bg-white text-slate-300 border-2 border-slate-300'
                }`}
              >
                {state === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : state === 'active' ? (
                  <Clock className="w-4 h-4" />
                ) : (
                  <Circle className="w-3 h-3 text-slate-300" />
                )}
              </div>

              {/* Step Content */}
              <div
                className={`flex-1 p-4 rounded-xl border transition-all ${
                  state === 'active'
                    ? 'bg-blue-50/40 border-blue-200 ring-1 ring-blue-200'
                    : state === 'completed'
                    ? 'bg-emerald-50/20 border-emerald-100'
                    : 'bg-slate-50/40 border-slate-200 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <h4 className="text-xs sm:text-sm font-bold text-slate-900 flex items-center gap-1.5">
                    {step.label}
                    {state === 'active' && (
                      <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
                        Current Stage
                      </span>
                    )}
                    {state === 'completed' && (
                      <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800">
                        COMPLETED
                      </span>
                    )}
                  </h4>
                </div>

                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  {step.description}
                </p>

                {state === 'active' && step.id === 'UNDER_AI_VERIFICATION' && (
                  <div className="mt-3 p-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-900 text-xs flex items-start gap-2">
                    <Bot className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold">Queued for AI Verification (Phase 3)</p>
                      <p className="text-[11px] text-blue-700 mt-0.5">
                        Your application has been received. In the upcoming phase, document authenticity, OCR text extraction, and merit scoring will be evaluated automatically.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
