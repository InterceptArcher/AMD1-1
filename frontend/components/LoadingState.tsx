'use client';

export default function LoadingState() {
  return (
    <div
      data-testid="loading-state"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem',
        backgroundColor: '#f9fafb',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          border: '4px solid #e5e7eb',
          borderTop: '4px solid #0A66C2',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}
      />
      <p
        style={{
          marginTop: '1.5rem',
          fontSize: '1.125rem',
          fontWeight: '600',
          color: '#374151',
        }}
      >
        Generating personalized content...
      </p>
      <p
        style={{
          marginTop: '0.5rem',
          fontSize: '0.875rem',
          color: '#6b7280',
        }}
      >
        This may take a few moments
      </p>

      <style jsx>{`
        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}
