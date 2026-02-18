'use client';

import { ChangeEvent } from 'react';
import { WizardData, COMPANY_SIZE_OPTIONS, INDUSTRY_OPTIONS, EnrichmentPreview } from '../wizardTypes';
import SelectionCard from '../SelectionCard';

interface StepCompanyProps {
  data: WizardData;
  onChange: (updates: Partial<WizardData>) => void;
  companyAutoFilled?: boolean;
  enrichmentData?: EnrichmentPreview | null;
  enrichmentLoading?: boolean;
  disabled?: boolean;
}

export default function StepCompany({
  data,
  onChange,
  companyAutoFilled = false,
  enrichmentData = null,
  enrichmentLoading = false,
  disabled = false,
}: StepCompanyProps) {
  return (
    <div className="space-y-6">
      {/* Enrichment found banner — richer than simple domain detection */}
      {enrichmentData && (
        <div className="company-detected flex items-start gap-3 px-4 py-3 rounded-lg border border-[#00c8aa]/25 bg-[#00c8aa]/[0.06]">
          <div className="w-8 h-8 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg className="w-4 h-4 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-sm text-white/80 font-medium">
              We found <strong className="text-white">{enrichmentData.company_name}</strong>
              {enrichmentData.title && (
                <span className="text-white/50"> — {enrichmentData.title}</span>
              )}
            </p>
            {(enrichmentData.employee_count || enrichmentData.industry) && (
              <div className="flex flex-wrap gap-2 mt-1.5">
                {enrichmentData.employee_count && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/40">
                    {enrichmentData.employee_count.toLocaleString()} employees
                  </span>
                )}
                {enrichmentData.industry && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/40">
                    {enrichmentData.industry}
                  </span>
                )}
                {enrichmentData.founded_year && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/40">
                    Founded {enrichmentData.founded_year}
                  </span>
                )}
              </div>
            )}
            <p className="text-[11px] text-white/30 mt-1">Fields pre-filled — feel free to edit</p>
          </div>
        </div>
      )}

      {/* Simple domain detection banner (only when no richer enrichment data) */}
      {!enrichmentData && companyAutoFilled && data.company && (
        <div className="company-detected flex items-center gap-2 px-4 py-2.5 rounded-lg border border-[#00c8aa]/25 bg-[#00c8aa]/[0.06]">
          <svg className="w-4 h-4 text-[#00c8aa] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs text-white/60">
            Detected <strong className="text-white/80">{data.company}</strong> from your email — feel free to edit
          </span>
        </div>
      )}

      {/* Enrichment loading indicator */}
      {enrichmentLoading && !enrichmentData && (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-white/[0.03]">
          <div className="w-3.5 h-3.5 border-2 border-[#00c8aa]/40 border-t-[#00c8aa] rounded-full animate-spin" />
          <span className="text-xs text-white/40">Looking up your company...</span>
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
