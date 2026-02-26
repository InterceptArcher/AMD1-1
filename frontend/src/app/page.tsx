'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import EmailConsentForm, { UserInputs } from '@/components/EmailConsentForm';
import LoadingSpinner from '@/components/LoadingSpinner';
import PersonalizedContent from '@/components/PersonalizedContent';
import ExecutiveReviewDisplay from '@/components/ExecutiveReviewDisplay';

interface PersonalizationData {
  intro_hook: string;
  cta: string;
  first_name?: string;
  company?: string;
  title?: string;
  email?: string;
  // Enhanced enrichment data for display
  employee_count?: number;
  funding_stage?: string;
  recent_news?: Array<{ title: string; source?: string }>;
  skills?: string[];
  news_themes?: string[];
}

interface UserContext {
  firstName?: string;
  company?: string;
  industry?: string;
  persona?: string;
}

interface ExecutiveReviewData {
  company_name: string;
  stage: string;
  stage_sidebar: string;
  stage_identification_text?: string;
  advantages: Array<{ headline: string; description: string }>;
  risks: Array<{ headline: string; description: string }>;
  recommendations: Array<{ title: string; description: string }>;
  case_study: string;
  case_study_description: string;
  case_study_link?: string;
  case_study_relevance?: string;
}

interface ExecutiveReviewInputs {
  industry: string;
  segment: string;
  persona: string;
  stage: string;
  priority: string;
  challenge: string;
}

interface ExecutiveReviewResponse {
  success: boolean;
  company_name: string;
  inputs: ExecutiveReviewInputs;
  executive_review: ExecutiveReviewData;
}

