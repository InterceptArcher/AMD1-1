import {
  deduceFromSignals,
  SIGNAL_QUESTIONS,
  SignalDeduction,
} from '../src/components/wizard/wizardTypes';

describe('deduceFromSignals', () => {
  // Helper: build answers from option indices (0-based) for each question
  function buildAnswers(indices: number[]): Record<string, string> {
    const answers: Record<string, string> = {};
    SIGNAL_QUESTIONS.forEach((q, i) => {
      if (indices[i] !== undefined) {
        // Use technical framing options by default
        answers[q.id] = q.options.technical[indices[i]].value;
      }
    });
    return answers;
  }

  it('returns all 3 fields: itEnvironment, businessPriority, confidence', () => {
    const result = deduceFromSignals(buildAnswers([0, 0, 0, 0]));
    expect(result).toHaveProperty('itEnvironment');
    expect(result).toHaveProperty('businessPriority');
    expect(result).toHaveProperty('confidence');
  });

  it('confidence is between 0 and 1', () => {
    const result = deduceFromSignals(buildAnswers([0, 0, 0, 0]));
    expect(result.confidence).toBeGreaterThanOrEqual(0);
    expect(result.confidence).toBeLessThanOrEqual(1);
  });

  // ===== All 9 combos must be reachable =====

  it('reaches traditional + reducing_cost', () => {
    // Q1: legacy, Q2: no AI, Q3: cost-focused, Q4: maintaining
    const result = deduceFromSignals(buildAnswers([0, 0, 0, 0]));
    expect(result.itEnvironment).toBe('traditional');
    expect(result.businessPriority).toBe('reducing_cost');
  });

  it('reaches traditional + improving_performance', () => {
    // Q1: legacy, Q2: no AI, Q3: performance-focused, Q4: maintaining
    const result = deduceFromSignals(buildAnswers([0, 0, 1, 0]));
    expect(result.itEnvironment).toBe('traditional');
    expect(result.businessPriority).toBe('improving_performance');
  });

  it('reaches traditional + preparing_ai', () => {
    // Q1: legacy (strong traditional), Q2: experimenting (adds some preparing_ai), Q3: AI-focused (strong preparing_ai), Q4: maintaining
    const result = deduceFromSignals(buildAnswers([0, 1, 2, 0]));
    expect(result.itEnvironment).toBe('traditional');
    expect(result.businessPriority).toBe('preparing_ai');
  });

  it('reaches modernizing + reducing_cost', () => {
    // Q1: hybrid, Q2: experimenting, Q3: cost-focused, Q4: mixed
    const result = deduceFromSignals(buildAnswers([1, 1, 0, 1]));
    expect(result.itEnvironment).toBe('modernizing');
    expect(result.businessPriority).toBe('reducing_cost');
  });

  it('reaches modernizing + improving_performance', () => {
    // Q1: hybrid, Q2: experimenting, Q3: performance-focused, Q4: mixed
    const result = deduceFromSignals(buildAnswers([1, 1, 1, 1]));
    expect(result.itEnvironment).toBe('modernizing');
    expect(result.businessPriority).toBe('improving_performance');
  });

  it('reaches modernizing + preparing_ai', () => {
    // Q1: hybrid, Q2: experimenting, Q3: AI-focused, Q4: mixed
    const result = deduceFromSignals(buildAnswers([1, 1, 2, 1]));
    expect(result.itEnvironment).toBe('modernizing');
    expect(result.businessPriority).toBe('preparing_ai');
  });

  it('reaches modern + reducing_cost', () => {
    // Q1: modern (strong modern), Q2: experimenting (mild), Q3: cost-focused (strong cost), Q4: mixed (mild)
    const result = deduceFromSignals(buildAnswers([2, 1, 0, 1]));
    expect(result.itEnvironment).toBe('modern');
    expect(result.businessPriority).toBe('reducing_cost');
  });

  it('reaches modern + improving_performance', () => {
    // Q1: modern, Q2: experimenting, Q3: performance-focused, Q4: AI-heavy
    const result = deduceFromSignals(buildAnswers([2, 1, 1, 2]));
    expect(result.itEnvironment).toBe('modern');
    expect(result.businessPriority).toBe('improving_performance');
  });

  it('reaches modern + preparing_ai', () => {
    // Q1: modern, Q2: production AI, Q3: AI-focused, Q4: AI-heavy
    const result = deduceFromSignals(buildAnswers([2, 2, 2, 2]));
    expect(result.itEnvironment).toBe('modern');
    expect(result.businessPriority).toBe('preparing_ai');
  });

  // ===== Mixed signal scenarios =====

  it('produces mixed result: legacy infra but AI-focused spend', () => {
    // Q1: legacy (traditional 1.5x), Q2: experimenting (mixed), Q3: AI spend (preparing_ai 1.5x), Q4: doesn't matter much
    const result = deduceFromSignals(buildAnswers([0, 1, 2, 0]));
    expect(result.itEnvironment).toBe('traditional');
    expect(result.businessPriority).toBe('preparing_ai');
  });

  it('produces mixed result: modern infra but cost-focused', () => {
    // Q1: modern (strong modern), Q2: experimenting (mild), Q3: cost (strong cost), Q4: mixed (mild)
    const result = deduceFromSignals(buildAnswers([2, 1, 0, 1]));
    expect(result.itEnvironment).toBe('modern');
    expect(result.businessPriority).toBe('reducing_cost');
  });

  // ===== No single question dominates =====

  it('no single question alone determines the outcome when others disagree', () => {
    // If Q1 says traditional but Q2/Q4 say modern, the result should not be traditional
    const result = deduceFromSignals(buildAnswers([0, 2, 2, 2]));
    // With 3 questions pointing modern vs 1 pointing traditional,
    // the outcome should NOT be traditional
    expect(result.itEnvironment).not.toBe('traditional');
  });

  // ===== Tie-breaking =====

  it('Q1 breaks itEnvironment ties', () => {
    // Create a scenario where Q1 favors traditional, and Q2/Q4 split evenly
    // Q1 weight is 1.5x for itEnvironment, so it should win ties
    const answers: Record<string, string> = {};
    SIGNAL_QUESTIONS.forEach((q) => {
      answers[q.id] = q.options.technical[0].value; // all first option
    });
    // Override to create mixed signals
    answers[SIGNAL_QUESTIONS[0].id] = SIGNAL_QUESTIONS[0].options.technical[0].value; // Q1: legacy
    answers[SIGNAL_QUESTIONS[3].id] = SIGNAL_QUESTIONS[3].options.technical[1].value; // Q4: mixed
    const result = deduceFromSignals(answers);
    // Q1's 1.5x weight for itEnvironment should make traditional win
    expect(result.itEnvironment).toBe('traditional');
  });

  it('Q3 breaks businessPriority ties', () => {
    // Q3 weight is 1.5x for businessPriority, so it should win ties
    const answers: Record<string, string> = {};
    SIGNAL_QUESTIONS.forEach((q) => {
      answers[q.id] = q.options.technical[1].value; // all middle option
    });
    // Override Q3 to cost-focused
    answers[SIGNAL_QUESTIONS[2].id] = SIGNAL_QUESTIONS[2].options.technical[0].value;
    const result = deduceFromSignals(answers);
    expect(result.businessPriority).toBe('reducing_cost');
  });

  // ===== SIGNAL_QUESTIONS structure =====

  it('has exactly 4 signal questions', () => {
    expect(SIGNAL_QUESTIONS).toHaveLength(4);
  });

  it('each question has 3 options for both persona types', () => {
    SIGNAL_QUESTIONS.forEach((q) => {
      expect(q.options.technical).toHaveLength(3);
      expect(q.options.business).toHaveLength(3);
    });
  });

  it('each question has a unique id', () => {
    const ids = SIGNAL_QUESTIONS.map((q) => q.id);
    expect(new Set(ids).size).toBe(4);
  });

  it('each option has scores for all 6 axes', () => {
    const axes = ['traditional', 'modernizing', 'modern', 'reducing_cost', 'improving_performance', 'preparing_ai'];
    SIGNAL_QUESTIONS.forEach((q) => {
      [...q.options.technical, ...q.options.business].forEach((opt) => {
        axes.forEach((axis) => {
          expect(opt.scores).toHaveProperty(axis);
          expect(typeof opt.scores[axis]).toBe('number');
        });
      });
    });
  });

  // ===== Confidence levels =====

  it('has high confidence when all signals agree', () => {
    const result = deduceFromSignals(buildAnswers([0, 0, 0, 0]));
    expect(result.confidence).toBeGreaterThan(0.6);
  });

  it('has lower confidence when signals are mixed', () => {
    // Q1: legacy, Q2: production AI, Q3: cost, Q4: AI-heavy — contradictory
    const result = deduceFromSignals(buildAnswers([0, 2, 0, 2]));
    expect(result.confidence).toBeLessThan(0.9);
  });

  // ===== Handles missing answers gracefully =====

  it('works with partial answers (only Q1)', () => {
    const answers: Record<string, string> = {
      [SIGNAL_QUESTIONS[0].id]: SIGNAL_QUESTIONS[0].options.technical[0].value,
    };
    const result = deduceFromSignals(answers);
    expect(result.itEnvironment).toBeDefined();
    expect(result.businessPriority).toBeDefined();
  });

  it('returns defaults for empty answers', () => {
    const result = deduceFromSignals({});
    expect(result.itEnvironment).toBeDefined();
    expect(result.businessPriority).toBeDefined();
  });
});
