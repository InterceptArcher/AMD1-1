'use client';

import { useState, useEffect, FormEvent } from 'react';

interface EmailFormProps {
  onSubmit: (data: {
    email: string;
    name?: string;
    company: string;
    role: string;
    modernization_stage: string;
    ai_priority: string;
  }) => void;
}

export default function EmailForm({ onSubmit }: EmailFormProps) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [modernizationStage, setModernizationStage] = useState('');
  const [aiPriority, setAiPriority] = useState('');
  const [consent, setConsent] = useState(false);
  const [isValid, setIsValid] = useState(false);

  // Email validation regex
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  useEffect(() => {
    // Validate form: all required fields must be filled
    const emailValid = emailRegex.test(email);
    const allFieldsFilled = company && role && modernizationStage && aiPriority;
    setIsValid(emailValid && consent && !!allFieldsFilled);
  }, [email, consent, company, role, modernizationStage, aiPriority]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!isValid) return;

    onSubmit({
      email,
      name: name || undefined,
      company,
      role,
      modernization_stage: modernizationStage,
      ai_priority: aiPriority,
    });
  };

  const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    fontSize: '1rem',
    boxSizing: 'border-box' as const,
  };

  const labelStyle = {
    display: 'block',
    marginBottom: '0.5rem',
    fontWeight: '600',
    color: '#374151',
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        padding: '2rem',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        backgroundColor: 'white',
      }}
    >
      {/* Company */}
      <div style={{ textAlign: 'left' }}>
        <label htmlFor="company" style={labelStyle}>
          Company
        </label>
        <input
          id="company"
          type="text"
          data-testid="company-input"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          required
          maxLength={60}
          placeholder="Enter your company name"
          style={inputStyle}
        />
      </div>

      {/* Role */}
      <div style={{ textAlign: 'left' }}>
        <label htmlFor="role" style={labelStyle}>
          Role
        </label>
        <select
          id="role"
          data-testid="role-select"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          required
          style={inputStyle}
        >
          <option value="">Select your role</option>
          <option value="Business Leader">Business Leader / Executive</option>
          <option value="IT">IT / Technical</option>
          <option value="Finance">Finance</option>
          <option value="Operations">Operations</option>
          <option value="Security">Security</option>
        </select>
      </div>

      {/* Modernization Stage */}
      <div style={{ textAlign: 'left' }}>
        <label htmlFor="modernization_stage" style={labelStyle}>
          Modernization Stage
        </label>
        <select
          id="modernization_stage"
          data-testid="modernization-stage-select"
          value={modernizationStage}
          onChange={(e) => setModernizationStage(e.target.value)}
          required
          style={inputStyle}
        >
          <option value="">Select your stage</option>
          <option value="awareness">Exploring & Learning (Early Stage)</option>
          <option value="evaluation">Evaluating & Comparing (Mid Stage)</option>
          <option value="decision">Ready to Implement (Late Stage)</option>
        </select>
      </div>

      {/* AI Priority */}
      <div style={{ textAlign: 'left' }}>
        <label htmlFor="ai_priority" style={labelStyle}>
          AI Priority
        </label>
        <select
          id="ai_priority"
          data-testid="ai-priority-select"
          value={aiPriority}
          onChange={(e) => setAiPriority(e.target.value)}
          required
          style={inputStyle}
        >
          <option value="">Select your AI focus</option>
          <option value="Infrastructure Modernization">Infrastructure Modernization</option>
          <option value="AI/ML Workloads">AI/ML Workloads</option>
          <option value="Cloud Migration">Cloud Migration</option>
          <option value="Data Center Optimization">Data Center Optimization</option>
          <option value="Performance & Scalability">Performance & Scalability</option>
          <option value="Cost Optimization">Cost Optimization</option>
        </select>
      </div>

      {/* Email */}
      <div style={{ textAlign: 'left' }}>
        <label htmlFor="email" style={labelStyle}>
          Work Email Address
        </label>
        <input
          id="email"
          type="email"
          data-testid="email-input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={100}
          pattern="[^\s@]+@[^\s@]+\.[^\s@]+"
          placeholder="your.email@company.com"
          style={inputStyle}
        />
      </div>

      {/* Name (Optional) */}
      <div style={{ textAlign: 'left' }}>
        <label htmlFor="name" style={labelStyle}>
          Name <span style={{ fontWeight: '400', color: '#6b7280' }}>(optional)</span>
        </label>
        <input
          id="name"
          type="text"
          data-testid="name-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={50}
          placeholder="John Smith"
          style={inputStyle}
        />
      </div>

      {/* Consent */}
      <div style={{ textAlign: 'left' }}>
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            cursor: 'pointer',
          }}
        >
          <input
            type="checkbox"
            data-testid="consent-checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            required
            style={{
              width: '1.25rem',
              height: '1.25rem',
              cursor: 'pointer',
            }}
          />
          <span style={{ color: '#374151' }}>
            I consent to receiving communications and agree to the terms
          </span>
        </label>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        data-testid="submit-button"
        disabled={!isValid}
        style={{
          padding: '0.75rem 1.5rem',
          backgroundColor: isValid ? '#DC2626' : '#9ca3af',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          fontSize: '1rem',
          fontWeight: '600',
          cursor: isValid ? 'pointer' : 'not-allowed',
          transition: 'background-color 0.2s',
        }}
      >
        Get Personalized Content
      </button>
    </form>
  );
}
