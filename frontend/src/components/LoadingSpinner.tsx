'use client';

import { useState, useEffect, useMemo, useRef } from 'react';

interface UserContext {
  firstName?: string;
  company?: string;
  industry?: string;
  persona?: string;
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

// Role-specific messages (keys match form persona values)
const PERSONA_MESSAGES: Record<string, string> = {
  cto: 'Preparing technical infrastructure insights...',
  cio: 'Curating IT strategy recommendations...',
  ciso: 'Adding security and compliance frameworks...',
  cdo: 'Incorporating data strategy considerations...',
  ceo: 'Preparing executive-level business insights...',
  coo: 'Adding operational efficiency analysis...',
  cfo: 'Including cost optimization frameworks...',
  vp_engineering: 'Adding engineering leadership perspectives...',
  vp_it: 'Curating IT infrastructure recommendations...',
  vp_data: 'Incorporating data and analytics insights...',
  vp_security: 'Adding security posture analysis...',
  vp_operations: 'Preparing operational strategy insights...',
  eng_manager: 'Including technical implementation details...',
  it_manager: 'Adding infrastructure management insights...',
  data_manager: 'Incorporating data platform analysis...',
  security_manager: 'Adding security framework details...',
  sr_engineer: 'Including technical architecture details...',
  engineer: 'Adding implementation considerations...',
  sysadmin: 'Including systems administration insights...',
  ops_manager: 'Preparing operational workflow analysis...',
  procurement: 'Including vendor evaluation criteria...',
};

// Overtime messages shown when primary steps are exhausted but API hasn't returned
const OVERTIME_MESSAGES = [
  'Cross-referencing industry benchmarks...',
  'Fine-tuning your recommendations...',
  'Applying latest AMD research data...',
  'Validating insights against your profile...',
  'Optimizing content for your role...',
  'Running final quality checks...',
  'Polishing your executive summary...',
  'Double-checking personalization accuracy...',
  'Reviewing case study alignment...',
  'Assembling your complete assessment...',
];

export default function LoadingSpinner({ message, userContext }: LoadingSpinnerProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [displayMessage, setDisplayMessage] = useState(message || 'Personalizing your content...');
  const [isInitialized, setIsInitialized] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const startTimeRef = useRef(Date.now());

  // Generate personalized loading steps - memoized to prevent recreation
  const steps = useMemo(() => {
    const result: string[] = [];

    if (userContext?.firstName && userContext?.company) {
      result.push(`Hi ${userContext.firstName}, generating your AI readiness snapshot for ${userContext.company}...`);
    } else if (userContext?.firstName) {
      result.push(`Hi ${userContext.firstName}, creating your AI readiness assessment...`);
    } else {
      result.push('Creating your AI readiness assessment...');
    }

    // Analysis steps
    result.push('Analyzing your IT environment and priorities...');
    result.push('Loading AMD reference data...');

    // Add industry-specific messages
    if (userContext?.industry && INDUSTRY_MESSAGES[userContext.industry]) {
      result.push(...INDUSTRY_MESSAGES[userContext.industry]);
    }

    // Add persona-specific message
    if (userContext?.persona && PERSONA_MESSAGES[userContext.persona]) {
      result.push(PERSONA_MESSAGES[userContext.persona]);
    }

    // Final steps
    result.push('Identifying advantages and risks...');
    result.push('Selecting relevant case studies...');
    result.push('Generating personalized recommendations...');
    result.push('Finalizing your executive review...');

    return result;
  }, [userContext?.firstName, userContext?.company, userContext?.industry, userContext?.persona]);

  // Track elapsed time for smooth asymptotic progress
  useEffect(() => {
    startTimeRef.current = Date.now();
    const timer = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 200);
    return () => clearInterval(timer);
  }, []);

  // Initialize on first render with userContext
  useEffect(() => {
    if (!userContext) {
      setDisplayMessage(message || 'Loading...');
      return;
    }

    // Only initialize once
    if (!isInitialized) {
      setDisplayMessage(steps[0]);
      setCurrentStep(0);
      setIsInitialized(true);
    }
  }, [userContext, steps, message, isInitialized]);

  // Step advancement with adaptive timing + overtime messages
  // Uses setTimeout chain instead of fixed setInterval so pacing can slow down
  useEffect(() => {
    if (!userContext || !isInitialized) return;

    let stepIndex = 0;
    let timeoutId: ReturnType<typeof setTimeout>;

    const advance = () => {
      stepIndex++;

      if (stepIndex < steps.length) {
        // Primary steps
        setDisplayMessage(steps[stepIndex]);
      } else {
        // Overtime: cycle through additional messages seamlessly
        const overtimeIdx = (stepIndex - steps.length) % OVERTIME_MESSAGES.length;
        setDisplayMessage(OVERTIME_MESSAGES[overtimeIdx]);
      }
      setCurrentStep(stepIndex);

      // Adaptive timing: slow down as we progress
      let interval: number;
      if (stepIndex < steps.length - 2) {
        interval = 2000;  // Primary steps: 2s each
      } else if (stepIndex < steps.length) {
        interval = 2500;  // Last primary steps: 2.5s
      } else if (stepIndex < steps.length + 3) {
        interval = 3500;  // Early overtime: 3.5s
      } else {
        interval = 5000;  // Late overtime: 5s
      }

      timeoutId = setTimeout(advance, interval);
    };

    timeoutId = setTimeout(advance, 2000);
    return () => clearTimeout(timeoutId);
  }, [userContext, isInitialized, steps]);

  // Time-based asymptotic progress: fast early, slows down, never reaches 93%
  // t=5s→28%, t=10s→44%, t=20s→64%, t=30s→76%, t=45s→85%, t=60s→89%
  const elapsedSeconds = elapsedMs / 1000;
  const progress = Math.min(92, 8 + 84 * (1 - Math.exp(-elapsedSeconds / 18)));

  // Display helpers for overtime state
  const isOvertime = currentStep >= steps.length;
  const displayStepNum = Math.min(currentStep + 1, steps.length);

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
          <h2 className="text-2xl font-bold text-white">Generating Your Assessment</h2>
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
              {isOvertime ? (
                <svg className="w-5 h-5 text-[#00c8aa] animate-spin [animation-duration:2s]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              ) : (
                <span className="text-[#00c8aa] font-bold text-sm">{displayStepNum}</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white transition-all duration-500 truncate">
                {displayMessage}
              </p>
              <p className="text-sm text-white/60 mt-1">
                {isOvertime ? 'Taking a bit longer — almost there...' : 'Processing your personalization...'}
              </p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="relative h-3 rounded-full bg-white/15 overflow-hidden shadow-inner">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[#00c8aa] via-[#00d4b4] to-[#00e0be] transition-all duration-700 ease-out shadow-[0_0_10px_rgba(0,200,170,0.5)]"
              style={{ width: `${progress}%` }}
            >
              {/* Animated shine effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_1.5s_ease-in-out_infinite]" />
            </div>
          </div>

          {/* Step counter */}
          <div className="flex items-center justify-between text-sm text-white/50">
            <span>{isOvertime ? 'Refining your results...' : `Step ${displayStepNum} of ${steps.length}`}</span>
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
                {userContext.company && (
                  <span className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 text-white/80 text-sm font-medium">
                    {userContext.company}
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
            Your assessment will include
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
