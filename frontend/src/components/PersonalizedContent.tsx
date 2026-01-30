'use client';

import { useState, useEffect } from 'react';

interface PersonalizationData {
  intro_hook: string;
  cta: string;
  first_name?: string;
  company?: string;
  title?: string;
  email?: string;
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
      link.download = `personalized-ebook-${data.first_name || 'user'}.pdf`;
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

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const greeting = data.first_name
    ? `Hi ${data.first_name}!`
    : 'Welcome!';

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-8 text-white">
        <p className="text-sm font-medium uppercase tracking-wider opacity-80">Your Personalized Ebook</p>
        <h2 className="mt-2 text-2xl font-bold">{greeting}</h2>
        {data.company && (
          <p className="mt-1 text-blue-100">
            Tailored insights for {data.title ? `${data.title} at ` : ''}{data.company}
          </p>
        )}
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Delivery Status Banner */}
        {isDelivering && (
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-4 flex items-center gap-3">
            <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
            <p className="text-blue-700 font-medium">Sending your personalized ebook...</p>
          </div>
        )}

        {deliveryStatus?.email_sent && (
          <div className="rounded-lg bg-green-50 border border-green-200 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100">
                <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-green-800">Check your inbox!</p>
                <p className="text-sm text-green-600">We've sent your personalized ebook to {data.email}</p>
              </div>
            </div>
          </div>
        )}

        {deliveryStatus && !deliveryStatus.email_sent && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100">
                <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-amber-800">Email delivery unavailable</p>
                <p className="text-sm text-amber-600">No worries! Download your ebook directly below.</p>
              </div>
            </div>
          </div>
        )}

        {/* Intro Hook */}
        <div className="prose prose-gray">
          <p className="text-lg leading-relaxed text-gray-700">{data.intro_hook}</p>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-gray-200"></div>
          <span className="text-xs font-medium uppercase tracking-wider text-gray-400">What's Inside</span>
          <div className="h-px flex-1 bg-gray-200"></div>
        </div>

        {/* Preview bullets */}
        <ul className="space-y-3 text-gray-600">
          <li className="flex items-start gap-3">
            <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">✓</span>
            <span>Industry-specific strategies and best practices</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">✓</span>
            <span>Real-world case studies from leading companies</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">✓</span>
            <span>Actionable frameworks you can implement today</span>
          </li>
        </ul>

        {/* CTA Box */}
        <div className="rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 p-5 border border-blue-100">
          <p className="font-semibold text-gray-900">{data.cta}</p>
        </div>

        {/* Download Button - always available */}
        {!isDelivering && (
          <button
            className="w-full rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white shadow-md transition hover:bg-blue-700 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handleDownload}
            disabled={isDownloading || !data.email}
          >
            {isDownloading ? (
              <span className="flex items-center justify-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                Generating Your Ebook...
              </span>
            ) : deliveryStatus?.email_sent ? (
              'Download a Copy Now'
            ) : (
              'Download Your Free Ebook'
            )}
          </button>
        )}

        <p className="text-center text-xs text-gray-400">
          {deliveryStatus?.email_sent
            ? "We've also emailed you a copy. Didn't get it? Check your spam folder."
            : 'Your personalized ebook will open in a new tab'}
        </p>

        {onReset && (
          <button
            onClick={onReset}
            className="w-full text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Try with a different email
          </button>
        )}
      </div>
    </div>
  );
}
