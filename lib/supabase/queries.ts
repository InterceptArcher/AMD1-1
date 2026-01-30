import { getSupabaseServerClient } from './client';
import type { PersonalizationJob, ClaudeOutput } from '../schemas';
import type { RADEnrichmentResponse } from '../enrichment/rad-client';

/**
 * Insert a new personalization job into the database
 */
export async function createPersonalizationJob(
  jobData: Omit<PersonalizationJob, 'status'>
): Promise<number> {
  const supabase = getSupabaseServerClient();

  const { data, error } = await supabase
    .from('personalization_jobs')
    .insert({
      ...jobData,
      status: 'pending',
    })
    .select('id')
    .single();

  if (error) {
    console.error('Supabase insert error:', error);
    throw new Error(`Failed to create personalization job: ${error.message}`);
  }

  return data.id;
}

/**
 * Store the Claude API output for a job
 */
export async function storePersonalizationOutput(
  jobId: number,
  output: ClaudeOutput
): Promise<void> {
  const supabase = getSupabaseServerClient();

  const { error } = await supabase
    .from('personalization_outputs')
    .insert({
      job_id: jobId,
      output_json: output,
    });

  if (error) {
    console.error('Supabase insert error:', error);
    throw new Error(`Failed to store personalization output: ${error.message}`);
  }
}

/**
 * Update job status
 */
export async function updateJobStatus(
  jobId: number,
  status: 'completed' | 'failed'
): Promise<void> {
  const supabase = getSupabaseServerClient();

  const { error } = await supabase
    .from('personalization_jobs')
    .update({ status })
    .eq('id', jobId);

  if (error) {
    console.error('Supabase update error:', error);
    throw new Error(`Failed to update job status: ${error.message}`);
  }
}

/**
 * Update enrichment data for a job
 */
export async function updateJobEnrichment(
  jobId: number,
  enrichment: RADEnrichmentResponse
): Promise<void> {
  const supabase = getSupabaseServerClient();

  const { error } = await supabase
    .from('personalization_jobs')
    .update({
      company_name: enrichment.company_name,
      industry: enrichment.industry,
      company_size: enrichment.company_size,
      employee_count: String(enrichment.employee_count),
      headquarters: enrichment.headquarters,
      founded_year: enrichment.founded_year,
      technology: enrichment.technology,
      news_summary: enrichment.news_summary,
      intent_signal: enrichment.intent_signal,
      confidence_score: enrichment.confidence_score,
      enrichment_sources: enrichment.sources_used,
      enrichment_timestamp: enrichment.enrichment_timestamp,
      enrichment_duration_ms: enrichment.enrichment_duration_ms
    })
    .eq('id', jobId);

  if (error) {
    console.error('Supabase update error:', error);
    throw new Error(`Failed to update job enrichment: ${error.message}`);
  }
}

/**
 * Update personalization output with template and performance metadata
 */
export async function updateOutputMetadata(
  jobId: number,
  metadata: {
    template_id?: string;
    template_name?: string;
    llm_model?: string;
    llm_tokens_used?: number;
    llm_latency_ms?: number;
    total_latency_ms?: number;
  }
): Promise<void> {
  const supabase = getSupabaseServerClient();

  const { error } = await supabase
    .from('personalization_outputs')
    .update(metadata)
    .eq('job_id', jobId);

  if (error) {
    console.error('Supabase update error:', error);
    throw new Error(`Failed to update output metadata: ${error.message}`);
  }
}

/**
 * Get enrichment data from cache
 */
export async function getEnrichmentFromCache(
  domain: string
): Promise<RADEnrichmentResponse | null> {
  const supabase = getSupabaseServerClient();

  const { data, error } = await supabase
    .from('enrichment_cache')
    .select('enriched_data, confidence_score, cached_at')
    .eq('domain', domain)
    .gt('expires_at', new Date().toISOString())
    .single();

  if (error || !data) {
    return null;
  }

  // Update last accessed time (cache_hits would require RPC call to increment)
  await supabase
    .from('enrichment_cache')
    .update({
      last_accessed_at: new Date().toISOString()
    })
    .eq('domain', domain);

  return data.enriched_data as RADEnrichmentResponse;
}

/**
 * Cache enrichment data
 */
export async function cacheEnrichment(
  domain: string,
  enrichment: RADEnrichmentResponse,
  ttlHours: number = 24
): Promise<void> {
  const supabase = getSupabaseServerClient();

  const expiresAt = new Date();
  expiresAt.setHours(expiresAt.getHours() + ttlHours);

  const { error } = await supabase
    .from('enrichment_cache')
    .upsert({
      domain,
      enriched_data: enrichment,
      confidence_score: enrichment.confidence_score,
      expires_at: expiresAt.toISOString(),
      cached_at: new Date().toISOString(),
      cache_hits: 0
    }, {
      onConflict: 'domain'
    });

  if (error) {
    console.error('Supabase upsert error:', error);
    // Don't throw - caching failures shouldn't break the flow
  }
}
