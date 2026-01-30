'use client';

import { useState, FormEvent, ChangeEvent } from 'react';

export interface UserInputs {
  email: string;
  firstName: string;
  lastName: string;
  goal: string;
  persona: string;
  industry: string;
}

interface EmailConsentFormProps {
  onSubmit: (inputs: UserInputs) => void;
  isLoading?: boolean;
}

const GOAL_OPTIONS = [
  { value: '', label: 'Select your primary goal...' },
  { value: 'exploring', label: 'Exploring modernization options' },
  { value: 'evaluating', label: 'Comparing approaches for my organization' },
  { value: 'learning', label: 'Understanding best practices and trends' },
  { value: 'building_case', label: 'Building a business case internally' },
];

const PERSONA_OPTIONS = [
  { value: '', label: 'Select your role...' },
  { value: 'executive', label: 'Executive Leadership (C-suite, VP)' },
  { value: 'it_infrastructure', label: 'IT / Infrastructure' },
  { value: 'security', label: 'Security' },
  { value: 'data_ai', label: 'Data / AI / Engineering' },
  { value: 'sales_gtm', label: 'Sales / GTM / Revenue Ops' },
  { value: 'hr_people', label: 'HR / People Ops' },
  { value: 'other', label: 'Other' },
];

const INDUSTRY_OPTIONS = [
  { value: '', label: 'Select your industry...' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'financial_services', label: 'Financial Services' },
  { value: 'technology', label: 'Technology / SaaS' },
  { value: 'gaming_media', label: 'Gaming / Media' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'retail', label: 'Retail / Consumer' },
  { value: 'government', label: 'Government / Public Sector' },
  { value: 'energy', label: 'Energy / Utilities' },
  { value: 'telecommunications', label: 'Telecommunications' },
  { value: 'other', label: 'Other' },
];

export default function EmailConsentForm({ onSubmit, isLoading = false }: EmailConsentFormProps) {
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
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

  const handleConsentChange = (e: ChangeEvent<HTMLInputElement>) => {
    setConsent(e.target.checked);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isFormValid) {
      onSubmit({ email, firstName, lastName, goal, persona, industry });
    }
  };

  const isEmailValid = email.length > 0 && validateEmail(email);
  const isNameValid = firstName.length > 0 && lastName.length > 0;
  const isFormValid = isEmailValid && isNameValid && consent && goal && persona && industry;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Name Inputs */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label
            htmlFor="firstName"
            className="block text-sm font-medium text-gray-700"
          >
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
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>
        <div>
          <label
            htmlFor="lastName"
            className="block text-sm font-medium text-gray-700"
          >
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
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>
      </div>

      {/* Email Input */}
      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-gray-700"
        >
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
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          aria-describedby={emailError ? 'email-error' : undefined}
        />
        {emailError && (
          <p id="email-error" className="mt-1 text-sm text-red-600">
            {emailError}
          </p>
        )}
      </div>

      {/* Primary Goal Dropdown */}
      <div>
        <label
          htmlFor="goal"
          className="block text-sm font-medium text-gray-700"
        >
          What brings you here today?
        </label>
        <select
          id="goal"
          name="goal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          {GOAL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Persona/Role Dropdown */}
      <div>
        <label
          htmlFor="persona"
          className="block text-sm font-medium text-gray-700"
        >
          What best describes your role?
        </label>
        <select
          id="persona"
          name="persona"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          {PERSONA_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Industry Dropdown */}
      <div>
        <label
          htmlFor="industry"
          className="block text-sm font-medium text-gray-700"
        >
          What industry is your organization in?
        </label>
        <select
          id="industry"
          name="industry"
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          {INDUSTRY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Consent Checkbox */}
      <div className="flex items-start">
        <input
          type="checkbox"
          id="consent"
          name="consent"
          checked={consent}
          onChange={handleConsentChange}
          disabled={isLoading}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed mt-0.5"
        />
        <label
          htmlFor="consent"
          className="ml-2 block text-sm text-gray-600"
        >
          I agree to receive my personalized ebook and relevant updates
        </label>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={!isFormValid || isLoading}
        className="w-full rounded-md bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
            Creating Your Personalized Ebook...
          </span>
        ) : (
          'Get My Free Ebook'
        )}
      </button>

      <p className="text-center text-xs text-gray-400">
        We'll send your customized ebook to your email
      </p>
    </form>
  );
}
