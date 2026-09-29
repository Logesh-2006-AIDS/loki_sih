import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { SchemeExplorer } from './pages/SchemeExplorer';
import { SchemeDetail } from './pages/SchemeDetail';
import { SchemeAdmin } from './pages/admin/SchemeAdmin';
import { AdminUserApprovals } from './pages/admin/AdminUserApprovals';
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
            {/* Public Entry & Discovery Routes */}
            <Route path="/" element={<SchemeExplorer />} />
            <Route path="/schemes/:schemeId" element={<SchemeDetail />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Applicant Protected Routes */}
            <Route
              path="/applicant/dashboard"
              element={
                <ProtectedRoute allowedRoles={['APPLICANT', 'ADMIN']}>
                  <ApplicantDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/applicant/fellowship"
              element={
                <ProtectedRoute allowedRoles={['APPLICANT', 'ADMIN']}>
                  <FellowshipPortal />
                </ProtectedRoute>
              }
            />
            <Route
              path="/applications/:applicationId"
              element={
                <ProtectedRoute allowedRoles={['APPLICANT', 'ADMIN']}>
                  <ApplicationWizard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/applications/:applicationId/deficiencies"
              element={
                <ProtectedRoute allowedRoles={['APPLICANT', 'ADMIN']}>
                  <DeficiencyResolution />
                </ProtectedRoute>
              }
            />

            {/* Officer Protected Routes */}
            <Route
              path="/officer/dashboard"
              element={
                <ProtectedRoute allowedRoles={['OFFICER', 'ADMIN']}>
                  <OfficerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/officer/fellowships"
              element={
                <ProtectedRoute allowedRoles={['OFFICER', 'ADMIN']}>
                  <OfficerFellowshipWorkbench />
                </ProtectedRoute>
              }
            />
            <Route
              path="/officer/applications/:applicationId/scrutiny"
              element={
                <ProtectedRoute allowedRoles={['OFFICER', 'ADMIN']}>
                  <OfficerScrutiny />
                </ProtectedRoute>
              }
            />

            {/* Committee Protected Routes */}
            <Route
              path="/committee"
              element={
                <ProtectedRoute allowedRoles={['COMMITTEE', 'ADMIN']}>
                  <CommitteeDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/committee/batches/:batchId/queue"
              element={
                <ProtectedRoute allowedRoles={['COMMITTEE', 'ADMIN']}>
                  <CommitteeQueue />
                </ProtectedRoute>
              }
            />
            <Route
              path="/committee/batches/:batchId/scrutiny/:applicationId"
              element={
                <ProtectedRoute allowedRoles={['COMMITTEE', 'ADMIN']}>
                  <CommitteeScrutiny />
                </ProtectedRoute>
              }
            />
            <Route
              path="/committee/batches/:batchId/ranking"
              element={
                <ProtectedRoute allowedRoles={['COMMITTEE', 'ADMIN']}>
                  <MeritRankingConsole />
                </ProtectedRoute>
              }
            />

            {/* Admin Protected Routes */}
            <Route
              path="/admin"
              element={<Navigate to="/admin/schemes" replace />}
            />
            <Route
              path="/admin/schemes"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <SchemeAdmin />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/user-approvals"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <AdminUserApprovals />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/analytics"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <AdminAnalytics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/disbursements"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <AdminDisbursementDesk />
                </ProtectedRoute>
              }
            />

            {/* Fallback Catch-all Route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>

        <Footer />
      </div>
    </BrowserRouter>
  );
};

export default App;
