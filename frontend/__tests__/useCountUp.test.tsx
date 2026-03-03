import { renderHook, act } from '@testing-library/react';
import { useCountUp } from '../src/hooks/useCountUp';

// Mock requestAnimationFrame for deterministic tests
beforeEach(() => {
  jest.useFakeTimers();
  let rafId = 0;
  jest.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
    rafId++;
    setTimeout(() => cb(performance.now()), 16);
    return rafId;
  });
  jest.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => {
    clearTimeout(id);
  });
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('useCountUp', () => {
  it('starts at 0', () => {
    const { result } = renderHook(() => useCountUp(33, 1500, 0));
    expect(result.current).toBe(0);
  });

  it('reaches target value after duration', () => {
    const { result } = renderHook(() => useCountUp(33, 1500, 0));
    act(() => {
      jest.advanceTimersByTime(2000);
    });
    expect(result.current).toBe(33);
  });

  it('respects delay before starting', () => {
    const { result } = renderHook(() => useCountUp(58, 1500, 500));
    act(() => {
      jest.advanceTimersByTime(400);
    });
    expect(result.current).toBe(0);
  });
});
