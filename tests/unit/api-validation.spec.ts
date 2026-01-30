/**
 * Unit tests for API validation handler
 * Tests MUST run and FAIL before implementation
 */

import { test, expect } from '@playwright/test';

test.describe('API Validation Handler', () => {
  test('should validate complete request with all required fields', async () => {
    // This will fail until the handler is implemented
    const { validatePersonalizeRequest } = await import('@/backend/api/personalize/handlers/validation');

    const validRequest = {
      email: 'test@example.com',
      company: 'Test Corp',
      role: 'Business Leader',
      modernization_stage: 'evaluation',
      ai_priority: 'AI/ML Development',
      cta: 'compare',
    };

    const result = await validatePersonalizeRequest(validRequest);

    expect(result.success).toBe(true);
    expect(result.data).toEqual(validRequest);
  });

  test('should reject request with invalid email', async () => {
    const { validatePersonalizeRequest } = await import('@/backend/api/personalize/handlers/validation');

    const invalidRequest = {
      email: 'not-an-email',
      company: 'Test Corp',
      role: 'Business Leader',
      modernization_stage: 'evaluation',
      ai_priority: 'AI/ML Development',
      cta: 'compare',
    };

    const result = await validatePersonalizeRequest(invalidRequest);

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
    expect(result.error?.message).toContain('email');
  });

  test('should reject request missing required company field', async () => {
    const { validatePersonalizeRequest } = await import('@/backend/api/personalize/handlers/validation');

    const invalidRequest = {
      email: 'test@example.com',
      role: 'Business Leader',
      modernization_stage: 'evaluation',
      ai_priority: 'AI/ML Development',
      cta: 'compare',
    };

    const result = await validatePersonalizeRequest(invalidRequest);

    expect(result.success).toBe(false);
    expect(result.error?.message).toContain('company');
  });

  test('should reject request missing required role field', async () => {
    const { validatePersonalizeRequest } = await import('@/backend/api/personalize/handlers/validation');

    const invalidRequest = {
      email: 'test@example.com',
      company: 'Test Corp',
      modernization_stage: 'evaluation',
      ai_priority: 'AI/ML Development',
      cta: 'compare',
    };

    const result = await validatePersonalizeRequest(invalidRequest);

    expect(result.success).toBe(false);
    expect(result.error?.message).toContain('role');
  });

  test('should reject request missing modernization_stage', async () => {
    const { validatePersonalizeRequest } = await import('@/backend/api/personalize/handlers/validation');

    const invalidRequest = {
      email: 'test@example.com',
      company: 'Test Corp',
      role: 'Business Leader',
      ai_priority: 'AI/ML Development',
      cta: 'compare',
    };

    const result = await validatePersonalizeRequest(invalidRequest);

    expect(result.success).toBe(false);
    expect(result.error?.message).toContain('modernization_stage');
  });

  test('should reject request missing ai_priority', async () => {
    const { validatePersonalizeRequest } = await import('@/backend/api/personalize/handlers/validation');

    const invalidRequest = {
      email: 'test@example.com',
      company: 'Test Corp',
      role: 'Business Leader',
      modernization_stage: 'evaluation',
      cta: 'compare',
    };

    const result = await validatePersonalizeRequest(invalidRequest);

    expect(result.success).toBe(false);
    expect(result.error?.message).toContain('ai_priority');
  });

  test('should allow optional name field', async () => {
    const { validatePersonalizeRequest } = await import('@/backend/api/personalize/handlers/validation');

    const requestWithName = {
      email: 'test@example.com',
      name: 'John Doe',
      company: 'Test Corp',
      role: 'Business Leader',
      modernization_stage: 'evaluation',
      ai_priority: 'AI/ML Development',
      cta: 'compare',
    };

    const result = await validatePersonalizeRequest(requestWithName);

    expect(result.success).toBe(true);
    expect(result.data?.name).toBe('John Doe');
  });

  test('should extract domain from email', async () => {
    const { extractDomainFromEmail } = await import('@/backend/api/personalize/handlers/validation');

    expect(extractDomainFromEmail('user@example.com')).toBe('example.com');
    expect(extractDomainFromEmail('admin@subdomain.example.co.uk')).toBe('subdomain.example.co.uk');
  });

  test('should handle malformed emails gracefully', async () => {
    const { extractDomainFromEmail } = await import('@/backend/api/personalize/handlers/validation');

    expect(extractDomainFromEmail('not-an-email')).toBe('');
    expect(extractDomainFromEmail('')).toBe('');
  });
});
