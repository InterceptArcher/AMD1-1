'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import EmailConsentForm, { UserInputs } from '@/components/EmailConsentForm';
import LoadingSpinner from '@/components/LoadingSpinner';
import PersonalizedContent from '@/components/PersonalizedContent';

interface PersonalizationData {
  intro_hook: string;
  cta: string;
  first_name?: string;
  company?: string;
  title?: string;
  email?: string;
}

interface UserContext {
  firstName?: string;
  company?: string;
  industry?: string;
  persona?: string;
  goal?: string;
}

function HomeContent() {
  const searchParams = useSearchParams();
  const cta = searchParams.get('cta');

  const [isLoading, setIsLoading] = useState(false);
  const [userContext, setUserContext] = useState<UserContext | null>(null);
  const [personalizationData, setPersonalizationData] = useState<PersonalizationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReset = () => {
    setPersonalizationData(null);
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
      goal: inputs.goal,
    });

    try {
      const apiUrl = getApiUrl();

      const response = await fetch(`${apiUrl}/rad/enrich`, {
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
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start personalization: ${response.status}`);
      }

      const profileResponse = await fetch(`${apiUrl}/rad/profile/${encodeURIComponent(inputs.email)}`);

      if (!profileResponse.ok) {
        throw new Error(`Failed to fetch profile: ${profileResponse.status}`);
      }

      const profileData = await profileResponse.json();

      setPersonalizationData({
        intro_hook: profileData.personalization?.intro_hook || 'Welcome!',
        cta: profileData.personalization?.cta || 'Get started today',
        first_name: inputs.firstName || profileData.normalized_profile?.first_name,
        company: inputs.company || profileData.normalized_profile?.company,
        title: profileData.normalized_profile?.title,
        email: inputs.email,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen relative">
      {/* Decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[#00c8aa]/5 rounded-full blur-[120px] translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-[#00c8aa]/3 rounded-full blur-[100px] -translate-x-1/2 translate-y-1/2" />
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Header */}
        <header className="px-6 py-6 lg:px-12">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="text-2xl font-bold tracking-wider text-white">AMD</div>
            <div className="hidden sm:flex items-center gap-6 text-sm text-white/70">
              <span>Enterprise Solutions</span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#00c8aa]" />
              <span>AI Readiness</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 flex items-center justify-center px-6 py-12 lg:px-12">
          <div className="w-full max-w-6xl">
            {!personalizationData && !isLoading && (
              <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
                {/* Left Side - Hero */}
                <div className="animate-fade-in-up">
                  <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full border border-[#00c8aa]/40 bg-[#00c8aa]/10 mb-8">
                    <span className="w-2 h-2 rounded-full bg-[#00c8aa] animate-pulse" />
                    <span className="text-sm text-[#00c8aa] font-semibold">Free Personalized Ebook</span>
                  </div>

                  <p className="text-[#00c8aa] font-bold uppercase tracking-widest text-sm mb-5">
                    From Observers to Leaders
                  </p>

                  <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.1] mb-8 text-white">
                    An Enterprise<br />
                    <span className="amd-text-gradient">AI Readiness</span><br />
                    Framework
                  </h1>

                  <p className="text-lg text-white/80 leading-relaxed mb-10 max-w-lg">
                    Discover where your organization stands on the modernization curve and get a personalized roadmap to AI leadership.
                  </p>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-8">
                    <div className="animate-fade-in-up stagger-1">
                      <div className="text-4xl font-bold text-[#00c8aa]">33%</div>
                      <div className="text-sm text-white/60 mt-2 font-medium">Leaders</div>
                    </div>
                    <div className="animate-fade-in-up stagger-2">
                      <div className="text-4xl font-bold text-white">58%</div>
                      <div className="text-sm text-white/60 mt-2 font-medium">Challengers</div>
                    </div>
                    <div className="animate-fade-in-up stagger-3">
                      <div className="text-4xl font-bold text-white/70">9%</div>
                      <div className="text-sm text-white/60 mt-2 font-medium">Observers</div>
                    </div>
                  </div>
                </div>

                {/* Right Side - Form */}
                <div className="animate-fade-in-up stagger-2">
                  <div className="amd-card p-8 lg:p-10 amd-glow">
                    <div className="mb-8">
                      <h2 className="text-2xl font-bold mb-3 text-white">Get Your Personalized Guide</h2>
                      <p className="text-white/70 text-base">
                        Tailored insights for your industry and role
                      </p>
                    </div>
                    <EmailConsentForm onSubmit={handleSubmit} isLoading={isLoading} />
                  </div>
                </div>
              </div>
            )}

            {isLoading && (
              <div className="max-w-xl mx-auto">
                <LoadingSpinner userContext={userContext || undefined} />
              </div>
            )}

            {personalizationData && (
              <div className="max-w-2xl mx-auto animate-fade-in-up">
                <PersonalizedContent data={personalizationData} error={error} onReset={handleReset} />
              </div>
            )}

            {error && !personalizationData && !isLoading && (
              <div className="max-w-md mx-auto amd-card p-8 border-red-500/30 bg-red-500/5">
                <p className="text-red-400 text-base">{error}</p>
                <button
                  onClick={handleReset}
                  className="mt-6 text-sm font-semibold text-[#00c8aa] hover:underline"
                >
                  Try again
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="px-6 py-8 lg:px-12 border-t border-white/10">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-white/50">
            <div>© 2025 Advanced Micro Devices, Inc.</div>
            <div className="flex items-center gap-8">
              <span className="hover:text-white/70 cursor-pointer transition-colors">Privacy</span>
              <span className="hover:text-white/70 cursor-pointer transition-colors">Terms</span>
              <span className="hover:text-white/70 cursor-pointer transition-colors">Contact</span>
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#00c8aa] border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <HomeContent />
    </Suspense>
  );
}
