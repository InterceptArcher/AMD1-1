'use client';

import { useState, FormEvent, ChangeEvent } from 'react';

export interface UserInputs {
  email: string;
  firstName: string;
  lastName: string;
  company: string;
  companySize: string;
  goal: string;
  persona: string;
  industry: string;
}

interface EmailConsentFormProps {
  onSubmit: (inputs: UserInputs) => void;
  isLoading?: boolean;
}

// Buying stage options
const GOAL_OPTIONS = [
  { value: '', label: 'Select your current stage...' },
  { value: 'awareness', label: 'Just starting to research' },
  { value: 'consideration', label: 'Actively evaluating options' },
  { value: 'decision', label: 'Ready to make a decision' },
  { value: 'implementation', label: 'Already implementing, need guidance' },
];

// Grouped role options - Technical vs Business, then by seniority
const ROLE_GROUPS = [
  {
    label: 'Technical Executive',
    options: [
      { value: 'cto', label: 'CTO' },
      { value: 'cio', label: 'CIO' },
      { value: 'ciso', label: 'CISO' },
      { value: 'cdo', label: 'Chief Data Officer' },
    ],
  },
  {
    label: 'Business Executive',
    options: [
      { value: 'ceo', label: 'CEO' },
      { value: 'coo', label: 'COO' },
      { value: 'cfo', label: 'CFO' },
      { value: 'c_suite_other', label: 'Other C-Suite' },
    ],
  },
  {
    label: 'Technical Leadership',
    options: [
      { value: 'vp_engineering', label: 'VP Engineering' },
      { value: 'vp_it', label: 'VP IT' },
      { value: 'vp_data', label: 'VP Data or AI' },
      { value: 'vp_security', label: 'VP Security' },
    ],
  },
  {
    label: 'Business Leadership',
    options: [
      { value: 'vp_ops', label: 'VP Operations' },
      { value: 'vp_finance', label: 'VP Finance' },
    ],
  },
  {
    label: 'Technical Manager',
    options: [
      { value: 'eng_manager', label: 'Engineering Manager' },
      { value: 'it_manager', label: 'IT Manager' },
      { value: 'data_manager', label: 'Data Science Manager' },
      { value: 'security_manager', label: 'Security Manager' },
    ],
  },
  {
    label: 'Technical Individual',
    options: [
      { value: 'senior_engineer', label: 'Senior Engineer or Architect' },
      { value: 'engineer', label: 'Engineer' },
      { value: 'sysadmin', label: 'Systems Administrator' },
    ],
  },
  {
    label: 'Business Role',
    options: [
      { value: 'ops_manager', label: 'Operations Manager' },
      { value: 'finance_manager', label: 'Finance Manager' },
      { value: 'procurement', label: 'Procurement' },
    ],
  },
  {
    label: 'Other',
    options: [
      { value: 'other', label: 'Other' },
    ],
  },
];

// Company size options
const COMPANY_SIZE_OPTIONS = [
  { value: '', label: 'Select company size...' },
  { value: 'startup', label: 'Startup (1-50 employees)' },
  { value: 'small', label: 'Small Business (51-200)' },
  { value: 'midmarket', label: 'Mid-Market (201-1,000)' },
  { value: 'enterprise', label: 'Enterprise (1,001-10,000)' },
  { value: 'large_enterprise', label: 'Large Enterprise (10,000+)' },
];

// Industry options aligned with case study mapping
const INDUSTRY_OPTIONS = [
  { value: '', label: 'Select your industry...' },
  { value: 'technology', label: 'Technology' },
  { value: 'financial_services', label: 'Financial Services' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'retail', label: 'Retail' },
  { value: 'energy', label: 'Energy' },
  { value: 'telecommunications', label: 'Telecommunications' },
  { value: 'media', label: 'Media' },
  { value: 'government', label: 'Government' },
  { value: 'education', label: 'Education' },
  { value: 'professional_services', label: 'Professional Services' },
  { value: 'other', label: 'Other' },
];

export default function EmailConsentForm({ onSubmit, isLoading = false }: EmailConsentFormProps) {
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [company, setCompany] = useState('');
  const [companySize, setCompanySize] = useState('');
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
      onSubmit({ email, firstName, lastName, company, companySize, goal, persona, industry });
    }
  };

  const isEmailValid = email.length > 0 && validateEmail(email);
  const isNameValid = firstName.length > 0 && lastName.length > 0;
  const isCompanyValid = company.length > 0;
  const isFormValid = isEmailValid && isNameValid && isCompanyValid && companySize && consent && goal && persona && industry;

  // Get display label for selected role
  const getSelectedRoleLabel = () => {
    for (const group of ROLE_GROUPS) {
      const found = group.options.find(opt => opt.value === persona);
      if (found) return found.label.split(' / ')[0];
    }
    return 'your role';
  };

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
            maxLength={50}
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
            maxLength={50}
            className="amd-input"
          />
        </div>
      </div>

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
      </div>

      {/* Company + Size Row */}
      <div className="grid grid-cols-2 gap-4">
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
            maxLength={60}
            className="amd-input"
          />
        </div>
        <div>
          <label htmlFor="companySize" className="amd-label">
            Company Size
          </label>
          <select
            id="companySize"
            name="companySize"
            value={companySize}
            onChange={(e) => setCompanySize(e.target.value)}
            disabled={isLoading}
            className="amd-select"
          >
            {COMPANY_SIZE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
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

      {/* Role Dropdown with optgroups */}
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
          <option value="">Select your role...</option>
          {ROLE_GROUPS.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </optgroup>
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
      <p className="text-center text-sm text-white/50 pt-3">
        Personalized for{' '}
        <span className="text-white/70 font-medium">{getSelectedRoleLabel()}</span>
        {' '}at{' '}
        <span className="text-white/70 font-medium">{company || 'your company'}</span>
      </p>
    </form>
  );
}
