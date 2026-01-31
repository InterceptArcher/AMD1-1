import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Enterprise AI Readiness Framework | AMD',
  description: 'Get your personalized guide to data center modernization and AI readiness. From Observers to Leaders.',
  keywords: ['AMD', 'AI', 'Enterprise', 'Data Center', 'Modernization', 'Infrastructure'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className="min-h-screen antialiased amd-gradient-bg amd-grid-pattern"
        style={{
          backgroundColor: '#0a0a12',
          color: '#f0f0f5',
        }}
      >
        {children}
      </body>
    </html>
  );
}
