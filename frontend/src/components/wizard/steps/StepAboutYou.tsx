'use client';

import { ChangeEvent, useState } from 'react';
import { WizardData, extractCompanyFromEmail } from '../wizardTypes';

interface StepAboutYouProps {
  data: WizardData;
  onChange: (updates: Partial<WizardData>) => void;
  onCompanySuggested?: (name: string) => void;
  disabled?: boolean;
}

export default function StepAboutYou({ data, onChange, onCompanySuggested, disabled = false }: StepAboutYouProps) {
  const [emailTouched, setEmailTouched] = useState(false);

  const validateEmail = (value: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value);
  };

  const emailError = emailTouched && data.email.length > 0 && !validateEmail(data.email)
    ? 'Please enter a valid email address'
    : null;

  const handleEmailBlur = () => {
    setEmailTouched(true);
    // Extract company name from work email domain
    if (data.email && validateEmail(data.email) && !data.company) {
      const suggested = extractCompanyFromEmail(data.email);
      if (suggested) {
        onChange({ company: suggested });
        onCompanySuggested?.(suggested);
      }
    }
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="wiz-firstName" className="amd-label">
            First Name
          </label>
          <input
            type="text"
            id="wiz-firstName"
            placeholder="John"
            value={data.firstName}
            onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ firstName: e.target.value })}
            disabled={disabled}
            maxLength={50}
            className="amd-input"
          />
        </div>
        <div>
          <label htmlFor="wiz-lastName" className="amd-label">
            Last Name
          </label>
          <input
            type="text"
            id="wiz-lastName"
            placeholder="Smith"
            value={data.lastName}
            onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ lastName: e.target.value })}
            disabled={disabled}
            maxLength={50}
            className="amd-input"
          />
        </div>
      </div>

      <div>
        <label htmlFor="wiz-email" className="amd-label">
          Work Email
        </label>
        <input
          type="email"
          id="wiz-email"
          placeholder="you@company.com"
          value={data.email}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ email: e.target.value })}
          onBlur={handleEmailBlur}
          disabled={disabled}
          maxLength={100}
          className={`amd-input ${emailError ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/50' : ''}`}
        />
        {emailError && (
          <p className="mt-2 text-sm text-red-400 font-medium">{emailError}</p>
        )}
      </div>
    </div>
  );
}
