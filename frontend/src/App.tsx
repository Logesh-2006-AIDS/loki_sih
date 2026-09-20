import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { SchemeExplorer } from './pages/SchemeExplorer';
import { SchemeDetail } from './pages/SchemeDetail';
import { SchemeAdmin } from './pages/admin/SchemeAdmin';
import { AdminAnalytics } from './pages/admin/AdminAnalytics';
import { ApplicantDashboard } from './pages/applicant/ApplicantDashboard';
import { ApplicationWizard } from './pages/applicant/ApplicationWizard';
import { DeficiencyResolution } from './pages/applicant/DeficiencyResolution';
import { OfficerDashboard } from './pages/officer/OfficerDashboard';
import { OfficerScrutiny } from './pages/officer/OfficerScrutiny';
import { CommitteeDashboard } from './pages/committee/CommitteeDashboard';
import { CommitteeQueue } from './pages/committee/CommitteeQueue';
import { CommitteeScrutiny } from './pages/committee/CommitteeScrutiny';
import { MeritRankingConsole } from './pages/committee/MeritRankingConsole';
import { FellowshipPortal } from './pages/applicant/FellowshipPortal';
import { OfficerFellowshipWorkbench } from './pages/officer/OfficerFellowshipWorkbench';
import { AdminDisbursementDesk } from './pages/admin/AdminDisbursementDesk';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
        <Navbar />

        <div className="flex-1">
          <Routes>
            <Route path="/" element={<SchemeExplorer />} />
            <Route path="/schemes/:schemeId" element={<SchemeDetail />} />
            <Route path="/admin/schemes" element={<SchemeAdmin />} />
            <Route path="/admin/analytics" element={<AdminAnalytics />} />
            <Route path="/admin/disbursements" element={<AdminDisbursementDesk />} />
            <Route path="/applicant/dashboard" element={<ApplicantDashboard />} />
            <Route path="/applicant/fellowship" element={<FellowshipPortal />} />
            <Route path="/applications/:applicationId" element={<ApplicationWizard />} />
            <Route path="/applications/:applicationId/deficiencies" element={<DeficiencyResolution />} />
            <Route path="/officer/dashboard" element={<OfficerDashboard />} />
            <Route path="/officer/fellowships" element={<OfficerFellowshipWorkbench />} />
            <Route path="/officer/applications/:applicationId/scrutiny" element={<OfficerScrutiny />} />
            <Route path="/committee" element={<CommitteeDashboard />} />
            <Route path="/committee/batches/:batchId/queue" element={<CommitteeQueue />} />
            <Route path="/committee/batches/:batchId/scrutiny/:applicationId" element={<CommitteeScrutiny />} />
            <Route path="/committee/batches/:batchId/ranking" element={<MeritRankingConsole />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>

        <Footer />
      </div>
    </BrowserRouter>
  );
};

export default App;
