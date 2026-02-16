'use client';

interface StepContainerProps {
  children: React.ReactNode;
  direction: 'forward' | 'back';
  stepKey: number;
}

export default function StepContainer({ children, direction, stepKey }: StepContainerProps) {
  return (
    <div
      key={stepKey}
      className={direction === 'forward' ? 'wizard-slide-right' : 'wizard-slide-left'}
    >
      {children}
    </div>
  );
}
