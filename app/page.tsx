'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import EmailForm from '@/frontend/components/EmailForm';
import LoadingState from '@/frontend/components/LoadingState';
import PersonalizedResults from '@/frontend/components/PersonalizedResults';

function LandingPageContent() {
  const searchParams = useSearchParams();
  const cta = searchParams.get('cta') || 'compare';

  const [stage, setStage] = useState<'form' | 'loading' | 'results' | 'error'>('form');
  const [personalizedContent, setPersonalizedContent] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFormSubmit = async (data: {
    email: string;
    name?: string;
    company: string;
    role: string;
    modernization_stage: string;
    ai_priority: string;
  }) => {
    setStage('loading');
    setError(null);

    try {
      const response: Response = await fetch('/api/personalize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...data, cta }),
      });

      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(responseData.error || 'Failed to generate personalized content');
      }

      setPersonalizedContent(responseData);
      setStage('results');
    } catch (err) {
      console.error('Personalization error:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
      setStage('error');
    }
  };

  return (
    <main style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#f9fafb',
    }}>
      <div style={{
        maxWidth: stage === 'results' ? '900px' : '600px',
        width: '100%',
        textAlign: 'center',
      }}>
        {/* Header - always visible */}
        <h1 style={{
          fontSize: '2.5rem',
          marginBottom: '1rem',
          color: '#DC2626'
        }}>
          {stage === 'results' ? 'Your Personalized Experience' : 'AMD Campaign Experience'}
        </h1>

        {stage === 'form' && (
          <p style={{
            fontSize: '1rem',
            marginBottom: '2rem',
            color: '#6b7280'
          }}>
            Tell us about your modernization journey to receive personalized insights
          </p>
        )}

        {stage === 'form' && (
          <p style={{
            fontSize: '1.25rem',
            marginBottom: '2rem',
            color: '#666'
          }}>
            Call to Action: <span data-testid="cta-display" style={{ fontWeight: 'bold', color: '#000' }}>{cta}</span>
          </p>
        )}

        {/* Form Stage */}
        {stage === 'form' && <EmailForm onSubmit={handleFormSubmit} />}

        {/* Loading Stage */}
        {stage === 'loading' && <LoadingState />}

        {/* Results Stage */}
        {stage === 'results' && personalizedContent && (
          <PersonalizedResults
            content={personalizedContent.data}
            metadata={personalizedContent.metadata}
          />
        )}

        {/* Error Stage */}
        {stage === 'error' && (
          <div
            style={{
              padding: '2rem',
              backgroundColor: '#FEE2E2',
              color: '#991B1B',
              borderRadius: '8px',
              textAlign: 'center',
            }}
          >
            <h2 style={{ marginBottom: '0.5rem' }}>Oops!</h2>
            <p>{error || 'Something went wrong. Please try again.'}</p>
            <button
              onClick={() => setStage('form')}
              style={{
                marginTop: '1rem',
                padding: '0.5rem 1.5rem',
                backgroundColor: '#991B1B',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LandingPageContent />
    </Suspense>
  );
}
