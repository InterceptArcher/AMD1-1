'use client';

interface Advantage {
  headline: string;
  description: string;
}

interface Risk {
  headline: string;
  description: string;
}

interface Recommendation {
  title: string;
  description: string;
}

interface ExecutiveReviewData {
  company_name: string;
  stage: string;
  stage_sidebar: string;
  stage_identification_text?: string;
  executive_summary?: string;
  advantages: Advantage[];
  risks: Risk[];
  recommendations: Recommendation[];
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

interface ExecutiveReviewDisplayProps {
  data: ExecutiveReviewData;
  inputs: ExecutiveReviewInputs;
  onReset?: () => void;
}

export default function ExecutiveReviewDisplay({ data, inputs, onReset }: ExecutiveReviewDisplayProps) {
  // Stage-specific colors
  const stageColors: Record<string, { bg: string; text: string; border: string }> = {
    Observer: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
    Challenger: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
    Leader: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  };

  const colors = stageColors[data.stage] || stageColors.Challenger;

  return (
    <div className="amd-card overflow-hidden">
      {/* Header */}
      <div className="relative px-8 py-8 border-b border-white/10">
        <div className="absolute inset-0 bg-gradient-to-br from-[#00c8aa]/15 via-transparent to-transparent" />

        <div className="relative">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-white">
              Enterprise AI Readiness Snapshot for{' '}
              <span className="text-[#00c8aa]">{data.company_name}</span>
            </h1>
          </div>

          {/* Input Summary Pills */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="px-2 py-1 rounded bg-white/10 text-white/70">{inputs.industry}</span>
            <span className="px-2 py-1 rounded bg-white/10 text-white/70">{inputs.segment}</span>
            <span className="px-2 py-1 rounded bg-white/10 text-white/70">{inputs.persona}</span>
            <span className="px-2 py-1 rounded bg-white/10 text-white/70">{inputs.priority}</span>
            <span className="px-2 py-1 rounded bg-white/10 text-white/70">{inputs.challenge}</span>
          </div>
        </div>
      </div>

      <div className="px-8 py-6 space-y-8">
        {/* Executive Summary */}
        {data.executive_summary && (
          <section>
            <p className="text-base text-white/80 leading-relaxed">{data.executive_summary}</p>
          </section>
        )}

        {/* Stage Identification */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[#00c8aa]/20 flex items-center justify-center text-xs text-[#00c8aa] font-bold">1</span>
            Your Current Modernization Stage
          </h2>

          <div className={`rounded-xl ${colors.bg} ${colors.border} border p-5`}>
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-2xl font-bold ${colors.text}`}>{data.stage}</span>
            </div>
            {data.stage_identification_text && (
              <p className="text-sm text-white/80 mb-2">{data.stage_identification_text}</p>
            )}
            <p className={`text-sm ${colors.text}`}>{data.stage_sidebar}</p>
          </div>
        </section>

        {/* Advantages & Risks */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[#00c8aa]/20 flex items-center justify-center text-xs text-[#00c8aa] font-bold">2</span>
            What This Means for {data.company_name}
          </h2>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Advantages */}
            <div>
              <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-wide mb-3">Advantages</h3>
              <div className="space-y-4">
                {data.advantages.map((adv, idx) => (
                  <div key={idx} className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-4">
                    <h4 className="font-semibold text-white text-sm mb-2">{adv.headline}</h4>
                    <p className="text-sm text-white/70 leading-relaxed">{adv.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Risks */}
            <div>
              <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wide mb-3">Risks</h3>
              <div className="space-y-4">
                {data.risks.map((risk, idx) => (
                  <div key={idx} className="rounded-lg bg-red-500/5 border border-red-500/20 p-4">
                    <h4 className="font-semibold text-white text-sm mb-2">{risk.headline}</h4>
                    <p className="text-sm text-white/70 leading-relaxed">{risk.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Recommendations */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[#00c8aa]/20 flex items-center justify-center text-xs text-[#00c8aa] font-bold">3</span>
            Your Recommended Actions
          </h2>

          <div className="space-y-4">
            {data.recommendations.map((rec, idx) => (
              <div key={idx} className="rounded-lg bg-white/[0.03] border border-white/10 p-5">
                <div className="flex items-start gap-4">
                  <span className="w-8 h-8 rounded-lg bg-[#00c8aa]/15 flex items-center justify-center text-[#00c8aa] font-bold text-sm flex-shrink-0">
                    {idx + 1}
                  </span>
                  <div>
                    <h4 className="font-semibold text-white mb-2">{rec.title}</h4>
                    <p className="text-sm text-white/70 leading-relaxed">{rec.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Case Study */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[#00c8aa]/20 flex items-center justify-center text-xs text-[#00c8aa] font-bold">4</span>
            How Organizations Modernize with AMD
          </h2>

          <div className="rounded-xl bg-gradient-to-r from-[#00c8aa]/10 via-[#00c8aa]/5 to-transparent border border-[#00c8aa]/20 p-6">
            <h3 className="font-semibold text-[#00c8aa] mb-2">{data.case_study}</h3>
            <p className="text-sm text-white/70 leading-relaxed">{data.case_study_description}</p>
            {data.case_study_relevance && (
              <p className="text-sm text-white/50 italic mt-2">{data.case_study_relevance}</p>
            )}
            {data.case_study_link ? (
              <a
                href={data.case_study_link}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-block text-sm text-[#00c8aa] font-medium hover:underline"
              >
                Read the case study &rarr;
              </a>
            ) : (
              <span className="mt-4 inline-block text-sm text-[#00c8aa]/50 font-medium">
                Read the case study &rarr;
              </span>
            )}
          </div>
        </section>

        {/* Reset Button */}
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