function HomeContent() {
  const searchParams = useSearchParams();
  const cta = searchParams.get('cta');

  const [isLoading, setIsLoading] = useState(false);
  const [userContext, setUserContext] = useState<UserContext | null>(null);
  const [personalizationData, setPersonalizationData] = useState<PersonalizationData | null>(null);
  const [executiveReview, setExecutiveReview] = useState<ExecutiveReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReset = () => {
    setPersonalizationData(null);
    setExecutiveReview(null);
    setUserContext(null);
    setError(null);
  };

  const getApiUrl = () => {
    return '/api';
  };

  const handleSubmit = async (inputs: UserInputs) => {
    setIsLoading(true);
    setError(null);

    setUserContext({
      firstName: inputs.firstName,
      company: inputs.company,
      industry: inputs.industry,
      persona: inputs.persona,
    });

    // Minimum 10s so users always see the personalized loading experience
    // The animation is elastic (never freezes) and handles longer waits gracefully
    const minLoadingMs = 10000;
    const minLoadingTime = new Promise(resolve => setTimeout(resolve, minLoadingMs));

    try {
      const apiUrl = getApiUrl();

      // Run API calls and minimum loading time in parallel
      const apiCall = async () => {
        // Call the executive review endpoint
        const response = await fetch(`${apiUrl}/rad/executive-review`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: inputs.email,
            firstName: inputs.firstName,
            lastName: inputs.lastName,
            company: inputs.company,
            companySize: inputs.companySize,
            goal: inputs.goal,
            persona: inputs.persona,
            industry: inputs.industry,
            cta: cta || 'default',
            // Fields for executive review generation
            itEnvironment: inputs.itEnvironment,
            businessPriority: inputs.businessPriority,
            challenge: inputs.challenge,
            signalAnswers: inputs.signalAnswers,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to generate executive review: ${response.status} - ${errorText}`);
        }

        return response.json();
      };

      // Wait for both API and minimum loading time
      const [reviewData] = await Promise.all([apiCall(), minLoadingTime]);

      // Store the executive review response
      setExecutiveReview(reviewData as ExecutiveReviewResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen relative overflow-hidden">
      {/* Enhanced Background Effects */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Primary glow - top right */}
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[#00c8aa]/[0.07] rounded-full blur-[150px] translate-x-1/3 -translate-y-1/3" />
        {/* Secondary glow - bottom left */}
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-[#00c8aa]/[0.04] rounded-full blur-[120px] -translate-x-1/3 translate-y-1/3" />
        {/* Accent glow - center */}
        <div className="absolute top-1/2 left-1/2 w-[400px] h-[400px] bg-blue-500/[0.03] rounded-full blur-[100px] -translate-x-1/2 -translate-y-1/2" />
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 amd-grid-pattern opacity-30" />
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Header */}
        <header className="px-6 py-6 lg:px-12 animate-fade-in-up">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <img
              src="/amd-logo.svg"
              alt="AMD"
              className="h-8 sm:h-10 w-auto transition-transform hover:scale-105"
            />
            <div className="hidden sm:flex items-center gap-6 text-sm text-white/60">
              <span className="hover:text-white/80 transition-colors cursor-default">Enterprise Solutions</span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#00c8aa] animate-pulse" />
              <span className="hover:text-white/80 transition-colors cursor-default">AI Readiness</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 flex items-center justify-center px-6 py-8 lg:py-12 lg:px-12">
          <div className="w-full max-w-6xl">
            {!personalizationData && !executiveReview && !isLoading && (
              <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
                {/* Left Side - Hero */}
                <div className="animate-fade-in-left">
                  {/* Badge */}
                  <div className="amd-badge mb-8">
                    <span className="w-2 h-2 rounded-full bg-[#00c8aa] animate-pulse" />
                    <span>Free Personalized Ebook</span>
                  </div>

                  {/* Eyebrow */}
                  <p className="text-[#00c8aa] font-bold uppercase tracking-[0.2em] text-sm mb-4 animate-fade-in-up stagger-1">
                    From Observers to Leaders
                  </p>

                  {/* Main Headline */}
                  <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.08] mb-6 text-white animate-fade-in-up stagger-2">
                    An Enterprise<br />
                    <span className="amd-text-gradient-animated">AI Readiness</span><br />
                    Framework
                  </h1>

                  {/* Subheadline */}
                  <p className="text-lg sm:text-xl text-white/70 leading-relaxed mb-10 max-w-lg animate-fade-in-up stagger-3">
                    Discover where your organization stands on the modernization curve and get a personalized roadmap to AI leadership.
                  </p>

                  {/* Stats with enhanced styling */}
                  <div className="grid grid-cols-3 gap-6 sm:gap-8 animate-fade-in-up stagger-4">
                    <div className="amd-stat group cursor-default">
                      <div className="text-3xl sm:text-4xl font-bold text-[#00c8aa] transition-transform group-hover:scale-105">33%</div>
                      <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Leaders</div>
                    </div>
                    <div className="amd-stat group cursor-default">
                      <div className="text-3xl sm:text-4xl font-bold text-white transition-transform group-hover:scale-105">58%</div>
                      <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Challengers</div>
                    </div>
                    <div className="amd-stat group cursor-default">
                      <div className="text-3xl sm:text-4xl font-bold text-white/60 transition-transform group-hover:scale-105">9%</div>
                      <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Observers</div>
                    </div>
                  </div>

                  {/* Trust indicators */}
                  <div className="mt-10 pt-8 border-t border-white/10 animate-fade-in-up stagger-5">
                    <div className="flex flex-wrap items-center gap-6 text-sm text-white/40">
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-[#00c8aa]" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span>Personalized to your role</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-[#00c8aa]" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span>Industry-specific insights</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-[#00c8aa]" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        <span>Instant PDF download</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Side - Form Card */}
                <div className="animate-fade-in-right stagger-2">
                  <div className="amd-card-premium p-8 lg:p-10 amd-glow-intense">
                    {/* Form Header */}
                    <div className="mb-8">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-xl bg-[#00c8aa]/15 flex items-center justify-center">
                          <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                          </svg>
                        </div>
                        <div>
                          <h2 className="text-xl sm:text-2xl font-bold text-white">Get Your Guide</h2>
                          <p className="text-white/50 text-sm">Takes 30 seconds</p>
                        </div>
                      </div>
                      <p className="text-white/60 text-base">
                        Get a personalized AI readiness snapshot based on your industry, role, and IT environment.
                      </p>
                    </div>

                    {/* Form Component */}
                    <EmailConsentForm onSubmit={handleSubmit} isLoading={isLoading} />

                    {/* Privacy note */}
                    <div className="mt-6 flex items-start gap-2 text-xs text-white/40">
                      <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                      <span>Your data is secure and never shared with third parties.</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {isLoading && (
              <div className="max-w-xl mx-auto animate-fade-in-scale">
                <LoadingSpinner userContext={userContext || undefined} />
              </div>
            )}

            {executiveReview && (
              <div className="max-w-4xl mx-auto animate-fade-in-scale">
                <ExecutiveReviewDisplay
                  data={executiveReview.executive_review}
                  inputs={executiveReview.inputs}
                  onReset={handleReset}
                />
              </div>
            )}

            {personalizationData && !executiveReview && (
              <div className="max-w-2xl mx-auto animate-fade-in-scale">
                <PersonalizedContent data={personalizationData} error={error} onReset={handleReset} />
              </div>
            )}

            {error && !personalizationData && !executiveReview && !isLoading && (
              <div className="max-w-md mx-auto amd-card p-8 border-red-500/30 bg-red-500/5 animate-fade-in-up">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                    <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Something went wrong</h3>
                    <p className="text-red-400 text-sm">{error}</p>
                  </div>
                </div>
                <button
                  onClick={handleReset}
                  className="w-full mt-4 py-3 px-4 rounded-lg border border-white/20 text-white/80 hover:bg-white/5 transition-colors font-medium"
                >
                  Try again
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="px-6 py-6 lg:px-12 border-t border-white/[0.06]">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-white/40">
            <div className="flex items-center gap-2">
              <img src="/amd-logo.svg" alt="AMD" className="h-4 w-auto opacity-50" />
              <span>© 2026 Advanced Micro Devices, Inc.</span>
            </div>
            <div className="flex items-center gap-8">
              <span className="hover:text-white/60 cursor-pointer transition-colors">Privacy</span>
              <span className="hover:text-white/60 cursor-pointer transition-colors">Terms</span>
              <span className="hover:text-white/60 cursor-pointer transition-colors">Contact</span>
            </div>
          </div>
        </footer>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a12]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-[#00c8aa] border-t-transparent rounded-full animate-spin" />
          <p className="text-white/50 text-sm">Loading...</p>
        </div>
      </div>
    }>
      <HomeContent />
    </Suspense>
  );
}
