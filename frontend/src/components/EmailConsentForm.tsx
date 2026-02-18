'use client';

import { useState, useRef, FormEvent, useCallback, useEffect, useMemo } from 'react';
import WizardProgressDots from './wizard/WizardProgressDots';
import StepContainer from './wizard/StepContainer';
import SelectionCard from './wizard/SelectionCard';
import StepAboutYou from './wizard/steps/StepAboutYou';
import StepCompany from './wizard/steps/StepCompany';
import StepRole from './wizard/steps/StepRole';
import {
  WizardData,
  INITIAL_WIZARD_DATA,
  STEP_VALIDATORS,
  TOTAL_STEPS,
  SOCIAL_PROOF,
  STAGE_LABELS,
  ROLE_OPTIONS,
  INDUSTRY_OPTIONS,
  PersonaType,
  getPersonaType,
  getITEnvironmentOptions,
  getPriorityOptions,
  getFilteredChallenges,
  getEnvLabel,
  getPriorityLabel as getAdaptivePriorityLabel,
  getChallengeLabel,
  getAdaptiveStepTitle,
  getTransitionMessage,
  getIntelligenceNugget,
  getAssessmentDepth,
  saveWizardProgress,
  loadWizardProgress,
  clearWizardProgress,
  EnrichmentPreview,
  isWorkEmail,
  employeeCountToSize,
  normalizeEnrichmentIndustry,
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
  const envOptions = useMemo(
    () => getITEnvironmentOptions(personaType, data.industry),
    [personaType, data.industry],
  );
  const priorityOptions = useMemo(() => getPriorityOptions(personaType), [personaType]);
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

  // Social proof helper
  const getSocialProof = (field: string, value: string): string | null => {
    return SOCIAL_PROOF[`${field}:${value}`] || null;
  };

  // Display label helpers for assessment preview
  const getRoleLabel = () => ROLE_OPTIONS.find((r) => r.value === data.persona)?.label || 'your role';
  const getIndustryLabel = () =>
    INDUSTRY_OPTIONS.find((i) => i.value === data.industry)?.label || 'your industry';
  const getStageLabel = () => STAGE_LABELS[data.itEnvironment] || '';
  const getDisplayPriorityLabel = () => {
    return priorityOptions.find((p) => p.value === data.businessPriority)?.label || '';
  };

  const isLastStep = currentStep === TOTAL_STEPS - 1;

  // Progressive reveal state for Step 4
  const showPriority = !!data.itEnvironment;
  const showChallenge = !!data.businessPriority;
  const showPreview =
    currentStep === 3 && !!data.itEnvironment && !!data.businessPriority && !!data.challenge;

  // Keyboard navigation for Step 4 sub-sections
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

      // Target = the latest revealed section without a selection
      if (!data.itEnvironment) {
        if (num <= envOptions.length) {
          updateData({ itEnvironment: envOptions[num - 1].value, challenge: '' });
        }
      } else if (!data.businessPriority) {
        if (num <= priorityOptions.length) {
          updateData({ businessPriority: priorityOptions[num - 1].value });
        }
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
    data.businessPriority,
    data.challenge,
    envOptions,
    priorityOptions,
    challengeOptions,
    updateData,
  ]);

  return (
    <form onSubmit={handleSubmit}>
      <WizardProgressDots
        currentStep={currentStep}
        stepTitle={getAdaptiveStepTitle(currentStep, currentStep >= 3 ? personaType : undefined)}
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
              disabled={isLoading}
            />
          )}

          {/* Step 3: Role (auto-advances) */}
          {currentStep === 2 && (
            <StepRole
              data={data}
              onChange={updateData}
              onAutoAdvance={handleAutoAdvance}
              disabled={isLoading}
            />
          )}

          {/* Step 4: Your Situation — Progressive Reveal */}
          {currentStep === 3 && (
            <div className="space-y-5">
              {/* IT Environment — always visible on Step 4 */}
              <div>
                <label className="amd-label">{getEnvLabel(personaType)}</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {envOptions.map((opt) => (
                    <SelectionCard
                      key={opt.value}
                      label={opt.label}
                      description={opt.description}
                      selected={data.itEnvironment === opt.value}
                      onClick={() =>
                        updateData({
                          itEnvironment: opt.value,
                          challenge: data.itEnvironment !== opt.value ? '' : data.challenge,
                        })
                      }
                      disabled={isLoading}
                      size="lg"
                    />
                  ))}
                </div>
                {!data.itEnvironment && (
                  <p className="hidden sm:block text-[11px] text-white/25 mt-2 pl-1">
                    Press 1-{envOptions.length} to select
                  </p>
                )}
                {data.itEnvironment && (
                  <p className="social-proof-enter text-xs text-[#00c8aa]/70 mt-2 pl-1">
                    {getSocialProof('itEnvironment', data.itEnvironment)}
                  </p>
                )}
              </div>

              {/* Business Priority — revealed after env selection */}
              {showPriority && (
                <div className="progressive-reveal">
                  <label className="amd-label">{getAdaptivePriorityLabel(personaType)}</label>
                  <div className="grid grid-cols-3 gap-3">
                    {priorityOptions.map((opt) => (
                      <SelectionCard
                        key={opt.value}
                        label={opt.label}
                        description={opt.description}
                        selected={data.businessPriority === opt.value}
                        onClick={() => updateData({ businessPriority: opt.value })}
                        disabled={isLoading}
                        size="md"
                      />
                    ))}
                  </div>
                  {!data.businessPriority && (
                    <p className="hidden sm:block text-[11px] text-white/25 mt-2 pl-1">
                      Press 1-{priorityOptions.length} to select
                    </p>
                  )}
                  {data.businessPriority && (
                    <p className="social-proof-enter text-xs text-[#00c8aa]/70 mt-2 pl-1">
                      {getSocialProof('businessPriority', data.businessPriority)}
                    </p>
                  )}
                </div>
              )}

              {/* Challenge — revealed after priority selection */}
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

              {/* Assessment Preview — after all selections made */}
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
                      {getDisplayPriorityLabel()}
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
