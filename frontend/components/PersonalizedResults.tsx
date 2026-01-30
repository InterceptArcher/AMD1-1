'use client';

interface PersonalizedContent {
  headline: string;
  subheadline: string;
  value_prop_1: string;
  value_prop_2: string;
  value_prop_3: string;
  cta_text: string;
  personalization_rationale?: string;
}

interface PersonalizedResultsProps {
  content: PersonalizedContent;
  metadata?: {
    persona?: string;
    buyer_stage?: string;
    company?: string;
    ai_priority?: string;
    industry?: string;
  };
}

export default function PersonalizedResults({
  content,
  metadata,
}: PersonalizedResultsProps) {
  return (
    <div
      data-testid="personalized-results"
      style={{
        width: '100%',
        maxWidth: '800px',
        margin: '0 auto',
      }}
    >
      {/* Metadata Badge */}
      {metadata && (
        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            flexWrap: 'wrap',
            marginBottom: '1.5rem',
          }}
        >
          {metadata.persona && (
            <span
              data-testid="metadata-persona"
              style={{
                padding: '0.25rem 0.75rem',
                backgroundColor: '#FEE2E2',
                color: '#DC2626',
                borderRadius: '9999px',
                fontSize: '0.875rem',
                fontWeight: '500',
              }}
            >
              {metadata.persona}
            </span>
          )}
          {metadata.buyer_stage && (
            <span
              data-testid="metadata-stage"
              style={{
                padding: '0.25rem 0.75rem',
                backgroundColor: '#FECACA',
                color: '#B91C1C',
                borderRadius: '9999px',
                fontSize: '0.875rem',
                fontWeight: '500',
              }}
            >
              {metadata.buyer_stage}
            </span>
          )}
          {metadata.company && (
            <span
              data-testid="metadata-company"
              style={{
                padding: '0.25rem 0.75rem',
                backgroundColor: '#FEF2F2',
                color: '#991B1B',
                borderRadius: '9999px',
                fontSize: '0.875rem',
                fontWeight: '500',
              }}
            >
              {metadata.company}
            </span>
          )}
          {metadata.ai_priority && (
            <span
              data-testid="metadata-ai-priority"
              style={{
                padding: '0.25rem 0.75rem',
                backgroundColor: '#FEE2E2',
                color: '#7C2D12',
                borderRadius: '9999px',
                fontSize: '0.875rem',
                fontWeight: '500',
              }}
            >
              {metadata.ai_priority}
            </span>
          )}
        </div>
      )}

      {/* Main Content Card */}
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          padding: '2.5rem',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          border: '1px solid #e5e7eb',
        }}
      >
        {/* Headline */}
        <h2
          data-testid="result-headline"
          style={{
            fontSize: '2rem',
            fontWeight: '700',
            color: '#111827',
            marginBottom: '1rem',
            lineHeight: '1.2',
          }}
        >
          {content.headline}
        </h2>

        {/* Subheadline */}
        <p
          data-testid="result-subheadline"
          style={{
            fontSize: '1.25rem',
            color: '#6b7280',
            marginBottom: '2rem',
            lineHeight: '1.6',
          }}
        >
          {content.subheadline}
        </p>

        {/* Value Propositions */}
        <div style={{ marginBottom: '2rem' }}>
          <h3
            style={{
              fontSize: '1.125rem',
              fontWeight: '600',
              color: '#374151',
              marginBottom: '1rem',
            }}
          >
            Key Benefits
          </h3>
          <div
            style={{
              display: 'grid',
              gap: '1.5rem',
            }}
          >
            {[content.value_prop_1, content.value_prop_2, content.value_prop_3].map((vp, index) => (
              <div
                key={index}
                data-testid={`value-prop-${index}`}
                style={{
                  display: 'flex',
                  gap: '1rem',
                  alignItems: 'start',
                }}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    backgroundColor: '#FEE2E2',
                    color: '#DC2626',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: '700',
                    flexShrink: 0,
                  }}
                >
                  {index + 1}
                </div>
                <div>
                  <p
                    style={{
                      fontSize: '0.875rem',
                      color: '#111827',
                      lineHeight: '1.5',
                    }}
                  >
                    {vp}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Button */}
        <button
          data-testid="result-cta"
          style={{
            width: '100%',
            padding: '1rem 2rem',
            backgroundColor: '#DC2626',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '1.125rem',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
          }}
          onMouseOver={(e) =>
            (e.currentTarget.style.backgroundColor = '#B91C1C')
          }
          onMouseOut={(e) =>
            (e.currentTarget.style.backgroundColor = '#DC2626')
          }
        >
          {content.cta_text}
        </button>
      </div>

      {/* Rationale (Debug Info) */}
      {content.personalization_rationale && (
        <div
          style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            fontSize: '0.875rem',
            color: '#6b7280',
            fontStyle: 'italic',
          }}
        >
          <strong>Personalization:</strong> {content.personalization_rationale}
        </div>
      )}
    </div>
  );
}
