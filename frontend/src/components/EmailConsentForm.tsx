'use client';

import { useState, FormEvent, ChangeEvent } from 'react';

export interface UserInputs {
  email: string;
  goal: string;
}

interface EmailConsentFormProps {
  onSubmit: (inputs: UserInputs) => void;
  isLoading?: boolean;
}

// Buying stage options (optional)
const GOAL_OPTIONS = [
  { value: '', label: 'Select your current stage (optional)' },
  { value: 'awareness', label: 'Just starting to research' },
  { value: 'consideration', label: 'Actively evaluating options' },
  { value: 'decision', label: 'Ready to make a decision' },
  { value: 'implementation', label: 'Already implementing, need guidance' },
];

export default function EmailConsentForm({ onSubmit, isLoading = false }: EmailConsentFormProps) {
  const [email, setEmail] = useState('');
  const [goal, setGoal] = useState('');
  const [consent, setConsent] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const validateEmail = (value: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value);
  };

  const handleEmailChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEmail(value);
    if (touched && value && !validateEmail(value)) {
      setEmailError('Please enter a valid work email address');
    } else {
      setEmailError(null);
    }
  };

  const handleEmailBlur = () => {
    setTouched(true);
    if (email && !validateEmail(email)) {
      setEmailError('Please enter a valid work email address');
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isFormValid) {
      onSubmit({ email, goal });
    }
  };

  const isEmailValid = email.length > 0 && validateEmail(email);
  const isFormValid = isEmailValid && consent;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Work Email */}
      <div>
        <label htmlFor="email" className="amd-label">
          Work Email
        </label>
        <input
          type="email"
          id="email"
          name="email"
          placeholder="you@company.com"
          value={email}
          onChange={handleEmailChange}
          onBlur={handleEmailBlur}
          disabled={isLoading}
          maxLength={100}
          className={`amd-input ${emailError ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/50' : ''}`}
        />
        {emailError && (
          <p className="mt-2 text-sm text-red-400 font-medium">{emailError}</p>
        )}
        <p className="mt-2 text-xs text-white/40">
          We&apos;ll use your email to find and personalize insights for your company
        </p>
      </div>

      {/* Journey Stage (Optional) */}
      <div>
        <label htmlFor="goal" className="amd-label">
          Where are you in your journey?
          <span className="text-white/40 font-normal ml-1">(optional)</span>
        </label>
        <select
          id="goal"
          name="goal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          disabled={isLoading}
          className="amd-select"
        >
          {GOAL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Consent Checkbox */}
      <div className="flex items-start gap-3 pt-3">
        <input
          type="checkbox"
          id="consent"
          name="consent"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          disabled={isLoading}
          className="amd-checkbox mt-0.5"
        />
        <label htmlFor="consent" className="text-sm text-white/70 leading-relaxed cursor-pointer">
          I agree to receive my personalized assessment and relevant updates from AMD
        </label>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={!isFormValid || isLoading}
        className="amd-button-primary mt-6"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-3">
            <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            Analyzing Your Company...
          </span>
        ) : (
          'Get My Personalized Assessment →'
        )}
      </button>

      {/* Info text */}
      <p className="text-center text-sm text-white/50 pt-3">
        Powered by AI-driven company enrichment
      </p>
    </form>
  );
}
