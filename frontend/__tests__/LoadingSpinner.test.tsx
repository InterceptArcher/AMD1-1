import { render, screen, act } from '@testing-library/react';
import LoadingSpinner from '../src/components/LoadingSpinner';

// Use fake timers for all tests
beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('LoadingSpinner', () => {
  it('renders loading spinner', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('displays loading message', () => {
    render(<LoadingSpinner message="Personalizing your content..." />);
    expect(screen.getByText(/personalizing/i)).toBeInTheDocument();
  });

  it('has accessible label for screen readers', () => {
    render(<LoadingSpinner />);
    expect(screen.getByLabelText(/loading/i)).toBeInTheDocument();
  });

  describe('adaptive timing (overtime behavior)', () => {
    const userContext = {
      firstName: 'Ritzia',
      company: 'Acme Corp',
      industry: 'technology',
      persona: 'cto',
    };

    it('shows personalized greeting initially', () => {
      render(<LoadingSpinner userContext={userContext} />);
      expect(screen.getByText(/Ritzia.*Acme Corp/)).toBeInTheDocument();
    });

    it('advances through primary steps on interval', () => {
      render(<LoadingSpinner userContext={userContext} />);

      // After 2 seconds, should advance to next step
      act(() => { jest.advanceTimersByTime(2000); });
      expect(screen.getByText(/Analyzing your IT environment/i)).toBeInTheDocument();
    });

    it('continues showing new messages after primary steps are exhausted', () => {
      render(<LoadingSpinner userContext={userContext} />);

      // Primary steps for this context: greeting + 2 analysis + 3 industry + 1 persona + 4 final = 11
      // At 2s per step, all 11 steps take ~22 seconds
      // Advance well past that point (40 seconds)
      act(() => { jest.advanceTimersByTime(40000); });

      // Should NOT be stuck on "Finalizing your executive review..."
      // Should be showing an overtime message instead
      const finalizing = screen.queryByText('Finalizing your executive review...');
      expect(finalizing).not.toBeInTheDocument();
    });

    it('shows overtime messages that cycle without freezing', () => {
      render(<LoadingSpinner userContext={userContext} />);

      // Advance past all primary steps (30s should be enough)
      act(() => { jest.advanceTimersByTime(30000); });

      // Should be showing one of the overtime messages
      const overtimePatterns = [
        /Cross-referencing/i, /Fine-tuning/i, /Applying latest/i,
        /Validating insights/i, /Optimizing content/i, /Running final/i,
        /Polishing/i, /Double-checking/i, /Reviewing case study/i, /Assembling/i,
      ];
      const foundOvertime = overtimePatterns.some(
        (pattern) => screen.queryByText(pattern) !== null
      );
      expect(foundOvertime).toBe(true);

      // Advance more time - a different overtime message should appear
      act(() => { jest.advanceTimersByTime(8000); });

      const foundOvertimeAfter = overtimePatterns.some(
        (pattern) => screen.queryByText(pattern) !== null
      );
      expect(foundOvertimeAfter).toBe(true);
    });

    it('uses time-based progress that never reaches 100%', () => {
      render(<LoadingSpinner userContext={userContext} />);

      // Advance to 60 seconds (well past all steps)
      act(() => { jest.advanceTimersByTime(60000); });

      // Progress should still be below 95% (asymptotic, never "done")
      const progressText = screen.getByText(/% complete/);
      const percentMatch = progressText.textContent?.match(/(\d+)%/);
      expect(percentMatch).toBeTruthy();

      const percent = parseInt(percentMatch![1]);
      expect(percent).toBeGreaterThan(50); // Should have progressed significantly
      expect(percent).toBeLessThan(95);    // Should never hit 95%+
    });

    it('shows "refining" state in step counter during overtime', () => {
      render(<LoadingSpinner userContext={userContext} />);

      // Advance past all primary steps
      act(() => { jest.advanceTimersByTime(40000); });

      // Should no longer show "Step X of Y" format
      // Instead should indicate refinement/overtime state
      expect(screen.queryByText(/Step \d+ of \d+/)).not.toBeInTheDocument();
    });
  });
});
