'use client';

import { useState, useEffect } from 'react';

interface PersonalizationData {
  intro_hook: string;
  cta: string;
  first_name?: string;
  company?: string;
  title?: string;
  email?: string;
  // Enhanced enrichment data
  employee_count?: number;
  funding_stage?: string;
  recent_news?: Array<{ title: string; source?: string }>;
  skills?: string[];
  news_themes?: string[];
}

interface DeliveryStatus {
  email_sent: boolean;
  pdf_url?: string;
  error?: string;
}

interface PersonalizedContentProps {
  data: PersonalizationData | null;
  error?: string | null;
  onReset?: () => void;
}

export default function PersonalizedContent({ data, error, onReset }: PersonalizedContentProps) {
  const [deliveryStatus, setDeliveryStatus] = useState<DeliveryStatus | null>(null);
  const [isDelivering, setIsDelivering] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // Automatically trigger email delivery when data is available
  useEffect(() => {
    if (data?.email && !deliveryStatus && !isDelivering) {
      deliverEbook();
    }
  }, [data?.email]);

  const deliverEbook = async () => {
    if (!data?.email) return;

    setIsDelivering(true);

    try {
      const response = await fetch(`/api/rad/deliver/${encodeURIComponent(data.email)}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to deliver ebook');
      }

      const result = await response.json();

      setDeliveryStatus({
        email_sent: result.email_sent,
        pdf_url: result.pdf_url,
        error: result.email_error,
      });
    } catch (err) {
      console.error('Delivery error:', err);
      setDeliveryStatus({
        email_sent: false,
        error: 'Failed to deliver your ebook. Please try downloading instead.',
      });
    } finally {
      setIsDelivering(false);
    }
  };

  const handleDownload = async () => {
    if (!data?.email) return;

    setIsDownloading(true);

    try {
      // Use direct download endpoint - returns actual PDF file
      const response = await fetch(`/api/rad/download/${encodeURIComponent(data.email)}`);

      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }

      // Get the PDF blob
      const blob = await response.blob();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `AMD-AI-Readiness-${data.first_name || 'Guide'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error('Download error:', err);
    } finally {
      setIsDownloading(false);
    }
  };

  // Format employee count for display
  const formatEmployeeCount = (count: number): string => {
    if (count >= 10000) return `${Math.round(count / 1000)}k+`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
    return count.toString();
  };

  if (error) {
    return (
      <div className="amd-card p-8 border-red-500/30 bg-red-500/5">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-full bg-red-500/15 flex items-center justify-center">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-red-400 font-medium text-base">{error}</p>
        </div>
        {onReset && (
          <button onClick={onReset} className="text-sm font-semibold text-[#00c8aa] hover:underline">
            Try again
          </button>
        )}
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const greeting = data.first_name
    ? `Your guide is ready, ${data.first_name}!`
    : 'Your guide is ready!';

  // Check if we have any enrichment data to display
  const hasEnrichmentData = data.employee_count || data.funding_stage || (data.recent_news && data.recent_news.length > 0) || (data.skills && data.skills.length > 0) || (data.news_themes && data.news_themes.length > 0);

  return (
    <div className="amd-card overflow-hidden amd-glow-intense">
      {/* Success Header with gradient */}
      <div className="relative px-8 py-10 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#00c8aa]/25 via-[#00c8aa]/10 to-transparent" />
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#00c8aa]/15 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4" />

        {/* Success checkmark */}
        <div className="relative flex items-center gap-5 mb-6">
          <div className="w-16 h-16 rounded-2xl bg-[#00c8aa]/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white">{greeting}</h2>
            {data.company && (
              <p className="text-white/60 text-base mt-1">
                Customized for{' '}
                <span className="text-[#00c8aa] font-semibold">{data.company}</span>
              </p>
            )}
          </div>
        </div>

        {/* User context pills */}
        {(data.title || data.company) && (
          <div className="relative flex flex-wrap gap-2">
            {data.title && (
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 text-sm text-white/80">
                <svg className="w-4 h-4 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                {data.title}
              </span>
            )}
            {data.employee_count && (
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 text-sm text-white/80">
                <svg className="w-4 h-4 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                {formatEmployeeCount(data.employee_count)} employees
              </span>
            )}
            {data.funding_stage && (
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#00c8aa]/15 text-sm text-[#00c8aa] font-medium">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                {data.funding_stage}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Content Section */}
      <div className="px-8 py-8 space-y-6">
        {/* Delivery Status Banners */}
        {isDelivering && (
          <div className="rounded-xl bg-[#00c8aa]/10 border border-[#00c8aa]/30 p-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#00c8aa]/15 flex items-center justify-center flex-shrink-0">
              <div className="w-5 h-5 border-2 border-[#00c8aa] border-t-transparent rounded-full animate-spin" />
            </div>
            <div>
              <p className="text-[#00c8aa] font-semibold">Sending your personalized ebook...</p>
              <p className="text-sm text-white/60 mt-1">This will just take a moment</p>
            </div>
          </div>
        )}

        {deliveryStatus?.email_sent && (
          <div className="rounded-xl bg-[#00c8aa]/10 border border-[#00c8aa]/40 p-5">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-[#00c8aa]/20 flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-white text-base">Check your inbox!</p>
                <p className="text-sm text-white/70 mt-1">Sent to <span className="text-[#00c8aa] font-medium">{data.email}</span></p>
              </div>
            </div>
          </div>
        )}

        {deliveryStatus && !deliveryStatus.email_sent && (
          <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-4">
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-white/70">Email unavailable - download your ebook directly below</p>
            </div>
          </div>
        )}

        {/* Enrichment Data Display - "What we found" section */}
        {hasEnrichmentData && (
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <div className="flex items-center gap-2 mb-4">
              <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <span className="text-sm font-semibold text-white/70 uppercase tracking-wide">What we found about {data.company || 'your company'}</span>
            </div>

            <div className="space-y-4">
              {/* Recent News */}
              {data.recent_news && data.recent_news.length > 0 && (
                <div>
                  <p className="text-xs text-white/50 uppercase tracking-wide mb-2">Recent News</p>
                  <div className="space-y-2">
                    {data.recent_news.slice(0, 2).map((news, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="text-[#00c8aa] mt-1">•</span>
                        <p className="text-sm text-white/80 line-clamp-2">{news.title}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* News Themes */}
              {data.news_themes && data.news_themes.length > 0 && (
                <div>
                  <p className="text-xs text-white/50 uppercase tracking-wide mb-2">Focus Areas</p>
                  <div className="flex flex-wrap gap-2">
                    {data.news_themes.map((theme, idx) => (
                      <span key={idx} className="px-2.5 py-1 rounded-md bg-[#00c8aa]/10 text-[#00c8aa] text-xs font-medium">
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Skills (if available) */}
              {data.skills && data.skills.length > 0 && (
                <div>
                  <p className="text-xs text-white/50 uppercase tracking-wide mb-2">Your Expertise</p>
                  <div className="flex flex-wrap gap-2">
                    {data.skills.map((skill, idx) => (
                      <span key={idx} className="px-2.5 py-1 rounded-md bg-white/10 text-white/70 text-xs">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Intro Hook */}
        <div className="py-2">
          <p className="text-base sm:text-lg text-white/80 leading-relaxed">{data.intro_hook}</p>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/15 to-transparent" />
          <span className="text-xs font-semibold uppercase tracking-widest text-white/40">Your Guide Includes</span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/15 to-transparent" />
        </div>

        {/* Feature List - Enhanced */}
        <div className="grid sm:grid-cols-3 gap-4">
          <div className="amd-card p-4 amd-card-hover text-center">
            <div className="w-10 h-10 rounded-xl bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <p className="text-sm text-white/80 font-medium">Industry Strategies</p>
          </div>
          <div className="amd-card p-4 amd-card-hover text-center">
            <div className="w-10 h-10 rounded-xl bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <p className="text-sm text-white/80 font-medium">Case Studies</p>
          </div>
          <div className="amd-card p-4 amd-card-hover text-center">
            <div className="w-10 h-10 rounded-xl bg-[#00c8aa]/15 flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
            </div>
            <p className="text-sm text-white/80 font-medium">Action Framework</p>
          </div>
        </div>

        {/* CTA Box */}
        <div className="rounded-xl bg-gradient-to-r from-[#00c8aa]/20 via-[#00c8aa]/10 to-transparent p-5 border border-[#00c8aa]/20">
          <p className="font-medium text-white text-base leading-relaxed">{data.cta}</p>
        </div>

        {/* Download Button */}
        {!isDelivering && (
          <button
            className="amd-button-primary amd-button-shimmer flex items-center justify-center gap-3"
            onClick={handleDownload}
            disabled={isDownloading || !data.email}
          >
            {isDownloading ? (
              <>
                <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Generating Your Ebook...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                {deliveryStatus?.email_sent ? 'Download a Copy' : 'Download Your Free Ebook'}
              </>
            )}
          </button>
        )}

        <p className="text-center text-sm text-white/40">
          {deliveryStatus?.email_sent
            ? "Also sent to your email. Check spam if you don't see it."
            : 'Instant download - no waiting required'}
        </p>

        {/* Reset Link */}
        {onReset && (
          <div className="pt-6 border-t border-white/10 text-center">
            <button
              onClick={onReset}
              className="text-sm text-white/40 hover:text-[#00c8aa] transition-colors font-medium"
            >
              Start over with different information
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
