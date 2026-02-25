'use client';

import { WizardData, INDUSTRY_OPTIONS, ROLE_OPTIONS, STAGE_LABELS } from './wizardTypes';

interface LivePreviewCardProps {
  data: WizardData;
}

export default function LivePreviewCard({ data }: LivePreviewCardProps) {
  const lines: string[] = [];

  const industryLabel = INDUSTRY_OPTIONS.find((i) => i.value === data.industry)?.label;
  const roleLabel = ROLE_OPTIONS.find((r) => r.value === data.persona)?.label;
  const stageLabel = STAGE_LABELS[data.itEnvironment];

  if (data.company && industryLabel) {
    lines.push(`AI readiness assessment for a ${industryLabel.toLowerCase()} enterprise`);
  } else if (data.company) {
    lines.push(`AI readiness assessment for ${data.company}`);
  } else if (industryLabel) {
    lines.push(`AI readiness assessment for ${industryLabel.toLowerCase()}`);
  }

  if (roleLabel) {
    lines.push(`Tailored for ${roleLabel} perspective`);
  }

  if (stageLabel) {
    lines.push(`Starting from ${stageLabel} infrastructure`);
  }

  // Don't show if nothing to display
  if (lines.length === 0) return null;

  return (
    <div className="progressive-reveal mt-4 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00c8aa] opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00c8aa]" />
        </span>
        <span className="text-[11px] text-white/40 uppercase tracking-widest font-semibold">
          Building your assessment
        </span>
      </div>
      <ul className="space-y-1">
        {lines.map((line, i) => (
          <li key={i} className="text-xs text-white/50 flex items-center gap-2">
            <svg className="w-3 h-3 text-[#00c8aa]/60 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            {line}
          </li>
        ))}
      </ul>
    </div>
  );
}
