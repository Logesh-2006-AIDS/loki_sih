import React, { useState, useEffect } from 'react';
import {
  Plus,
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Edit,
  UserCheck,
} from 'lucide-react';
import { Scheme, SchemeVersion, UserProfile } from '../../types/scheme';
import { schemeService } from '../../services/schemeService';
import { authService } from '../../services/authService';

export const SchemeAdmin: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [selectedScheme, setSelectedScheme] = useState<Scheme | null>(null);
  const [versions, setVersions] = useState<SchemeVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newVersionNum, setNewVersionNum] = useState('');
  const [newVersionName, setNewVersionName] = useState('');
  const [newVersionDesc, setNewVersionDesc] = useState('');
  const [newVersionRulesJson, setNewVersionRulesJson] = useState('{\n  "min_qualifying_percentage": 60.0,\n  "max_annual_family_income": 650000\n}');
  const [newVersionActivate, setNewVersionActivate] = useState(false);

  // Edit Modal
  const [editingVersion, setEditingVersion] = useState<SchemeVersion | null>(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editRulesJson, setEditRulesJson] = useState('');

  useEffect(() => {
    const handleAuthChange = () => {
      setCurrentUser(authService.getCurrentUser());
    };
    window.addEventListener('auth-changed', handleAuthChange);
    handleAuthChange();
    fetchSchemes();

    return () => {
      window.removeEventListener('auth-changed', handleAuthChange);
    };
  }, []);

  const fetchSchemes = async () => {
    try {
      setLoading(true);
      const data = await schemeService.getSchemes();
      setSchemes(data);
      if (data.length > 0 && !selectedScheme) {
        setSelectedScheme(data[0]);
        loadVersions(data[0].id);
      } else if (selectedScheme) {
        loadVersions(selectedScheme.id);
      }
    } catch (err) {
      console.error('Failed to load schemes', err);
    } finally {
      setLoading(false);
    }
  };

  const loadVersions = async (schemeId: string) => {
    try {
      const vList = await schemeService.getSchemeVersions(schemeId);
      setVersions(vList);
    } catch (err) {
      console.error('Failed to load scheme versions', err);
    }
  };

  const handleSchemeSelect = (s: Scheme) => {
    setSelectedScheme(s);
    loadVersions(s.id);
    setMessage(null);
  };

  const handleActivateVersion = async (v: SchemeVersion) => {
    try {
      setActionLoading(true);
      await schemeService.activateSchemeVersion(v.id);
      setMessage({
        type: 'success',
        text: `Version ${v.scheme_version} activated successfully. Previous active version was deactivated.`,
      });
      fetchSchemes();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to activate version.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleLockVersion = async (v: SchemeVersion) => {
    if (!window.confirm(`Are you sure you want to permanently lock Version ${v.scheme_version}? Once locked, it can NEVER be edited.`)) {
      return;
    }
    try {
      setActionLoading(true);
      await schemeService.lockSchemeVersion(v.id);
      setMessage({
        type: 'success',
        text: `Version ${v.scheme_version} has been permanently locked.`,
      });
      fetchSchemes();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to lock version.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedScheme) return;
    try {
      setActionLoading(true);
      let parsedRules = {};
      try {
        parsedRules = JSON.parse(newVersionRulesJson);
      } catch {
        alert('Invalid JSON in Eligibility Rules field.');
        setActionLoading(false);
        return;
      }

      await schemeService.createSchemeVersion(selectedScheme.id, {
        scheme_version: newVersionNum.trim(),
        name: newVersionName || `${selectedScheme.name} v${newVersionNum}`,
        description: newVersionDesc || selectedScheme.description || '',
        eligibility_rules: parsedRules,
        is_active: newVersionActivate,
      });

      setMessage({
        type: 'success',
        text: `Version ${newVersionNum} created successfully.`,
      });
      setIsCreateModalOpen(false);
      setNewVersionNum('');
      setNewVersionName('');
      setNewVersionDesc('');
      fetchSchemes();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to create scheme version.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const openEditModal = (v: SchemeVersion) => {
    setEditingVersion(v);
    setEditName(v.name);
    setEditDesc(v.description || '');
    setEditRulesJson(JSON.stringify(v.eligibility_rules, null, 2));
  };

  const handleUpdateVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingVersion) return;
    try {
      setActionLoading(true);
      let parsedRules = {};
      try {
        parsedRules = JSON.parse(editRulesJson);
      } catch {
        alert('Invalid JSON in Eligibility Rules field.');
        setActionLoading(false);
        return;
      }

      await schemeService.updateSchemeVersion(editingVersion.id, {
        name: editName,
        description: editDesc,
        eligibility_rules: parsedRules,
      });

      setMessage({
        type: 'success',
        text: `Version ${editingVersion.scheme_version} updated successfully.`,
      });
      setEditingVersion(null);
      fetchSchemes();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to update scheme version.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  // RBAC Access Check
  if (currentUser?.role !== 'ADMIN') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-md max-w-md text-center">
          <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center mx-auto mb-4 font-bold">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Administrator Access Required</h2>
          <p className="text-xs text-slate-500 mt-2 mb-6">
            The Scheme Configuration Console is restricted to System Administrators.
            You are currently browsing with {currentUser ? `role: ${currentUser.role}` : 'an unauthenticated guest session'}.
          </p>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-left mb-6">
            <p className="text-xs font-semibold text-slate-700 mb-1">
              Prototype Quick Switch:
            </p>
            <p className="text-[11px] text-slate-500 mb-3">
              Click below to immediately authenticate as the demo administrator:
            </p>
            <button
              onClick={() => authService.demoLogin('ADMIN').then(() => window.dispatchEvent(new Event('auth-changed')))}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-all shadow-sm"
            >
              <UserCheck className="w-4 h-4" />
              Login as Admin Demo
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Console Header */}
        <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-sm border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wider">
                Admin Console
              </span>
              <span className="text-xs text-slate-400">Phase 1 Scheme Engine</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight mt-1">
              Scheme & Version Management Console
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Authoritative configuration of scheme versions, eligibility rules, and locking lifecycle.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchSchemes()}
              className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold transition-colors flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Create Version
            </button>
          </div>
        </div>

        {/* Message Banner */}
        {message && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-xs ${
              message.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                : 'bg-red-50 border-red-200 text-red-950'
            }`}
          >
            <div className="flex items-center gap-2">
              {message.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
              )}
              <span>{message.text}</span>
            </div>
            <button
              onClick={() => setMessage(null)}
              className="text-slate-400 hover:text-slate-700 text-xs font-bold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Scheme Selector Pills */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3 overflow-x-auto">
          <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">Select Scheme:</span>
          {schemes.map((s) => {
            const isSelected = selectedScheme?.id === s.id;
            return (
              <button
                key={s.id}
                onClick={() => handleSchemeSelect(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                  isSelected
                    ? 'bg-teal-700 text-white shadow-sm ring-1 ring-teal-500'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {s.scheme_code} — {s.name}
              </button>
            );
          })}
        </div>

        {/* Versions Table */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Configured Versions for {selectedScheme?.scheme_code}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Single Active Version Rule: Exactly one version can be active at a time. Activating another version deactivates the rest.
              </p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              {versions.length} Version{versions.length === 1 ? '' : 's'}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Name / Label</th>
                  <th className="py-3 px-4">State</th>
                  <th className="py-3 px-4">Lock Status</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {versions.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                      v{v.scheme_version}
                    </td>
                    <td className="py-3.5 px-4 text-slate-800 font-medium">
                      {v.name}
                    </td>
                    <td className="py-3.5 px-4">
                      {v.is_active ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                          INACTIVE
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      {v.is_locked ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-800 inline-flex items-center gap-1">
                          <Lock className="w-3 h-3" /> Locked
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 inline-flex items-center gap-1">
                          <Unlock className="w-3 h-3" /> Unlocked
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {new Date(v.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* Edit button */}
                        <button
                          onClick={() => openEditModal(v)}
                          disabled={v.is_locked || actionLoading}
                          className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-colors ${
                            v.is_locked
                              ? 'text-slate-300 cursor-not-allowed'
                              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                          }`}
                          title={v.is_locked ? 'Locked versions cannot be modified' : 'Edit unlocked version'}
                        >
                          <Edit className="w-3 h-3" />
                          Edit
                        </button>

                        {/* Activate button */}
                        {!v.is_active && (
                          <button
                            onClick={() => handleActivateVersion(v)}
                            disabled={actionLoading}
                            className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                          >
                            Activate
                          </button>
                        )}

                        {/* Lock button */}
                        {!v.is_locked && (
                          <button
                            onClick={() => handleLockVersion(v)}
                            disabled={actionLoading}
                            className="px-2.5 py-1 rounded text-xs font-semibold bg-slate-800 text-white hover:bg-slate-700 transition-colors flex items-center gap-1"
                          >
                            <Lock className="w-3 h-3" />
                            Lock
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create Version Modal */}
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 border border-slate-200 animate-in fade-in">
              <h3 className="text-base font-bold text-slate-900 mb-1">
                Create New Version for {selectedScheme?.scheme_code}
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Define a new scheme version with custom rule parameters and schemas.
              </p>

              <form onSubmit={handleCreateVersion} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Version Identifier (e.g. 1.1, 2.0) *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 1.1"
                    value={newVersionNum}
                    onChange={(e) => setNewVersionNum(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Version Name / Title
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 2026 Revised Criteria"
                    value={newVersionName}
                    onChange={(e) => setNewVersionName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Eligibility Rules (JSON Object) *
                  </label>
                  <textarea
                    rows={5}
                    value={newVersionRulesJson}
                    onChange={(e) => setNewVersionRulesJson(e.target.value)}
                    className="w-full font-mono text-xs p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-slate-50"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Accepts numeric thresholds, category equality, or structured 'rules' list.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="makeActive"
                    checked={newVersionActivate}
                    onChange={(e) => setNewVersionActivate(e.target.checked)}
                    className="rounded text-teal-600 focus:ring-teal-500"
                  />
                  <label htmlFor="makeActive" className="text-xs font-medium text-slate-700">
                    Activate immediately upon creation (deactivates previous active version)
                  </label>
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-5 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold shadow-sm"
                  >
                    {actionLoading ? 'Creating...' : 'Create Version'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Unlocked Version Modal */}
        {editingVersion && (
          <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 border border-slate-200 animate-in fade-in">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-bold text-slate-900">
                  Edit Unlocked Version {editingVersion.scheme_version}
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700">
                  UNLOCKED
                </span>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Modify title, description, or eligibility rules. All edits record immutable audit entries.
              </p>

              <form onSubmit={handleUpdateVersion} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Version Title / Name
                  </label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Description
                  </label>
                  <textarea
                    rows={2}
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Eligibility Rules (JSON Object)
                  </label>
                  <textarea
                    rows={6}
                    value={editRulesJson}
                    onChange={(e) => setEditRulesJson(e.target.value)}
                    className="w-full font-mono text-xs p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-slate-50"
                  />
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setEditingVersion(null)}
                    className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-5 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold shadow-sm"
                  >
                    {actionLoading ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
