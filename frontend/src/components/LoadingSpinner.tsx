'use client';

import { useState, useEffect, useMemo } from 'react';

interface UserContext {
  company?: string;
}

interface LoadingSpinnerProps {
  message?: string;
  userContext?: UserContext;
}

export default function LoadingSpinner({ message, userContext }: LoadingSpinnerProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [displayMessage, setDisplayMessage] = useState(message || 'Personalizing your content...');
  const [isInitialized, setIsInitialized] = useState(false);

  const companyName = userContext?.company || 'your company';

  // Generate loading steps focused on enrichment process
  const steps = useMemo(() => {
    return [
      `Analyzing ${companyName}...`,
      'Looking up company data...',
      'Gathering company intelligence...',
      'Searching recent news and announcements...',
      'Analyzing industry trends...',
      'Identifying business priorities...',
      'Detecting modernization stage...',
      'Selecting relevant case studies...',
      'Generating personalized insights with AI...',
      'Building your executive assessment...',
      'Finalizing your personalized content...',
    ];
  }, [companyName]);

  // Initialize on first render
  useEffect(() => {
    if (!isInitialized) {
      setDisplayMessage(steps[0]);
      setCurrentStep(0);
      setIsInitialized(true);
    }
  }, [steps, isInitialized]);

  // Cycle through messages
  useEffect(() => {
    if (!isInitialized) return;

    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        const next = prev + 1;
        if (next >= steps.length) return prev;
        setDisplayMessage(steps[next]);
        return next;
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [isInitialized, steps]);

  const progress = Math.max(8, Math.min(((currentStep + 1) / steps.length) * 100, 95));

  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex flex-col items-center justify-center space-y-8 py-12 animate-fade-in-up"
    >
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white mb-3">
          Analyzing <span className="text-[#00c8aa]">{companyName}</span>
        </h2>
        <p className="text-white/70 text-base">
          Building your personalized assessment
        </p>
      </div>

      {/* Animated spinner */}
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-[#00c8aa]/20 blur-xl animate-pulse" />
        <div className="relative w-24 h-24 rounded-full border-2 border-white/20 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-[#00c8aa] animate-spin" />
          <div className="absolute inset-2 rounded-full border-2 border-transparent border-r-[#00c8aa]/50 animate-spin [animation-duration:1.5s]" />
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
          <div className="flex items-center gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center">
              <span className="text-[#00c8aa] font-bold text-sm">{currentStep + 1}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white transition-all duration-500 truncate">
                {displayMessage}
              </p>
              <p className="text-sm text-white/60 mt-1">Enriching from multiple data sources...</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="relative h-3 rounded-full bg-white/15 overflow-hidden shadow-inner">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[#00c8aa] via-[#00d4b4] to-[#00e0be] transition-all duration-700 ease-out shadow-[0_0_10px_rgba(0,200,170,0.5)]"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_1.5s_ease-in-out_infinite]" />
            </div>
          </div>

          <div className="flex items-center justify-between text-sm text-white/50">
            <span>Step {currentStep + 1} of {steps.length}</span>
            <span className="font-medium">{Math.round(progress)}% complete</span>
          </div>
        </div>
      </div>

      {/* Preview section */}
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
            <p className="text-sm text-white/70 font-medium">Strategic Advantages</p>
          </div>
          <div className="amd-card p-4 text-center amd-card-hover">
            <div className="w-10 h-10 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <p className="text-sm text-white/70 font-medium">Risk Analysis</p>
          </div>
          <div className="amd-card p-4 text-center amd-card-hover">
            <div className="w-10 h-10 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <p className="text-sm text-white/70 font-medium">Next Steps</p>
          </div>
        </div>
      </div>
    </div>
  );
}
