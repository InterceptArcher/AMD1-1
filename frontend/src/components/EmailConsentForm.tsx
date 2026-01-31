'use client';

import { useState, FormEvent, ChangeEvent } from 'react';

export interface UserInputs {
  email: string;
  firstName: string;
  lastName: string;
  company: string;
  goal: string;
  persona: string;
  industry: string;
}

interface EmailConsentFormProps {
  onSubmit: (inputs: UserInputs) => void;
  isLoading?: boolean;
}

const GOAL_OPTIONS = [
  { value: '', label: 'Select your current stage...' },
  { value: 'awareness', label: 'Just starting to research' },
  { value: 'consideration', label: 'Actively evaluating options' },
  { value: 'decision', label: 'Ready to make a decision' },
  { value: 'implementation', label: 'Already implementing, need guidance' },
];

const PERSONA_OPTIONS = [
  { value: '', label: 'Select your role...' },
  { value: 'c_suite', label: 'C-Suite / Executive' },
  { value: 'vp_director', label: 'VP / Director' },
  { value: 'it_infrastructure', label: 'IT / Infrastructure Manager' },
  { value: 'engineering', label: 'Engineering / DevOps' },
  { value: 'data_ai', label: 'Data Science / AI / ML' },
  { value: 'security', label: 'Security / Compliance' },
  { value: 'procurement', label: 'Procurement / Vendor Management' },
  { value: 'other', label: 'Other' },
];

const INDUSTRY_OPTIONS = [
  { value: '', label: 'Select your industry...' },
  { value: 'technology', label: 'Technology / Software' },
  { value: 'financial_services', label: 'Financial Services / Banking' },
  { value: 'healthcare', label: 'Healthcare / Life Sciences' },
  { value: 'retail_ecommerce', label: 'Retail / E-commerce' },
  { value: 'manufacturing', label: 'Manufacturing / Industrial' },
  { value: 'telecommunications', label: 'Telecommunications / Media' },
  { value: 'energy_utilities', label: 'Energy / Utilities' },
  { value: 'government', label: 'Government / Public Sector' },
  { value: 'education', label: 'Education / Research' },
  { value: 'professional_services', label: 'Professional Services' },
  { value: 'other', label: 'Other' },
];

export default function EmailConsentForm({ onSubmit, isLoading = false }: EmailConsentFormProps) {
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [company, setCompany] = useState('');
  const [goal, setGoal] = useState('');
  const [persona, setPersona] = useState('');
  const [industry, setIndustry] = useState('');
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
      setEmailError('Please enter a valid email address');
    } else {
      setEmailError(null);
    }
  };

  const handleEmailBlur = () => {
    setTouched(true);
    if (email && !validateEmail(email)) {
      setEmailError('Please enter a valid email address');
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isFormValid) {
      onSubmit({ email, firstName, lastName, company, goal, persona, industry });
    }
  };

  const isEmailValid = email.length > 0 && validateEmail(email);
  const isNameValid = firstName.length > 0 && lastName.length > 0;
  const isCompanyValid = company.length > 0;
  const isFormValid = isEmailValid && isNameValid && isCompanyValid && consent && goal && persona && industry;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Name Inputs */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="firstName" className="amd-label">
            First Name
          </label>
          <input
            type="text"
            id="firstName"
            name="firstName"
            placeholder="John"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            disabled={isLoading}
            className="amd-input"
          />
        </div>
        <div>
          <label htmlFor="lastName" className="amd-label">
            Last Name
          </label>
          <input
            type="text"
            id="lastName"
            name="lastName"
            placeholder="Smith"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            disabled={isLoading}
            className="amd-input"
          />
        </div>
      </div>

      {/* Company Input */}
      <div>
        <label htmlFor="company" className="amd-label">
          Company
        </label>
        <input
          type="text"
          id="company"
          name="company"
          placeholder="Acme Corp"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          disabled={isLoading}
          className="amd-input"
        />
      </div>

      {/* Email Input */}
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
          className={`amd-input ${emailError ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/50' : ''}`}
        />
        {emailError && (
          <p className="mt-2 text-sm text-red-400">{emailError}</p>
        )}
      </div>

      {/* Industry Dropdown */}
      <div>
        <label htmlFor="industry" className="amd-label">
          Industry
        </label>
        <select
          id="industry"
          name="industry"
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          disabled={isLoading}
          className="amd-select"
        >
          {INDUSTRY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Persona/Role Dropdown */}
      <div>
        <label htmlFor="persona" className="amd-label">
          Your Role
        </label>
        <select
          id="persona"
          name="persona"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          disabled={isLoading}
          className="amd-select"
        >
          {PERSONA_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Buying Stage Dropdown */}
      <div>
        <label htmlFor="goal" className="amd-label">
          Where are you in your journey?
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
      <div className="flex items-start gap-3 pt-2">
        <input
          type="checkbox"
          id="consent"
          name="consent"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          disabled={isLoading}
          className="amd-checkbox mt-0.5"
        />
        <label htmlFor="consent" className="text-sm text-white/50 leading-relaxed cursor-pointer">
          I agree to receive my personalized ebook and relevant updates from AMD
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
            Creating Your Ebook...
          </span>
        ) : (
          'Get My Free Ebook →'
        )}
      </button>

      {/* Preview text */}
      <p className="text-center text-xs text-white/30 pt-2">
        Personalized for {company || 'your company'} in {
          INDUSTRY_OPTIONS.find(i => i.value === industry)?.label.split(' /')[0] || 'your industry'
        }
      </p>
    </form>
  );
}
