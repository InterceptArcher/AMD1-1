'use client';

import { WizardData, ROLE_OPTIONS } from '../wizardTypes';
import SelectionCard from '../SelectionCard';

interface StepRoleProps {
  data: WizardData;
  onChange: (updates: Partial<WizardData>) => void;
  onAutoAdvance?: () => void;
  suggestedRole?: string;
  disabled?: boolean;
}

export default function StepRole({ data, onChange, onAutoAdvance, suggestedRole, disabled = false }: StepRoleProps) {
  const handleSelect = (value: string) => {
    onChange({ persona: value });
    // Auto-advance after brief delay so the user sees their selection
    if (onAutoAdvance) {
      setTimeout(() => onAutoAdvance(), 500);
    }
  };

  return (
    <div>
      <label className="amd-label">Select the role that best describes you</label>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {ROLE_OPTIONS.map((opt) => (
          <SelectionCard
            key={opt.value}
            label={opt.label}
            description={opt.description}
            selected={data.persona === opt.value}
            onClick={() => handleSelect(opt.value)}
            disabled={disabled}
            size="md"
          />
        ))}
      </div>
      {suggestedRole && data.persona === suggestedRole && (
        <p className="social-proof-enter text-[11px] text-[#00c8aa]/60 mt-2 pl-1">
          Suggested from your profile — change anytime
        </p>
      )}
    </div>
  );
}
