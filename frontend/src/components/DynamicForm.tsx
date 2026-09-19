import React, { useState } from 'react';
import {
  ChevronRight,
  ChevronLeft,
  Save,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';
import { FormSchema, FormField } from '../types/application';

interface Props {
  schema: FormSchema;
  formData: Record<string, any>;
  onChange: (updatedData: Record<string, any>) => void;
  onSaveDraft: () => Promise<void>;
  isReadOnly?: boolean;
}

export const DynamicForm: React.FC<Props> = ({
  schema,
  formData,
  onChange,
  onSaveDraft,
  isReadOnly = false,
}) => {
  const sections = schema.sections || [];
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  if (sections.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
        No form sections configured for this scheme version.
      </div>
    );
  }

  const currentSection = sections[activeSectionIndex] || sections[0];

  const handleFieldChange = (fieldName: string, value: any) => {
    if (isReadOnly) return;
    onChange({
      ...formData,
      [fieldName]: value,
    });
  };

  const handleManualSave = async () => {
    try {
      setSaving(true);
      await onSaveDraft();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch (err) {
      console.error('Draft save failed', err);
    } finally {
      setSaving(false);
    }
  };

  const renderField = (field: FormField) => {
    const value = formData[field.name] ?? '';

    return (
      <div key={field.name} className="space-y-1.5">
        <label className="block text-xs font-bold text-slate-800">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </label>

        {field.help_text && (
          <p className="text-[11px] text-slate-400 flex items-center gap-1 mb-1">
            <HelpCircle className="w-3 h-3 text-slate-400 shrink-0" />
            {field.help_text}
          </p>
        )}

        {/* 1. Text */}
        {field.type === 'text' && (
          <input
            type="text"
            value={value}
            disabled={isReadOnly}
            required={field.required}
            placeholder={field.placeholder}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100 disabled:text-slate-500"
          />
        )}

        {/* 2. Number */}
        {field.type === 'number' && (
          <input
            type="number"
            step="any"
            value={value}
            disabled={isReadOnly}
            required={field.required}
            placeholder={field.placeholder}
            onChange={(e) =>
              handleFieldChange(
                field.name,
                e.target.value === '' ? '' : parseFloat(e.target.value)
              )
            }
            className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100 disabled:text-slate-500"
          />
        )}

        {/* 3. Date */}
        {field.type === 'date' && (
          <input
            type="date"
            value={value}
            disabled={isReadOnly}
            required={field.required}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100 disabled:text-slate-500"
          />
        )}

        {/* 4. Email */}
        {field.type === 'email' && (
          <input
            type="email"
            value={value}
            disabled={isReadOnly}
            required={field.required}
            placeholder={field.placeholder}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100 disabled:text-slate-500"
          />
        )}

        {/* 5. Phone */}
        {field.type === 'phone' && (
          <input
            type="tel"
            value={value}
            disabled={isReadOnly}
            required={field.required}
            placeholder={field.placeholder}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100 disabled:text-slate-500"
          />
        )}

        {/* 6. Select */}
        {field.type === 'select' && (
          <select
            value={value}
            disabled={isReadOnly}
            required={field.required}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white disabled:bg-slate-100 disabled:text-slate-500"
          >
            <option value="">-- Select an option --</option>
            {field.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )}

        {/* 7. Radio */}
        {field.type === 'radio' && (
          <div className="flex flex-wrap gap-4 pt-1">
            {field.options?.map((opt) => (
              <label
                key={opt.value}
                className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-xs font-medium transition-all ${
                  value === opt.value
                    ? 'border-teal-600 bg-teal-50 text-teal-900 font-bold ring-1 ring-teal-500'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                } ${isReadOnly ? 'pointer-events-none opacity-80' : ''}`}
              >
                <input
                  type="radio"
                  name={field.name}
                  value={opt.value}
                  checked={value === opt.value}
                  disabled={isReadOnly}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  className="text-teal-600 focus:ring-teal-500"
                />
                <span>{opt.label}</span>
              </label>
            ))}
          </div>
        )}

        {/* 8. Checkbox */}
        {field.type === 'checkbox' && (
          <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50/50 cursor-pointer mt-1">
            <input
              type="checkbox"
              checked={!!value}
              disabled={isReadOnly}
              required={field.required}
              onChange={(e) => handleFieldChange(field.name, e.target.checked)}
              className="w-4 h-4 rounded text-teal-600 focus:ring-teal-500 mt-0.5"
            />
            <span className="text-xs text-slate-700 font-medium leading-relaxed">
              {field.label}
            </span>
          </label>
        )}

        {/* 9. Textarea */}
        {field.type === 'textarea' && (
          <textarea
            rows={4}
            value={value}
            disabled={isReadOnly}
            required={field.required}
            placeholder={field.placeholder}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-100 disabled:text-slate-500"
          />
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Step Stepper Header */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between gap-2 overflow-x-auto pb-2 sm:pb-0 scrollbar-none">
          {sections.map((section, idx) => {
            const isCompleted = idx < activeSectionIndex;
            const isCurrent = idx === activeSectionIndex;

            return (
              <button
                key={section.id}
                type="button"
                onClick={() => setActiveSectionIndex(idx)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  isCurrent
                    ? 'bg-teal-700 text-white shadow-sm'
                    : isCompleted
                    ? 'bg-teal-50 text-teal-800 hover:bg-teal-100'
                    : 'bg-slate-50 text-slate-500 hover:bg-slate-100'
                }`}
              >
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                    isCurrent
                      ? 'bg-white text-teal-800'
                      : isCompleted
                      ? 'bg-teal-200 text-teal-900'
                      : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {idx + 1}
                </span>
                <span>{section.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Section Form Fields */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div className="border-b border-slate-100 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
              Section {activeSectionIndex + 1} of {sections.length}
            </span>
            <h3 className="text-base font-bold text-slate-900 mt-1">
              {currentSection.title}
            </h3>
            {currentSection.description && (
              <p className="text-xs text-slate-500 mt-0.5">
                {currentSection.description}
              </p>
            )}
          </div>

          {!isReadOnly && (
            <button
              type="button"
              onClick={handleManualSave}
              disabled={saving}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                saveSuccess
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-700'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              {saveSuccess ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Saved!
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5 text-slate-500" />
                  {saving ? 'Saving...' : 'Save Draft'}
                </>
              )}
            </button>
          )}
        </div>

        <div className="space-y-4">
          {currentSection.fields.map((field) => renderField(field))}
        </div>

        {/* Section Navigation Buttons */}
        <div className="pt-6 border-t border-slate-100 flex items-center justify-between">
          <button
            type="button"
            disabled={activeSectionIndex === 0}
            onClick={() => setActiveSectionIndex((prev) => Math.max(0, prev - 1))}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous Section
          </button>

          {activeSectionIndex < sections.length - 1 ? (
            <button
              type="button"
              onClick={() =>
                setActiveSectionIndex((prev) =>
                  Math.min(sections.length - 1, prev + 1)
                )
              }
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-all shadow-sm"
            >
              Next Section
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <div className="text-xs text-slate-500 flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              All sections completed. Proceed to Document Upload.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
