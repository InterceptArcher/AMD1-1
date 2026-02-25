'use client';

import { useState, useRef, FormEvent, useCallback, useEffect, useMemo } from 'react';
import WizardProgressDots from './wizard/WizardProgressDots';
import StepContainer from './wizard/StepContainer';
import SelectionCard from './wizard/SelectionCard';
import StepAboutYou from './wizard/steps/StepAboutYou';
import StepCompany from './wizard/steps/StepCompany';
import StepRole from './wizard/steps/StepRole';
import LivePreviewCard from './wizard/LivePreviewCard';
import {
  WizardData,
  INITIAL_WIZARD_DATA,
  STEP_VALIDATORS,
  TOTAL_STEPS,
  STAGE_LABELS,
  ROLE_OPTIONS,
  INDUSTRY_OPTIONS,
  PersonaType,
  getPersonaType,
  getFilteredChallenges,
  getScenarioLabel,
  getChallengeLabel,
  getAdaptiveStepTitle,
  getTransitionMessage,
  getIntelligenceNugget,
  getAssessmentDepth,
  saveWizardProgress,
  loadWizardProgress,
  clearWizardProgress,
  EnrichmentPreview,
  SCENARIO_OPTIONS,
  STAGE_REVEAL_COPY,
  employeeCountToSize,
  normalizeEnrichmentIndustry,
  mapSeniorityToRole,
} from './wizard/wizardTypes';

export interface UserInputs {
  email: string;
  firstName: string;
  lastName: string;
  company: string;
  companySize: string;
  goal: string;
  persona: string;
  industry: string;
  itEnvironment: string;
  businessPriority: string;
  challenge: string;
}

interface EmailConsentFormProps {
  onSubmit: (inputs: UserInputs) => void;
  isLoading?: boolean;
}

