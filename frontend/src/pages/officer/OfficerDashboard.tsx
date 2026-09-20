import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, RefreshCw, ShieldCheck } from 'lucide-react';
import { officerService } from '../../services/officerService';
import { OfficerQueueCounts, OfficerQueueItem } from '../../types/officer';
import { OfficerMetricsCards } from '../../components/officer/OfficerMetricsCards';
import { OfficerQueueTable } from '../../components/officer/OfficerQueueTable';

export const OfficerDashboard: React.FC = () => {
  const [items, setItems] = useState<OfficerQueueItem[]>([]);
  const [counts, setCounts] = useState<OfficerQueueCounts>({
    pending_review: 0,
    verified: 0,
    deficient: 0,
    rejected: 0,
    all: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [activeStatusFilter, setActiveStatusFilter] = useState<string>('UNDER_MANUAL_REVIEW');
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [aiFlagFilter, setAiFlagFilter] = useState<string>('ALL');

  const fetchQueue = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await officerService.getQueue({
        status_filter: activeStatusFilter,
        search: searchQuery.trim() || undefined,
        state: stateFilter.trim() || undefined,
        has_ai_flags: aiFlagFilter === 'FLAGGED' ? true : aiFlagFilter === 'CLEAN' ? false : undefined,
        limit: 100,
      });
      setItems(res.items);
      setCounts(res.counts);
    } catch (err) {
      console.error('Failed to load officer queue', err);
    } finally {
      setIsLoading(false);
    }
  }, [activeStatusFilter, searchQuery, stateFilter, aiFlagFilter]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  // Listen for auth-changed event (e.g. demo role switcher in navbar)
  useEffect(() => {
    const handleAuthChanged = () => {
      fetchQueue();
    };
    window.addEventListener('auth-changed', handleAuthChanged);
    return () => window.removeEventListener('auth-changed', handleAuthChanged);
  }, [fetchQueue]);

  return (
    <div className="min-h-screen bg-slate-100/60 pb-16">
      {/* Page Header */}
      <div className="bg-white border-b border-slate-200 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-teal-100 text-teal-800 border border-teal-200">
                  Human Scrutiny Portal
                </span>
                <span className="text-xs text-slate-400">Phase 4 Desk Scrutiny</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
                Officer Verification Dashboard
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Inspect assigned applications, evaluate Phase 3 AI extractions, and record authoritative human determinations.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => fetchQueue()}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh Queue
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-6">
        {/* Workload Metric Counters */}
        <OfficerMetricsCards
          counts={counts}
          activeFilter={activeStatusFilter}
          onSelectFilter={(status) => setActiveStatusFilter(status)}
        />

        {/* Filter and Search Toolbar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-[260px] max-w-md">
            <div className="relative w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search reference ID or applicant name..."
                className="w-full text-xs pl-9 pr-3 py-2 rounded-lg border border-slate-300 text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 text-xs">
            {/* AI Risk Filter */}
            <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
              <span className="text-slate-500 font-medium">AI Status:</span>
              <select
                value={aiFlagFilter}
                onChange={(e) => setAiFlagFilter(e.target.value)}
                className="bg-transparent text-slate-800 font-semibold focus:outline-none cursor-pointer"
              >
                <option value="ALL">All Applications</option>
                <option value="FLAGGED">Flags Detected Only</option>
                <option value="CLEAN">Clean / AI Verified</option>
              </select>
            </div>

            {/* State Filter */}
            <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-slate-500 font-medium">State:</span>
              <input
                type="text"
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                placeholder="All States"
                className="w-24 bg-transparent text-slate-800 font-semibold focus:outline-none placeholder-slate-400"
              />
            </div>
          </div>
        </div>

        {/* Queue Table */}
        <OfficerQueueTable items={items} isLoading={isLoading} />
      </div>
    </div>
  );
};
