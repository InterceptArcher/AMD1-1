/**
 * RAD Enrichment Client
 *
 * Integrates with RADTest enrichment framework to fetch company intelligence
 * from Apollo.io and PeopleDataLabs, with LLM-based conflict resolution.
 */

import { getEnrichmentFromCache, cacheEnrichment } from '../supabase/queries';

export type CompanySize = 'startup' | 'SMB' | 'mid-market' | 'enterprise';
export type IntentSignal = 'early' | 'mid' | 'late';

export interface RADEnrichmentRequest {
  domain: string;
  email?: string;
}

export interface RADEnrichmentResponse {
  company_name: string;
  domain: string;
  industry: string;
  employee_count: number | string;
  company_size: CompanySize;
  headquarters: string;
  founded_year: number | null;
  technology: string[];
  news_summary: string | null;
  intent_signal: IntentSignal | null;
  confidence_score: number;
  sources_used: string[];
  enrichment_timestamp: string;
  enrichment_duration_ms: number;
}

export interface RADApiResponse {
  status: string;
  job_id?: string;
  data?: any;
  message?: string;
}

const RAD_API_URL = process.env.RAD_API_URL || process.env.NEXT_PUBLIC_RAD_API_URL;
const RAD_API_KEY = process.env.RAD_API_KEY;
const USE_MOCK_ENRICHMENT = process.env.USE_MOCK_ENRICHMENT === 'true';
const ENRICHMENT_TIMEOUT_MS = 30000; // 30 seconds

/**
 * Main enrichment function
 * Fetches company data from RAD enrichment service
 */
export async function enrichCompanyData(
  request: RADEnrichmentRequest
): Promise<RADEnrichmentResponse> {
  const startTime = Date.now();

  try {
    // Check if using mock enrichment
    if (USE_MOCK_ENRICHMENT || !RAD_API_URL) {
      console.log('[RAD] Using mock enrichment (USE_MOCK_ENRICHMENT=true or no RAD_API_URL)');
      return getMockEnrichment(request.domain, startTime);
    }

    // Check cache first
    const cached = await getEnrichmentFromCache(request.domain);
    if (cached) {
      console.log(`[RAD] Cache hit for domain: ${request.domain}`);
      return {
        ...cached,
        enrichment_duration_ms: Date.now() - startTime
      };
    }

    // Call RAD enrichment API
    console.log(`[RAD] Fetching enrichment for domain: ${request.domain}`);
    const enriched = await callRADApi(request);

    // Cache the result
    await cacheEnrichment(request.domain, enriched);

    const duration = Date.now() - startTime;
    console.log(`[RAD] Enrichment completed in ${duration}ms`);

    return {
      ...enriched,
      enrichment_duration_ms: duration
    };
  } catch (error) {
    console.error('[RAD] Enrichment error:', error);

    // Fall back to mock enrichment on error
    console.log('[RAD] Falling back to mock enrichment');
    return getMockEnrichment(request.domain, startTime);
  }
}

/**
 * Call RAD API for enrichment
 */
async function callRADApi(
  request: RADEnrichmentRequest
): Promise<RADEnrichmentResponse> {
  // Submit enrichment request
  const response = await fetchWithTimeout(`${RAD_API_URL}/profile-request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': RAD_API_KEY ? `Bearer ${RAD_API_KEY}` : ''
    },
    body: JSON.stringify({
      domain: request.domain,
      requested_by: request.email || 'system'
    })
  }, ENRICHMENT_TIMEOUT_MS);

  if (!response.ok) {
    throw new Error(`RAD API error: ${response.status} ${response.statusText}`);
  }

  const data: RADApiResponse = await response.json();

  if (!data.job_id) {
    throw new Error('RAD API did not return job_id');
  }

  // Poll for results
  const result = await pollForJobCompletion(data.job_id);

  // Normalize RAD response to our format
  return normalizeRADResponse(result);
}

/**
 * Poll for RAD job completion
 */
async function pollForJobCompletion(jobId: string, maxAttempts: number = 20): Promise<any> {
  const pollInterval = 2000; // 2 seconds

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await sleep(pollInterval);

    const response = await fetch(`${RAD_API_URL}/job-status/${jobId}`, {
      headers: {
        'Authorization': RAD_API_KEY ? `Bearer ${RAD_API_KEY}` : ''
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to poll job status: ${response.status}`);
    }

    const data: RADApiResponse = await response.json();

    if (data.status === 'completed' || data.status === 'success') {
      return data.data;
    }

    if (data.status === 'failed' || data.status === 'error') {
      throw new Error(`RAD job failed: ${data.message || 'Unknown error'}`);
    }

    // Continue polling if status is 'pending' or 'processing'
  }

  throw new Error('RAD job timeout: max polling attempts reached');
}

/**
 * Normalize RAD API response to our schema
 */
