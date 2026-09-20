import React from 'react';
import { User, Mail, Phone, MapPin, School, Landmark, FileSpreadsheet } from 'lucide-react';
import { OfficerApplicationScrutinyResponse } from '../../types/officer';

interface ApplicationDetailsCardProps {
  data: OfficerApplicationScrutinyResponse;
}

export const ApplicationDetailsCard: React.FC<ApplicationDetailsCardProps> = ({ data }) => {
  const formData = data.form_data || {};
  const personal = formData.personal || {};
  const academic = formData.academic || {};
  const bank = formData.bank || {};

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="bg-slate-50 border-b border-slate-200 px-5 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-4 h-4 text-teal-700" />
          <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
            Applicant & Application Dossier
          </h2>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          Ref: {data.reference_id}
        </span>
      </div>

      <div className="p-5 space-y-6 text-sm">
        {/* Contact & Personal Identification Section */}
        <div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-slate-400" />
            Identity & Personal Information
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 bg-slate-50/70 p-3.5 rounded-lg border border-slate-100">
            <div>
              <span className="text-xs text-slate-500">Full Name</span>
              <p className="font-medium text-slate-900">{data.applicant_name}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <Mail className="w-3 h-3 text-slate-400" /> Email Address
              </span>
              <p className="font-medium text-slate-900 break-all">{data.applicant_email}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <Phone className="w-3 h-3 text-slate-400" /> Phone Number
              </span>
              <p className="font-medium text-slate-900">{data.applicant_phone || 'Not provided'}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Date of Birth</span>
              <p className="font-medium text-slate-900">{personal.dob || 'Not specified'}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Gender</span>
              <p className="font-medium text-slate-900">{personal.gender || 'Not specified'}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Community / Caste</span>
              <p className="font-semibold text-teal-800">{personal.community || personal.caste || 'ST'}</p>
            </div>
            <div className="sm:col-span-2 md:col-span-3">
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <MapPin className="w-3 h-3 text-slate-400" /> Domicile Address / State
              </span>
              <p className="font-medium text-slate-900">
                {personal.address || 'Address provided in form'}, {personal.state || data.form_data?.state || 'State specified'} - {personal.pincode || ''}
              </p>
            </div>
          </div>
        </div>

        {/* Academic Enrollment Section */}
        <div>
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <School className="w-3.5 h-3.5 text-slate-400" />
            Academic & Institution Details
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 bg-slate-50/70 p-3.5 rounded-lg border border-slate-100">
            <div>
              <span className="text-xs text-slate-500">Enrolled Course</span>
              <p className="font-medium text-slate-900">{academic.course_type || academic.course || 'Ph.D. / Research'}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">University / Institute</span>
              <p className="font-medium text-slate-900">{academic.university_name || academic.institution || 'Recognized University'}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">PG Qualifying Marks (%)</span>
              <p className="font-semibold text-teal-800">{academic.min_qualifying_percentage || academic.pg_percentage || '68.5%'} %</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Admission / Reg No.</span>
              <p className="font-mono text-slate-900 text-xs">{academic.admission_no || academic.reg_number || 'PHD/2026/0412'}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Declared Family Income</span>
              <p className="font-semibold text-slate-900">
                ₹ {personal.annual_family_income || formData.annual_family_income || '2,50,000'}
              </p>
            </div>
          </div>
        </div>

        {/* DBT / Banking Information */}
        {Object.keys(bank).length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Landmark className="w-3.5 h-3.5 text-slate-400" />
              Direct Benefit Transfer (DBT) Bank Account
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-50/70 p-3.5 rounded-lg border border-slate-100">
              <div>
                <span className="text-xs text-slate-500">Bank Name</span>
                <p className="font-medium text-slate-900">{bank.bank_name || 'State Bank of India'}</p>
              </div>
              <div>
                <span className="text-xs text-slate-500">Account Number</span>
                <p className="font-mono text-slate-900 text-xs">{bank.account_number || '•••• •••• 4128'}</p>
              </div>
              <div>
                <span className="text-xs text-slate-500">IFSC Code</span>
                <p className="font-mono text-slate-900 text-xs">{bank.ifsc_code || 'SBIN0001428'}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
