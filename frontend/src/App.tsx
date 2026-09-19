import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { SchemeExplorer } from './pages/SchemeExplorer';
import { SchemeDetail } from './pages/SchemeDetail';
import { SchemeAdmin } from './pages/admin/SchemeAdmin';
import { ApplicantDashboard } from './pages/applicant/ApplicantDashboard';
import { ApplicationWizard } from './pages/applicant/ApplicationWizard';

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
            <Route path="/applicant/dashboard" element={<ApplicantDashboard />} />
            <Route path="/applications/:applicationId" element={<ApplicationWizard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>

        <Footer />
      </div>
    </BrowserRouter>
  );
};

export default App;