export default function EmailConsentForm({ onSubmit, isLoading = false }: EmailConsentFormProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState<'forward' | 'back'>('forward');
  const [data, setData] = useState<WizardData>(INITIAL_WIZARD_DATA);
  const [wizardState, setWizardState] = useState<'idle' | 'thinking'>('idle');
  const [transitionMessage, setTransitionMessage] = useState('');
  const [companyAutoFilled, setCompanyAutoFilled] = useState(false);
  const [enrichmentData, setEnrichmentData] = useState<EnrichmentPreview | null>(null);
  const [enrichmentLoading, setEnrichmentLoading] = useState(false);
  const lastEnrichedEmailRef = useRef('');

  // Derived persona type from role selection
  const personaType: PersonaType = useMemo(() => getPersonaType(data.persona), [data.persona]);

  // Adaptive options based on persona and industry
  const scenarioOptions = useMemo(
    () => SCENARIO_OPTIONS[personaType],
    [personaType],
  );
  const challengeOptions = useMemo(
    () => getFilteredChallenges(data.itEnvironment, data.industry),
    [data.itEnvironment, data.industry],
  );

  // Assessment depth indicator
  const assessmentDepth = useMemo(() => getAssessmentDepth(data), [data]);

  // Intelligence nugget for industry + challenge
  const nugget = useMemo(
    () => getIntelligenceNugget(data.industry, data.challenge),
    [data.industry, data.challenge],
  );

  // Stable updateData via useCallback (needed for keyboard effect deps)
  const updateData = useCallback((updates: Partial<WizardData>) => {
    setData((prev) => ({ ...prev, ...updates }));
  }, []);

  // Fire quick-enrich API when a valid work email is entered
  const handleEmailEnrich = useCallback(async (email: string) => {
    if (!email || email === lastEnrichedEmailRef.current) return;
    lastEnrichedEmailRef.current = email;

    setEnrichmentLoading(true);
    try {
      const resp = await fetch('/api/rad/quick-enrich', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (resp.ok) {
        const result = await resp.json();
        if (result.found) {
          setEnrichmentData(result);
          // Pre-fill empty fields from enrichment
          setData((prev) => {
            const updates: Partial<WizardData> = {};
            if (!prev.company && result.company_name) {
              updates.company = result.company_name;
            }
            if (!prev.companySize && result.employee_count) {
              updates.companySize = employeeCountToSize(result.employee_count);
            }
            if (!prev.industry && result.industry) {
              updates.industry = normalizeEnrichmentIndustry(result.industry);
            }
            // Pre-fill role from seniority + title
            if (!prev.persona && result.seniority && result.title) {
              const mapped = mapSeniorityToRole(result.seniority, result.title);
              if (mapped) updates.persona = mapped;
            }
            if (Object.keys(updates).length === 0) return prev;
            return { ...prev, ...updates };
          });
          setCompanyAutoFilled(true);
        }
      }
    } catch {
      // Silently fail — enrichment is a nice-to-have
    } finally {
      setEnrichmentLoading(false);
    }
  }, []);

  // localStorage: restore on mount
  useEffect(() => {
    const saved = loadWizardProgress();
    if (saved) {
      setData(saved.data);
      setCurrentStep(saved.step);
    }
  }, []);

  // localStorage: auto-save on meaningful changes
  useEffect(() => {
    if (currentStep > 0 || data.firstName) {
      saveWizardProgress(currentStep, data);
    }
  }, [currentStep, data]);

  const isCurrentStepValid = STEP_VALIDATORS[currentStep](data);

  // Transition with contextual thinking moment
  const startTransition = useCallback(
    (fromStep: number, nextStep: number) => {
      setTransitionMessage(getTransitionMessage(fromStep, data));
      setWizardState('thinking');
      setTimeout(() => {
        setWizardState('idle');
        setDirection('forward');
        setCurrentStep(nextStep);
      }, 900);
    },
    [data],
  );

  const goNext = () => {
    if (currentStep < TOTAL_STEPS - 1 && isCurrentStepValid) {
      startTransition(currentStep, currentStep + 1);
    }
  };

  const goBack = () => {
    if (currentStep > 0) {
      setDirection('back');
      setCurrentStep((s) => s - 1);
    }
  };

  // Auto-advance for single-select steps (Role → Situation)
  const handleAutoAdvance = useCallback(() => {
    startTransition(2, 3);
  }, [startTransition]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isCurrentStepValid) {
      clearWizardProgress();
      onSubmit({
        email: data.email,
        firstName: data.firstName,
        lastName: data.lastName,
        company: data.company,
        companySize: data.companySize,
        goal: 'consideration',
        persona: data.persona,
        industry: data.industry,
        itEnvironment: data.itEnvironment,
        businessPriority: data.businessPriority,
        challenge: data.challenge,
      });
    }
  };

  // Display label helpers for assessment preview
  const getRoleLabel = () => ROLE_OPTIONS.find((r) => r.value === data.persona)?.label || 'your role';
  const getIndustryLabel = () =>
    INDUSTRY_OPTIONS.find((i) => i.value === data.industry)?.label || 'your industry';
  const getStageLabel = () => STAGE_LABELS[data.itEnvironment] || '';
  const getSelectedScenarioLabel = () =>
    scenarioOptions.find((s) => s.itEnvironment === data.itEnvironment)?.label || '';

  const isLastStep = currentStep === TOTAL_STEPS - 1;

  // Progressive reveal state for Step 4
  const showChallenge = !!data.itEnvironment; // scenario selected → show challenge
  const showStageReveal = !!data.itEnvironment && !!data.challenge; // scenario + challenge → stage reveal
  const showPreview =
    currentStep === 3 && showStageReveal;

  // Keyboard navigation for Step 4 sub-sections (2 sections: scenario, challenge)
  useEffect(() => {
    if (currentStep !== 3 || wizardState !== 'idle') return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      const num = parseInt(e.key);
      if (isNaN(num) || num < 1) return;

      // Section 1: Scenario (sets itEnvironment + businessPriority)
      if (!data.itEnvironment) {
        if (num <= scenarioOptions.length) {
          const scenario = scenarioOptions[num - 1];
          updateData({
            itEnvironment: scenario.itEnvironment,
            businessPriority: scenario.businessPriority,
            challenge: '',
          });
        }
      // Section 2: Challenge
      } else if (!data.challenge) {
        if (num <= challengeOptions.length) {
          updateData({ challenge: challengeOptions[num - 1].value });
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    currentStep,
    wizardState,
    data.itEnvironment,
    data.challenge,
    scenarioOptions,
    challengeOptions,
    updateData,
  ]);

  return (
    <form onSubmit={handleSubmit}>
      <WizardProgressDots
        currentStep={currentStep}
        stepTitle={getAdaptiveStepTitle(
          currentStep,
          currentStep >= 3 ? personaType : undefined,
          data.company || undefined,
        )}
      />

      {/* Assessment depth indicator on Step 4 */}
      {currentStep === 3 && wizardState === 'idle' && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] text-white/40 uppercase tracking-widest font-semibold">
              Assessment Depth
            </span>
            <span className="text-[11px] text-[#00c8aa]/70 font-semibold">
              {assessmentDepth.percentage}%
            </span>
          </div>
          <div className="h-1 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#00c8aa] rounded-full transition-all duration-500 ease-out"
              style={{ width: `${assessmentDepth.percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Thinking overlay between steps */}
      {wizardState === 'thinking' ? (
        <div className="thinking-overlay flex flex-col items-center justify-center py-16">
          <div className="w-8 h-8 border-2 border-[#00c8aa] border-t-transparent rounded-full animate-spin mb-4" />
          <p className="thinking-text text-white/50 text-sm font-medium">{transitionMessage}</p>
        </div>
      ) : (
        <StepContainer direction={direction} stepKey={currentStep}>
          {/* Step 1: About You */}
          {currentStep === 0 && (
            <StepAboutYou
              data={data}
              onChange={updateData}
              onCompanySuggested={() => setCompanyAutoFilled(true)}
              onEmailValidated={handleEmailEnrich}
              disabled={isLoading}
            />
          )}

          {/* Step 2: Company */}
          {currentStep === 1 && (
            <StepCompany
              data={data}
              onChange={updateData}
              companyAutoFilled={companyAutoFilled}
              enrichmentData={enrichmentData}
              enrichmentLoading={enrichmentLoading}
              email={data.email}
              disabled={isLoading}
            />
          )}

          {/* Step 3: Role (auto-advances) */}
          {currentStep === 2 && (
            <StepRole
              data={data}
              onChange={updateData}
              onAutoAdvance={handleAutoAdvance}
              suggestedRole={enrichmentData?.seniority && enrichmentData?.title
                ? mapSeniorityToRole(enrichmentData.seniority, enrichmentData.title) ?? undefined
                : undefined}
              disabled={isLoading}
            />
          )}

          {/* Step 4: Your Situation — Scenario Cards → Challenge → Stage Reveal */}
          {currentStep === 3 && (
            <div className="space-y-5">
              {/* Scenario Cards — always visible on Step 4 */}
              <div>
                <label className="amd-label">{getScenarioLabel(personaType)}</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {scenarioOptions.map((scenario) => (
                    <SelectionCard
                      key={scenario.itEnvironment}
                      label={scenario.label}
                      description={scenario.description}
                      selected={data.itEnvironment === scenario.itEnvironment}
                      onClick={() =>
                        updateData({
                          itEnvironment: scenario.itEnvironment,
                          businessPriority: scenario.businessPriority,
                          challenge: data.itEnvironment !== scenario.itEnvironment ? '' : data.challenge,
                        })
                      }
                      disabled={isLoading}
                      size="lg"
                    />
                  ))}
                </div>
                {!data.itEnvironment && (
                  <p className="hidden sm:block text-[11px] text-white/25 mt-2 pl-1">
                    Press 1-{scenarioOptions.length} to select
                  </p>
                )}
              </div>

              {/* Challenge — revealed after scenario selection */}
              {showChallenge && (
                <div className="progressive-reveal">
                  <label className="amd-label">{getChallengeLabel(personaType)}</label>
                  <div
                    className={`grid grid-cols-2 ${challengeOptions.length <= 4 ? 'sm:grid-cols-4' : 'sm:grid-cols-5'} gap-2`}
                  >
                    {challengeOptions.map((opt) => (
                      <SelectionCard
                        key={opt.value}
                        label={opt.label}
                        description={opt.description}
                        selected={data.challenge === opt.value}
                        onClick={() => updateData({ challenge: opt.value })}
                        disabled={isLoading}
                        size="sm"
                      />
                    ))}
                  </div>
                  {!data.challenge && (
                    <p className="hidden sm:block text-[11px] text-white/25 mt-2 pl-1">
                      Press 1-{challengeOptions.length} to select
                    </p>
                  )}
                  {/* Intelligence nugget after challenge selection */}
                  {data.challenge && nugget && (
                    <p className="social-proof-enter text-xs text-[#00c8aa]/70 mt-2 pl-1 italic">
                      {nugget}
                    </p>
                  )}
                </div>
              )}

              {/* Stage Reveal — animated card after scenario + challenge */}
              {showStageReveal && STAGE_REVEAL_COPY[getStageLabel()] && (
                <div className="stage-reveal rounded-xl border border-[#00c8aa]/30 bg-[#00c8aa]/[0.04] p-5">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className="w-6 h-6 rounded-full bg-[#00c8aa]/20 flex items-center justify-center">
                      <svg
                        className="w-3.5 h-3.5 text-[#00c8aa]"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                    <span className="text-sm font-bold text-[#00c8aa]">
                      {STAGE_REVEAL_COPY[getStageLabel()].title}
                    </span>
                  </div>
                  <p className="text-white/70 text-sm leading-relaxed mb-3">
                    {STAGE_REVEAL_COPY[getStageLabel()].description}
                  </p>
                  <p className="text-[11px] text-white/40 italic">
                    {STAGE_REVEAL_COPY[getStageLabel()].stat}
                  </p>
                </div>
              )}

              {/* Assessment Preview — after stage reveal */}
              {showPreview && (
                <div className="progressive-reveal assessment-preview rounded-xl border border-[#00c8aa]/20 p-4">
                  <div className="flex items-center gap-2 mb-2.5">
                    <div className="w-5 h-5 rounded-full bg-[#00c8aa]/20 flex items-center justify-center">
                      <svg
                        className="w-3 h-3 text-[#00c8aa]"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <span className="text-xs text-[#00c8aa] uppercase tracking-widest font-bold">
                      Assessment Preview
                    </span>
                  </div>
                  <p className="text-white/80 text-sm">
                    Personalized for a <strong className="text-white">{getRoleLabel()}</strong> at{' '}
                    <strong className="text-white">{data.company || 'your company'}</strong>
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-2.5">
                    <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-white/50">
                      {getIndustryLabel()}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-white/50">
                      {getStageLabel()} Stage
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-white/50">
                      {getSelectedScenarioLabel()}
                    </span>
                  </div>
                </div>
              )}

              {/* Consent — appears with preview */}
              {showPreview && (
                <div className="progressive-reveal flex items-start gap-3 pt-1">
                  <input
                    type="checkbox"
                    id="wiz-consent"
                    checked={data.consent}
                    onChange={(e) => updateData({ consent: e.target.checked })}
                    disabled={isLoading}
                    className="amd-checkbox mt-0.5"
                  />
                  <label
                    htmlFor="wiz-consent"
                    className="text-sm text-white/70 leading-relaxed cursor-pointer"
                  >
                    I agree to receive my personalized AI readiness assessment and relevant updates
                    from AMD
                  </label>
                </div>
              )}
            </div>
          )}
        </StepContainer>
      )}

      {/* Live Preview Card — shows on Steps 1-2 */}
      {wizardState === 'idle' && (currentStep === 1 || currentStep === 2) && (
        <LivePreviewCard data={data} />
      )}

      {/* Navigation buttons */}
      {wizardState === 'idle' && (
        <div className="flex items-center gap-3 mt-8">
          {currentStep > 0 && (
            <button
              type="button"
              onClick={goBack}
              disabled={isLoading}
              className="px-5 py-3.5 rounded-lg border border-white/20 text-white/70 hover:text-white hover:border-white/30 hover:bg-white/[0.05] transition-all duration-200 text-sm font-medium"
            >
              Back
            </button>
          )}

          {!isLastStep ? (
            <button
              type="button"
              onClick={goNext}
              disabled={!isCurrentStepValid || isLoading}
              className="amd-button-primary flex-1"
            >
              Continue
            </button>
          ) : (
            <button
              type="submit"
              disabled={!isCurrentStepValid || isLoading}
              className="amd-button-primary flex-1"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-3">
                  <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Generating Your Assessment...
                </span>
              ) : (
                'Get Your AI Readiness Snapshot'
              )}
            </button>
          )}
        </div>
      )}
    </form>
  );
}
