'use client';

import { useState, useEffect } from 'react';

interface UserContext {
  firstName?: string;
  company?: string;
  industry?: string;
  persona?: string;
  goal?: string;
}

interface LoadingSpinnerProps {
  message?: string;
  userContext?: UserContext;
}

// Industry-specific loading messages
const INDUSTRY_MESSAGES: Record<string, string[]> = {
  technology: [
    'Analyzing tech industry trends...',
    'Finding relevant SaaS case studies...',
    'Tailoring content for software leaders...',
  ],
  financial_services: [
    'Reviewing financial services benchmarks...',
    'Adding compliance considerations...',
    'Customizing for banking & insurance...',
  ],
  healthcare: [
    'Incorporating healthcare regulations...',
    'Finding life sciences case studies...',
    'Tailoring for patient data requirements...',
  ],
  retail_ecommerce: [
    'Analyzing retail transformation trends...',
    'Adding e-commerce scalability insights...',
    'Customizing for customer experience...',
  ],
  manufacturing: [
    'Reviewing industrial automation trends...',
    'Adding supply chain considerations...',
    'Tailoring for operational efficiency...',
  ],
  telecommunications: [
    'Analyzing network infrastructure trends...',
    'Adding media delivery insights...',
    'Customizing for 5G readiness...',
  ],
  energy_utilities: [
    'Reviewing grid modernization trends...',
    'Adding sustainability considerations...',
    'Tailoring for energy efficiency...',
  ],
  government: [
    'Incorporating compliance requirements...',
    'Adding security frameworks...',
    'Customizing for public sector needs...',
  ],
  education: [
    'Analyzing education technology trends...',
    'Adding research computing insights...',
    'Tailoring for academic institutions...',
  ],
  professional_services: [
    'Reviewing consulting best practices...',
    'Adding client delivery insights...',
    'Customizing for service organizations...',
  ],
};

// Role-specific messages
const PERSONA_MESSAGES: Record<string, string> = {
  c_suite: 'Preparing executive-level insights...',
  vp_director: 'Curating strategic recommendations...',
  it_infrastructure: 'Adding technical architecture details...',
  engineering: 'Including implementation patterns...',
  data_ai: 'Incorporating ML/AI workload specifics...',
  security: 'Adding security & compliance frameworks...',
  procurement: 'Including vendor evaluation criteria...',
};

// Buying stage messages
const GOAL_MESSAGES: Record<string, string> = {
  awareness: 'Building your foundational guide...',
  consideration: 'Preparing comparison frameworks...',
  decision: 'Finalizing your decision toolkit...',
  implementation: 'Creating your implementation roadmap...',
};

