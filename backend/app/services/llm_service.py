"""
LLM Service: Generates personalization content (intro hook + CTA).
Uses Claude Haiku for fast inference (target <30s latency).
Implements structured output, validation, and retry logic.
"""

import logging
import json
import time
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import anthropic
from anthropic import APIError, APITimeoutError, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0
DEFAULT_MODEL = "claude-3-5-haiku-20241022"
OPUS_MODEL = "claude-opus-4-5-20251101"

# Output constraints
MAX_INTRO_LENGTH = 200  # characters
MAX_CTA_LENGTH = 150  # characters


@dataclass
class PersonalizationResult:
    """Result from personalization generation."""
    intro_hook: str
    cta: str
    model_used: str
    tokens_used: int
    latency_ms: int
    raw_response: Dict[str, Any]


class LLMService:
    """
    Generates personalized intro hook and CTA using Claude.
    - Uses Haiku for speed (default)
    - Falls back to Opus for complex cases
    - Implements structured output with JSON validation
    - Retry logic for transient failures
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM service.

        Args:
            api_key: Anthropic API key. If None, use environment variable.
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.client = None

        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("LLM service initialized with Anthropic client")
        else:
            logger.warning("LLM service initialized without API key (mock mode)")

    async def generate_personalization(
        self,
        normalized_profile: Dict[str, Any],
        use_opus: bool = False,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate intro hook and CTA from normalized profile.

        Args:
            normalized_profile: Normalized enrichment data
            use_opus: Whether to use Opus model for richer output
            user_context: User-provided context (goal, persona, industry)

        Returns:
            Dict with 'intro_hook', 'cta', and metadata
        """
        if not self.client:
            return self._mock_response(normalized_profile, user_context)

        start_time = time.time()
        model = OPUS_MODEL if use_opus else DEFAULT_MODEL

        # Build the prompt with user context
        prompt = self._build_prompt(normalized_profile, user_context)

        # Try with retries
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                    system=self._get_system_prompt()
                )

                # Parse response
                content = response.content[0].text
                parsed = self._parse_response(content)

                if parsed:
                    latency_ms = int((time.time() - start_time) * 1000)

                    result = {
                        "intro_hook": parsed["intro_hook"],
                        "cta": parsed["cta"],
                        "model_used": model,
                        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                        "latency_ms": latency_ms,
                        "raw_response": {"content": content}
                    }

                    logger.info(
                        f"Generated personalization: model={model}, "
                        f"tokens={result['tokens_used']}, latency={latency_ms}ms"
                    )
                    return result

                # Parse failed, retry with fix prompt
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Parse failed, retrying with fix prompt (attempt {attempt + 1})")
                    prompt = self._build_fix_prompt(content)
                    continue

            except RateLimitError as e:
                logger.warning(f"Rate limited, retrying in {RETRY_DELAY_SECONDS}s: {e}")
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                continue

            except APITimeoutError as e:
                logger.warning(f"API timeout, retrying: {e}")
                continue

            except APIError as e:
                logger.error(f"API error: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise

        # All retries failed, return fallback
        logger.error("All retries failed, returning fallback response")
        return self._fallback_response(normalized_profile)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for personalization."""
        return """You are a B2B marketing copywriter creating personalized content for ebook landing pages.

Your task: Generate a personalized intro hook (1-2 sentences) and call-to-action (CTA) based on the prospect's profile.

Rules:
1. Be conversational and specific to their role/company
2. Reference their industry or company context when available
3. Keep intro under 200 characters
4. Keep CTA under 150 characters
5. Do NOT make unsubstantiated claims (no "guaranteed", "proven", "#1", etc.)
6. Do NOT use superlatives without evidence
7. Sound helpful, not salesy

Output ONLY valid JSON in this exact format:
{
  "intro_hook": "Your personalized intro here",
  "cta": "Your call to action here"
}

No other text before or after the JSON."""

    def _build_prompt(self, profile: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> str:
        """Build the user prompt from profile data and user-provided context."""
        parts = []
        user_context = user_context or {}

        # Extract key fields from enrichment
        first_name = profile.get("first_name", "there")
        company = profile.get("company_name", "your company")
        title = profile.get("title", "professional")
        industry = profile.get("industry", "your industry")
        company_size = profile.get("company_size", "")
        company_context = profile.get("company_context", "")
        seniority = profile.get("seniority", "")

        # Extract user-provided context (more reliable than API data)
        user_goal = user_context.get("goal", "")
        user_persona = user_context.get("persona", "")
        user_industry = user_context.get("industry_input", "")

        # Goal mapping for more natural language
        goal_descriptions = {
            "exploring": "exploring modernization options and doing early research",
            "evaluating": "comparing different approaches for their organization",
            "learning": "learning about best practices and industry trends",
            "building_case": "building a business case to present internally"
        }

        # Persona mapping for richer context
        persona_descriptions = {
            "executive": "an executive leader (C-suite or VP level) focused on strategic decisions",
            "it_infrastructure": "an IT/Infrastructure professional managing technical operations",
            "security": "a security professional focused on protecting systems and data",
            "data_ai": "a data/AI engineer working on analytics and machine learning",
            "sales_gtm": "a sales or GTM leader driving revenue growth",
            "hr_people": "an HR/People Ops professional managing talent and culture",
            "other": "a professional seeking industry insights"
        }

        # Industry-specific angles
        industry_angles = {
            "healthcare": "compliance, patient outcomes, and operational efficiency",
            "financial_services": "risk management, regulatory compliance, and digital transformation",
            "technology": "innovation velocity, scalability, and technical excellence",
            "gaming_media": "user engagement, content delivery, and real-time performance",
            "manufacturing": "operational efficiency, supply chain optimization, and IoT",
            "retail": "customer experience, omnichannel strategy, and inventory management",
            "government": "security, compliance, and citizen services modernization",
            "energy": "grid modernization, sustainability, and operational resilience",
            "telecommunications": "network performance, 5G adoption, and customer experience"
        }

        parts.append(f"Create personalized content for this prospect:\n")
        parts.append(f"- First Name: {first_name}")
        parts.append(f"- Company: {company}")
        parts.append(f"- Title: {title}")

        # Prefer user-provided industry if available
        effective_industry = user_industry or industry
        parts.append(f"- Industry: {effective_industry}")

        if company_size:
            parts.append(f"- Company Size: {company_size}")

        if seniority:
            parts.append(f"- Seniority: {seniority}")

        # Add user-provided context for better personalization
        if user_goal:
            goal_desc = goal_descriptions.get(user_goal, user_goal)
            parts.append(f"\nThis person is currently {goal_desc}.")

        if user_persona:
            persona_desc = persona_descriptions.get(user_persona, user_persona)
            parts.append(f"They are {persona_desc}.")

        if effective_industry in industry_angles:
            parts.append(f"In their industry, key concerns include {industry_angles[effective_industry]}.")

        if company_context:
            parts.append(f"\nRecent company context: {company_context[:500]}")

        parts.append("\nGenerate content that speaks directly to their role, goals, and industry context.")
        parts.append("Make it specific and actionable, not generic.")
        parts.append("\nGenerate the JSON response now.")

        return "\n".join(parts)

    def _build_fix_prompt(self, failed_response: str) -> str:
        """Build a prompt to fix malformed JSON."""
        return f"""The previous response was not valid JSON. Here's what was returned:

{failed_response}

Please fix this and return ONLY valid JSON in this exact format:
{{
  "intro_hook": "Your personalized intro here",
  "cta": "Your call to action here"
}}

No other text."""

    def _parse_response(self, content: str) -> Optional[Dict[str, str]]:
        """
        Parse LLM response to extract intro_hook and cta.

        Args:
            content: Raw LLM response text

        Returns:
            Dict with intro_hook and cta, or None if parse failed
        """
        # Try direct JSON parse
        try:
            # Find JSON in response (handle markdown code blocks)
            json_match = re.search(r'\{[^{}]*"intro_hook"[^{}]*"cta"[^{}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                intro = data.get("intro_hook", "").strip()
                cta = data.get("cta", "").strip()

                if intro and cta:
                    # Validate lengths
                    if len(intro) > MAX_INTRO_LENGTH:
                        intro = intro[:MAX_INTRO_LENGTH - 3] + "..."
                    if len(cta) > MAX_CTA_LENGTH:
                        cta = cta[:MAX_CTA_LENGTH - 3] + "..."

                    return {"intro_hook": intro, "cta": cta}

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")

        return None

    def _mock_response(self, profile: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Generate mock response when API key not configured."""
        logger.info("LLM: Using mock response (no API key)")
        user_context = user_context or {}

        first_name = profile.get("first_name", "")
        company = profile.get("company", profile.get("company_name", ""))
        title = profile.get("title", "")
        industry = profile.get("industry", "Technology")
        company_size = profile.get("company_size", "")

        # Use user-provided context if available
        user_goal = user_context.get("goal", "")
        user_persona = user_context.get("persona", "")
        user_industry = user_context.get("industry_input", "")

        # Prefer user-provided industry
        effective_industry = user_industry or industry

        # Industry-specific hooks (tailored for AMD use case)
        industry_hooks = {
            "healthcare": "Healthcare organizations are modernizing their infrastructure to improve patient outcomes while maintaining strict compliance.",
            "financial_services": "Financial services leaders are balancing regulatory requirements with the need for digital transformation and innovation.",
            "technology": "Tech companies like yours are pushing the boundaries of what's possible with modern infrastructure and AI workloads.",
            "gaming_media": "Gaming and media companies need infrastructure that delivers real-time performance at massive scale.",
            "manufacturing": "Manufacturing leaders are leveraging smart infrastructure to optimize operations and drive efficiency.",
            "retail": "Retail organizations are transforming customer experiences through modern, scalable technology.",
            "government": "Government agencies are modernizing citizen services while maintaining the highest security standards.",
            "energy": "Energy companies are building resilient, sustainable infrastructure for the future.",
            "telecommunications": "Telecom providers are building next-generation networks to meet growing connectivity demands.",
        }

        # Goal-specific intros
        goal_intros = {
            "exploring": "You're taking the right first step by exploring your options.",
            "evaluating": "Making the right infrastructure decision requires careful evaluation.",
            "learning": "Staying informed on best practices gives you a strategic advantage.",
            "building_case": "Building a compelling business case starts with the right insights.",
        }

        # Persona-specific CTAs
        persona_ctas = {
            "executive": "Get the executive summary with ROI insights for your board",
            "it_infrastructure": "Download the technical deep-dive with architecture patterns",
            "security": "Access the security-focused guide with compliance frameworks",
            "data_ai": "Get the data infrastructure guide optimized for AI workloads",
            "sales_gtm": "Download strategies to accelerate your digital sales motion",
            "hr_people": "Learn how tech modernization impacts talent and culture",
        }

        # Build personalized intro
        base_hook = industry_hooks.get(effective_industry, "Organizations like yours are discovering new ways to modernize and scale.")
        goal_hook = goal_intros.get(user_goal, "")

        if first_name and company:
            intro = f"{goal_hook} {base_hook}".strip()
            if len(intro) < 50:
                intro = f"{intro} At {company}, these insights can drive real impact."
        elif first_name:
            intro = f"{goal_hook} {base_hook}".strip()
        else:
            intro = base_hook

        # Build personalized CTA based on persona
        if user_persona and user_persona in persona_ctas:
            cta = persona_ctas[user_persona]
        elif title:
            cta = f"Get your free ebook with actionable insights for {title}s like you"
        else:
            cta = "Download your personalized guide and unlock strategies for your team"

        return {
            "intro_hook": intro[:MAX_INTRO_LENGTH],
            "cta": cta[:MAX_CTA_LENGTH],
            "model_used": "mock",
            "tokens_used": 0,
            "latency_ms": 0,
            "raw_response": {"_mock": True, "user_context": user_context}
        }

    def _fallback_response(self, profile: Dict[str, Any]) -> Dict[str, str]:
        """Generate safe fallback response on all failures."""
        logger.warning("Using fallback response due to LLM failures")

        first_name = profile.get("first_name", "")
        greeting = f"Hi {first_name}, " if first_name else ""

        return {
            "intro_hook": f"{greeting}This guide was created to help professionals like you navigate common challenges in your field.",
            "cta": "Download the guide and discover actionable insights for your team.",
            "model_used": "fallback",
            "tokens_used": 0,
            "latency_ms": 0,
            "raw_response": {"_fallback": True}
        }

    async def generate_intro_hook(
        self,
        normalized_profile: Dict[str, Any]
    ) -> str:
        """Generate just the intro hook."""
        result = await self.generate_personalization(normalized_profile)
        return result.get("intro_hook", "")

    async def generate_cta(
        self,
        normalized_profile: Dict[str, Any]
    ) -> str:
        """Generate just the CTA."""
        result = await self.generate_personalization(normalized_profile)
        return result.get("cta", "")

    def should_use_opus(self, profile: Dict[str, Any]) -> bool:
        """
        Determine if Opus should be used based on profile quality.

        Uses Opus for:
        - High data quality scores
        - VIP domains (can be configured)
        - Complex industry contexts

        Args:
            profile: Normalized profile data

        Returns:
            True if Opus should be used
        """
        quality_score = profile.get("data_quality_score", 0)

        # Use Opus for high-quality profiles
        if quality_score >= 0.8:
            return True

        # Check for VIP domains (example)
        vip_domains = ["google.com", "microsoft.com", "apple.com", "amazon.com"]
        domain = profile.get("domain", "")
        if domain in vip_domains:
            return True

        return False
