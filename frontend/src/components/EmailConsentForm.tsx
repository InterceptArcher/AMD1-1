'use client';

import { useState, FormEvent, useCallback } from 'react';
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
  TRANSITION_MESSAGES,
  SOCIAL_PROOF,
  STAGE_LABELS,
  IT_ENVIRONMENT_OPTIONS,
  BUSINESS_PRIORITY_OPTIONS,
  ROLE_OPTIONS,
  INDUSTRY_OPTIONS,
  getFilteredChallenges,
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

  const updateData = (updates: Partial<WizardData>) => {
    setData((prev) => ({ ...prev, ...updates }));
  };

  const isCurrentStepValid = STEP_VALIDATORS[currentStep](data);

  // Transition with thinking moment
  const startTransition = useCallback((fromStep: number, nextStep: number) => {
    setTransitionMessage(TRANSITION_MESSAGES[fromStep] || 'Processing...');
    setWizardState('thinking');
    setTimeout(() => {
      setWizardState('idle');
      setDirection('forward');
      setCurrentStep(nextStep);
    }, 900);
  }, []);

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

  // Auto-advance for single-select steps (Role)
  const handleAutoAdvance = useCallback(() => {
    startTransition(2, 3); // Step 3 (role) → Step 4 (situation)
  }, [startTransition]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isCurrentStepValid) {
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
  const getIndustryLabel = () => INDUSTRY_OPTIONS.find((i) => i.value === data.industry)?.label || 'your industry';
  const getStageLabel = () => STAGE_LABELS[data.itEnvironment] || '';
  const getPriorityLabel = () => BUSINESS_PRIORITY_OPTIONS.find((p) => p.value === data.businessPriority)?.label || '';

  const isLastStep = currentStep === TOTAL_STEPS - 1;
  const filteredChallenges = getFilteredChallenges(data.itEnvironment);

  // Assessment preview is shown when enough fields are filled on step 4
  const showPreview = currentStep === 3 && data.itEnvironment && data.businessPriority && data.challenge;

  return (
    <form onSubmit={handleSubmit}>
      <WizardProgressDots currentStep={currentStep} />

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
              disabled={isLoading}
            />
          )}

          {/* Step 2: Company */}
          {currentStep === 1 && (
            <StepCompany
              data={data}
              onChange={updateData}
              companyAutoFilled={companyAutoFilled}
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

          {/* Step 4: Your Situation */}
          {currentStep === 3 && (
            <div className="space-y-5">
              {/* IT Environment */}
              <div>
                <label className="amd-label">Which sounds most like your day-to-day?</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {IT_ENVIRONMENT_OPTIONS.map((opt) => (
                    <SelectionCard
                      key={opt.value}
                      label={opt.label}
                      description={opt.description}
                      selected={data.itEnvironment === opt.value}
                      onClick={() => updateData({ itEnvironment: opt.value, challenge: data.itEnvironment !== opt.value ? '' : data.challenge })}
                      disabled={isLoading}
                      size="lg"
                    />
                  ))}
                </div>
                {data.itEnvironment && (
                  <p className="social-proof-enter text-xs text-[#00c8aa]/70 mt-2 pl-1">
                    {getSocialProof('itEnvironment', data.itEnvironment)}
                  </p>
                )}
              </div>

              {/* Business Priority */}
              <div>
                <label className="amd-label">If you could change one thing tomorrow...</label>
                <div className="grid grid-cols-3 gap-3">
                  {BUSINESS_PRIORITY_OPTIONS.map((opt) => (
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
                {data.businessPriority && (
                  <p className="social-proof-enter text-xs text-[#00c8aa]/70 mt-2 pl-1">
                    {getSocialProof('businessPriority', data.businessPriority)}
                  </p>
                )}
              </div>

              {/* Challenge (adaptive filtering) */}
              <div>
                <label className="amd-label">What&apos;s the biggest thing holding your team back?</label>
                <div className={`grid grid-cols-2 ${filteredChallenges.length <= 4 ? 'sm:grid-cols-4' : 'sm:grid-cols-5'} gap-2`}>
                  {filteredChallenges.map((opt) => (
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
                {data.challenge && (
                  <p className="social-proof-enter text-xs text-[#00c8aa]/70 mt-2 pl-1">
                    {getSocialProof('challenge', data.challenge)}
                  </p>
                )}
              </div>

              {/* Assessment Preview */}
              {showPreview && (
                <div className="assessment-preview social-proof-enter rounded-xl border border-[#00c8aa]/20 p-4">
                  <div className="flex items-center gap-2 mb-2.5">
                    <div className="w-5 h-5 rounded-full bg-[#00c8aa]/20 flex items-center justify-center">
                      <svg className="w-3 h-3 text-[#00c8aa]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
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
                    <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-white/50">{getIndustryLabel()}</span>
                    <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-white/50">{getStageLabel()} Stage</span>
                    <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-white/50">{getPriorityLabel()}</span>
                  </div>
                </div>
              )}

              {/* Consent */}
              <div className="flex items-start gap-3 pt-1">
                <input
                  type="checkbox"
                  id="wiz-consent"
                  checked={data.consent}
                  onChange={(e) => updateData({ consent: e.target.checked })}
                  disabled={isLoading}
                  className="amd-checkbox mt-0.5"
                />
                <label htmlFor="wiz-consent" className="text-sm text-white/70 leading-relaxed cursor-pointer">
                  I agree to receive my personalized AI readiness assessment and relevant updates from AMD
                </label>
              </div>
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
