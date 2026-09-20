import React from 'react';
import { Clock, CheckCircle2, AlertTriangle, XCircle, FileText } from 'lucide-react';
import { OfficerQueueCounts } from '../../types/officer';

interface OfficerMetricsCardsProps {
  counts: OfficerQueueCounts;
  activeFilter?: string;
  onSelectFilter: (status: string) => void;
}

export const OfficerMetricsCards: React.FC<OfficerMetricsCardsProps> = ({
  counts,
  activeFilter,
  onSelectFilter,
}) => {
  const cards = [
    {
      id: 'UNDER_MANUAL_REVIEW',
      title: 'Pending Scrutiny',
      count: counts.pending_review,
      icon: Clock,
      color: 'border-amber-500/40 bg-amber-50 text-amber-900',
      activeColor: 'ring-2 ring-amber-500 bg-amber-100',
      badgeColor: 'bg-amber-200 text-amber-800',
      description: 'Awaiting desk review',
    },
    {
      id: 'VERIFIED',
      title: 'Scrutinized & Verified',
      count: counts.verified,
      icon: CheckCircle2,
      color: 'border-emerald-500/40 bg-emerald-50 text-emerald-900',
      activeColor: 'ring-2 ring-emerald-500 bg-emerald-100',
      badgeColor: 'bg-emerald-200 text-emerald-800',
      description: 'Ready for evaluation',
    },
    {
      id: 'DEFICIENT',
      title: 'Flagged Deficient',
      count: counts.deficient,
      icon: AlertTriangle,
      color: 'border-orange-500/40 bg-orange-50 text-orange-900',
      activeColor: 'ring-2 ring-orange-500 bg-orange-100',
      badgeColor: 'bg-orange-200 text-orange-800',
      description: 'Handed to Phase 5',
    },
    {
      id: 'REJECTED',
      title: 'Disqualified / Rejected',
      count: counts.rejected,
      icon: XCircle,
      color: 'border-rose-500/40 bg-rose-50 text-rose-900',
      activeColor: 'ring-2 ring-rose-500 bg-rose-100',
      badgeColor: 'bg-rose-200 text-rose-800',
      description: 'Ineligible or forged',
    },
    {
      id: 'ALL',
      title: 'Total In Scope',
      count: counts.all,
      icon: FileText,
      color: 'border-slate-300 bg-slate-50 text-slate-800',
      activeColor: 'ring-2 ring-slate-600 bg-slate-100',
      badgeColor: 'bg-slate-200 text-slate-700',
      description: 'Applications in jurisdiction',
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {cards.map((card) => {
        const Icon = card.icon;
        const isSelected = (activeFilter || 'UNDER_MANUAL_REVIEW') === card.id;

        return (
          <button
            key={card.id}
            onClick={() => onSelectFilter(card.id)}
            className={`p-3.5 rounded-xl border text-left transition-all duration-150 flex flex-col justify-between ${
              card.color
            } ${isSelected ? card.activeColor + ' shadow-sm' : 'hover:bg-opacity-80'}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold tracking-wide uppercase text-slate-600">
                {card.title}
              </span>
              <Icon className="w-4 h-4 opacity-75" />
            </div>
            <div>
              <div className="text-2xl font-bold tracking-tight text-slate-900">
                {card.count}
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">{card.description}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
};
