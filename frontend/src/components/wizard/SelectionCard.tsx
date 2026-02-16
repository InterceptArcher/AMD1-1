'use client';

interface SelectionCardProps {
  label: string;
  description?: string;
  selected: boolean;
  onClick: () => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

export default function SelectionCard({
  label,
  description,
  selected,
  onClick,
  disabled = false,
  size = 'md',
  icon,
}: SelectionCardProps) {
  const sizeClasses = {
    sm: 'px-3 py-2.5',
    md: 'px-4 py-3.5',
    lg: 'px-5 py-5',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`
        relative w-full h-full text-left rounded-xl border transition-all duration-200 cursor-pointer overflow-hidden
        ${sizeClasses[size]}
        ${selected
          ? 'selection-card-selected'
          : 'border-white/15 bg-white/[0.04] hover:border-white/30 hover:bg-white/[0.08]'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      {selected && (
        <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-[#00c8aa] flex items-center justify-center">
          <svg className="w-3 h-3 text-[#0a0a12]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}

      <div className="flex items-start gap-3 pr-5">
        {icon && (
          <div className={`flex-shrink-0 ${selected ? 'text-[#00c8aa]' : 'text-white/50'} transition-colors`}>
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <div className={`font-semibold leading-snug ${selected ? 'text-white' : 'text-white/80'} ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
            {label}
          </div>
          {description && (
            <div className={`mt-0.5 leading-snug ${selected ? 'text-white/60' : 'text-white/40'} ${size === 'sm' ? 'text-[11px]' : 'text-xs'}`}>
              {description}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
