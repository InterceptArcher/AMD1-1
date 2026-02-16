'use client';

import { ChangeEvent } from 'react';
import { WizardData, COMPANY_SIZE_OPTIONS, INDUSTRY_OPTIONS } from '../wizardTypes';
import SelectionCard from '../SelectionCard';

interface StepCompanyProps {
  data: WizardData;
  onChange: (updates: Partial<WizardData>) => void;
  companyAutoFilled?: boolean;
  disabled?: boolean;
}

export default function StepCompany({ data, onChange, companyAutoFilled = false, disabled = false }: StepCompanyProps) {
  return (
    <div className="space-y-6">
      {/* Company detected banner */}
      {companyAutoFilled && data.company && (
        <div className="company-detected flex items-center gap-2 px-4 py-2.5 rounded-lg border border-[#00c8aa]/25 bg-[#00c8aa]/[0.06]">
          <svg className="w-4 h-4 text-[#00c8aa] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs text-white/60">
            Detected <strong className="text-white/80">{data.company}</strong> from your email — feel free to edit
          </span>
        </div>
      )}

      {/* Company name */}
      <div>
        <label htmlFor="wiz-company" className="amd-label">
          Company
        </label>
        <input
          type="text"
          id="wiz-company"
          placeholder="Acme Corp"
          value={data.company}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ company: e.target.value })}
          disabled={disabled}
          maxLength={60}
          className="amd-input"
        />
      </div>

      {/* Company size cards */}
      <div>
        <label className="amd-label">Company Size</label>
        <div className="grid grid-cols-3 gap-3">
          {COMPANY_SIZE_OPTIONS.map((opt) => (
            <SelectionCard
              key={opt.value}
              label={opt.label}
              description={opt.description}
              selected={data.companySize === opt.value}
              onClick={() => onChange({ companySize: opt.value })}
              disabled={disabled}
              size="md"
            />
          ))}
        </div>
      </div>

      {/* Industry tiles */}
      <div>
        <label className="amd-label">Industry</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {INDUSTRY_OPTIONS.map((opt) => (
            <SelectionCard
              key={opt.value}
              label={opt.label}
              selected={data.industry === opt.value}
              onClick={() => onChange({ industry: opt.value })}
              disabled={disabled}
              size="sm"
            />
          ))}
        </div>
      </div>
    </div>
  );
}
