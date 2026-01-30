/**
 * Validation handler for personalization API requests
 * Validates input using Zod schemas and extracts domain from email
 */

import 'server-only';
import { PersonalizeRequestSchema } from '@/shared/schemas';
import type { PersonalizeRequest } from '@/shared/schemas';

export interface ValidationResult {
  success: boolean;
  data?: PersonalizeRequest & { domain: string };
  error?: {
    message: string;
    details?: any;
  };
}

/**
 * Validates a personalization request against the schema
 * Returns validated data with extracted domain or error details
 */
export async function validatePersonalizeRequest(
  body: unknown
): Promise<ValidationResult> {
  try {
    // Validate against schema
    const validatedData = PersonalizeRequestSchema.parse(body);

    // Extract domain from email
    const domain = extractDomainFromEmail(validatedData.email);

    return {
      success: true,
      data: {
        ...validatedData,
        domain,
      },
    };
  } catch (error: any) {
    // Handle Zod validation errors
    if (error.errors && Array.isArray(error.errors)) {
      const firstError = error.errors[0];
      const fieldName = firstError.path.join('.');
      const message = `${fieldName}: ${firstError.message}`;

      return {
        success: false,
        error: {
          message,
          details: error.errors,
        },
      };
    }

    // Handle other errors
    return {
      success: false,
      error: {
        message: error.message || 'Validation failed',
        details: error,
      },
    };
  }
}

/**
 * Extracts domain from email address
 * Returns empty string if email is malformed
 */
export function extractDomainFromEmail(email: string): string {
  if (!email || typeof email !== 'string') {
    return '';
  }

  const parts = email.split('@');
  if (parts.length !== 2) {
    return '';
  }

  const domain = parts[1].trim();
  return domain || '';
}

/**
 * Validates request and throws error if invalid
 * Use for API routes where you want to throw errors
 */
export async function validateOrThrow(body: unknown): Promise<PersonalizeRequest & { domain: string }> {
  const result = await validatePersonalizeRequest(body);

  if (!result.success) {
    throw new Error(result.error?.message || 'Validation failed');
  }

  return result.data!;
}
