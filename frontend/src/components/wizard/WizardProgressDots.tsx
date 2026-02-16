'use client';

import { TOTAL_STEPS, STEP_TITLES } from './wizardTypes';

interface WizardProgressDotsProps {
  currentStep: number;
}

export default function WizardProgressDots({ currentStep }: WizardProgressDotsProps) {
  return (
    <div className="mb-8">
      {/* Dots with connecting lines */}
      <div className="flex items-center justify-center gap-0">
        {Array.from({ length: TOTAL_STEPS }, (_, i) => (
          <div key={i} className="flex items-center">
            {/* Dot */}
            <div
              className={`
                w-3 h-3 rounded-full transition-all duration-300 flex-shrink-0
                ${i < currentStep
                  ? 'bg-[#00c8aa] shadow-[0_0_8px_rgba(0,200,170,0.4)]'
                  : i === currentStep
                    ? 'bg-[#00c8aa] shadow-[0_0_12px_rgba(0,200,170,0.5)] scale-125'
                    : 'bg-white/20'
                }
              `}
            />
            {/* Connecting line (not after last dot) */}
            {i < TOTAL_STEPS - 1 && (
              <div
                className={`
                  w-8 sm:w-12 h-0.5 transition-all duration-300
                  ${i < currentStep ? 'bg-[#00c8aa]/50' : 'bg-white/10'}
                `}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step label */}
      <div className="text-center mt-3">
        <span className="text-xs text-white/40 uppercase tracking-widest font-medium">
          Step {currentStep + 1} of {TOTAL_STEPS}
        </span>
        <span className="text-white/20 mx-2">|</span>
        <span className="text-xs text-white/50 font-medium">
          {STEP_TITLES[currentStep]}
        </span>
      </div>
    </div>
  );
}