function normalizeRADResponse(radData: any): RADEnrichmentResponse {
  const employeeCount = radData.employee_count || radData.estimated_num_employees || 'Unknown';
  const companySize = inferCompanySize(employeeCount);

  return {
    company_name: radData.company_name || radData.display_name || radData.name || 'Unknown Company',
    domain: radData.domain || radData.website || '',
    industry: radData.industry || 'Technology',
    employee_count: employeeCount,
    company_size: companySize,
    headquarters: radData.headquarters || radData.location?.locality || radData.city || 'Unknown',
    founded_year: radData.founded_year || radData.founded || null,
    technology: Array.isArray(radData.technology) ? radData.technology : (radData.tags || []),
    news_summary: radData.news_summary || null,
    intent_signal: radData.intent_signal || null,
    confidence_score: radData.confidence_score || 0.75,
    sources_used: radData.sources_used || ['apollo', 'peopledatalabs'],
    enrichment_timestamp: new Date().toISOString(),
    enrichment_duration_ms: 0 // Will be set by caller
  };
}

/**
 * Infer company size from employee count
 */
function inferCompanySize(employeeCount: number | string): CompanySize {
  const count = typeof employeeCount === 'string'
    ? parseInt(employeeCount.replace(/,/g, ''))
    : employeeCount;

  if (isNaN(count)) return 'SMB';

  if (count >= 10000) return 'enterprise';
  if (count >= 1000) return 'mid-market';
  if (count >= 50) return 'SMB';
  return 'startup';
}

/**
 * Mock enrichment for testing and fallback
 */
function getMockEnrichment(domain: string, startTime: number): RADEnrichmentResponse {
  // Use existing mock data from enrichment.ts
  const mockData = getMockDataForDomain(domain);

  return {
    company_name: mockData.company_name,
    domain: domain,
    industry: mockData.industry,
    employee_count: mockData.employee_count,
    company_size: mockData.company_size,
    headquarters: mockData.headquarters || 'San Francisco, CA',
    founded_year: mockData.founded_year || null,
    technology: mockData.technology || [],
    news_summary: mockData.news_summary || null,
    intent_signal: null,
    confidence_score: 0.5, // Lower confidence for mock data
    sources_used: ['mock'],
    enrichment_timestamp: new Date().toISOString(),
    enrichment_duration_ms: Date.now() - startTime
  };
}

/**
 * Get mock data for known domains
 */
function getMockDataForDomain(domain: string): any {
  const mockDatabase: Record<string, any> = {
    'google.com': {
      company_name: 'Google LLC',
      industry: 'Technology',
      employee_count: '156,500',
      company_size: 'enterprise' as CompanySize,
      headquarters: 'Mountain View, CA',
      founded_year: 1998,
      technology: ['Cloud', 'AI', 'Search'],
      news_summary: 'Google continues to expand its AI capabilities with new product launches.'
    },
    'microsoft.com': {
      company_name: 'Microsoft Corporation',
      industry: 'Technology',
      employee_count: '221,000',
      company_size: 'enterprise' as CompanySize,
      headquarters: 'Redmond, WA',
      founded_year: 1975,
      technology: ['Azure', 'Windows', 'Office 365'],
      news_summary: 'Microsoft reports strong cloud revenue growth in latest quarterly earnings.'
    },
    'amazon.com': {
      company_name: 'Amazon.com, Inc.',
      industry: 'E-commerce',
      employee_count: '1,541,000',
      company_size: 'enterprise' as CompanySize,
      headquarters: 'Seattle, WA',
      founded_year: 1994,
      technology: ['AWS', 'E-commerce', 'Logistics'],
      news_summary: 'Amazon announces new sustainability initiatives for its delivery network.'
    },
    'apple.com': {
      company_name: 'Apple Inc.',
      industry: 'Technology',
      employee_count: '164,000',
      company_size: 'enterprise' as CompanySize,
      headquarters: 'Cupertino, CA',
      founded_year: 1976,
      technology: ['iOS', 'macOS', 'Hardware'],
      news_summary: 'Apple unveils new product lineup with focus on AI integration.'
    },
    'salesforce.com': {
      company_name: 'Salesforce, Inc.',
      industry: 'Software',
      employee_count: '73,541',
      company_size: 'enterprise' as CompanySize,
      headquarters: 'San Francisco, CA',
      founded_year: 1999,
      technology: ['CRM', 'Cloud', 'Sales'],
      news_summary: 'Salesforce expands its AI platform with new Einstein features.'
    }
  };

  return mockDatabase[domain] || {
    company_name: `Company (${domain})`,
    industry: 'Technology',
    employee_count: '500',
    company_size: 'SMB' as CompanySize,
    headquarters: 'Unknown',
    founded_year: null,
    technology: [],
    news_summary: null
  };
}

/**
 * Utility: Fetch with timeout
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeout);
    return response;
  } catch (error: any) {
    clearTimeout(timeout);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}

/**
 * Utility: Sleep
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