export default function LoadingSpinner({ message, userContext }: LoadingSpinnerProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [displayMessage, setDisplayMessage] = useState(message || 'Personalizing your content...');

  // Generate personalized loading steps
  const getLoadingSteps = (): string[] => {
    const steps: string[] = [];

    if (userContext?.firstName && userContext?.company) {
      steps.push(`Hi ${userContext.firstName}, preparing your personalized guide for ${userContext.company}...`);
    } else if (userContext?.firstName) {
      steps.push(`Hi ${userContext.firstName}, creating your personalized ebook...`);
    } else {
      steps.push('Creating your personalized ebook...');
    }

    // Enrichment steps
    steps.push('Gathering company intelligence...');
    steps.push('Analyzing recent industry news...');

    // Add industry-specific messages
    if (userContext?.industry && INDUSTRY_MESSAGES[userContext.industry]) {
      steps.push(...INDUSTRY_MESSAGES[userContext.industry]);
    }

    // Add persona-specific message
    if (userContext?.persona && PERSONA_MESSAGES[userContext.persona]) {
      steps.push(PERSONA_MESSAGES[userContext.persona]);
    }

    // Add goal-specific message
    if (userContext?.goal && GOAL_MESSAGES[userContext.goal]) {
      steps.push(GOAL_MESSAGES[userContext.goal]);
    }

    // Final steps
    steps.push('Selecting relevant case studies...');
    steps.push('Generating personalized insights with AI...');
    steps.push('Formatting your custom PDF...');
    steps.push('Finalizing your personalized content...');

    return steps;
  };

  const steps = getLoadingSteps();

  useEffect(() => {
    if (!userContext) {
      setDisplayMessage(message || 'Loading...');
      return;
    }

    // Cycle through personalized messages (pace to show most steps within loading time)
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        const next = (prev + 1) % steps.length;
        setDisplayMessage(steps[next]);
        return next;
      });
    }, 2000);

    // Set initial message
    setDisplayMessage(steps[0]);

    return () => clearInterval(interval);
  }, [userContext, steps.length]);

  // Calculate progress percentage
  const progress = Math.min(((currentStep + 1) / steps.length) * 100, 95);

  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex flex-col items-center justify-center space-y-8 py-12 animate-fade-in-up"
    >
      {/* AMD Branded Header */}
      <div className="text-center">
        {userContext?.firstName ? (
          <>
            <h2 className="text-2xl font-bold text-white mb-3">
              Almost there, <span className="text-[#00c8aa]">{userContext.firstName}</span>!
            </h2>
            {userContext.company && (
              <p className="text-white/70 text-base">
                Customizing insights for <span className="text-white font-medium">{userContext.company}</span>
              </p>
            )}
          </>
        ) : (
          <h2 className="text-2xl font-bold text-white">Generating Your Ebook</h2>
        )}
      </div>

      {/* Animated AMD Logo/Icon */}
      <div className="relative">
        {/* Outer glow ring */}
        <div className="absolute inset-0 rounded-full bg-[#00c8aa]/20 blur-xl animate-pulse" />

        {/* Main spinner container */}
        <div className="relative w-24 h-24 rounded-full border-2 border-white/20 flex items-center justify-center">
          {/* Rotating arc */}
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-[#00c8aa] animate-spin" />
          <div className="absolute inset-2 rounded-full border-2 border-transparent border-r-[#00c8aa]/50 animate-spin [animation-duration:1.5s]" />

          {/* Center icon */}
          <div className="relative z-10 w-12 h-12 rounded-full bg-[#00c8aa]/10 flex items-center justify-center">
            <svg className="w-6 h-6 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Progress card */}
      <div className="w-full max-w-md amd-card p-6">
        <div className="space-y-5">
          {/* Current step indicator */}
          <div className="flex items-center gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center">
              <span className="text-[#00c8aa] font-bold text-sm">{currentStep + 1}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white transition-all duration-500 truncate">
                {displayMessage}
              </p>
              <p className="text-sm text-white/60 mt-1">Processing your personalization...</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="relative h-2.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[#00c8aa] to-[#00e0be] transition-all duration-700 ease-out progress-shine"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Step counter */}
          <div className="flex items-center justify-between text-sm text-white/50">
            <span>Step {currentStep + 1} of {steps.length}</span>
            <span className="font-medium">{Math.round(progress)}% complete</span>
          </div>

          {/* Context tags */}
          {userContext && (
            <div className="pt-5 border-t border-white/10">
              <p className="text-sm text-white/50 mb-3">Personalizing for:</p>
              <div className="flex flex-wrap gap-2">
                {userContext.industry && (
                  <span className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-[#00c8aa]/15 text-[#00c8aa] text-sm font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00c8aa]" />
                    {userContext.industry.replace('_', ' ')}
                  </span>
                )}
                {userContext.persona && (
                  <span className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 text-white/80 text-sm font-medium">
                    {userContext.persona.replace('_', ' ')}
                  </span>
                )}
                {userContext.goal && (
                  <span className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 text-white/80 text-sm font-medium">
                    {userContext.goal.replace('_', ' ')} stage
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preview section */}
      {userContext && (
        <div className="w-full max-w-md space-y-4 animate-fade-in-up stagger-2">
          <p className="text-sm font-semibold text-white/60 text-center uppercase tracking-wider">
            Your ebook will include
          </p>
          <div className="grid grid-cols-3 gap-4">
            <div className="amd-card p-4 text-center amd-card-hover">
              <div className="w-10 h-10 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
                <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <p className="text-sm text-white/70 font-medium">Industry Insights</p>
            </div>
            <div className="amd-card p-4 text-center amd-card-hover">
              <div className="w-10 h-10 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
                <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <p className="text-sm text-white/70 font-medium">Best Practices</p>
            </div>
            <div className="amd-card p-4 text-center amd-card-hover">
              <div className="w-10 h-10 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
                <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <p className="text-sm text-white/70 font-medium">Case Studies</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
