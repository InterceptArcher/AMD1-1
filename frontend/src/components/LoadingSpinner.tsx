interface LoadingSpinnerProps {
  message?: string;
}

export default function LoadingSpinner({ message = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex flex-col items-center justify-center space-y-6 py-12"
    >
      {/* Animated dots */}
      <div className="flex space-x-2">
        <div className="h-3 w-3 animate-bounce rounded-full bg-blue-600 [animation-delay:-0.3s]" />
        <div className="h-3 w-3 animate-bounce rounded-full bg-blue-600 [animation-delay:-0.15s]" />
        <div className="h-3 w-3 animate-bounce rounded-full bg-blue-600" />
      </div>

      {/* Progress card */}
      <div className="w-full max-w-sm rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 animate-pulse rounded-full bg-blue-100 flex items-center justify-center">
              <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900">{message}</p>
              <p className="text-sm text-gray-500">This usually takes a few seconds</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="h-2 overflow-hidden rounded-full bg-gray-100">
            <div className="h-full w-2/3 animate-pulse rounded-full bg-gradient-to-r from-blue-500 to-indigo-500" />
          </div>
        </div>
      </div>
    </div>
  );
}
