"""
LLM Service: Generates personalization content (intro hook + CTA).
Multi-provider support with fallback: Anthropic → OpenAI → Gemini → mock.
Implements structured output, validation, and retry logic.
"""

import logging
import json
import time
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import anthropic
from anthropic import APIError as AnthropicAPIError, APITimeoutError as AnthropicTimeoutError, RateLimitError as AnthropicRateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import optional providers
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.info("OpenAI not installed, skipping as fallback")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.info("Google Generative AI not installed, skipping as fallback")

# Constants
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0

# Model names per provider
ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"
ANTHROPIC_OPUS = "claude-opus-4-5-20251101"
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-1.5-flash"

# Output constraints
MAX_INTRO_LENGTH = 200  # characters
MAX_CTA_LENGTH = 150  # characters

# Role mapping: form values to human-readable titles and seniority
ROLE_MAPPING = {
    # Executive Leadership
    "ceo": {"title": "CEO", "seniority": "c_suite", "department": "executive"},
    "coo": {"title": "COO", "seniority": "c_suite", "department": "operations"},
    "c_suite_other": {"title": "Executive", "seniority": "c_suite", "department": "executive"},
    # Technology Leadership
    "cto": {"title": "CTO", "seniority": "c_suite", "department": "technology"},
    "cio": {"title": "CIO", "seniority": "c_suite", "department": "technology"},
    "vp_engineering": {"title": "VP of Engineering", "seniority": "vp", "department": "engineering"},
    # Security & Compliance
    "ciso": {"title": "CISO", "seniority": "c_suite", "department": "security"},
    "vp_security": {"title": "VP of Security", "seniority": "vp", "department": "security"},
    "security_manager": {"title": "Security Manager", "seniority": "manager", "department": "security"},
    # Data & AI
    "cdo": {"title": "Chief Data Officer", "seniority": "c_suite", "department": "data"},
    "vp_data": {"title": "VP of Data/AI", "seniority": "vp", "department": "data"},
    "data_manager": {"title": "Data Science Manager", "seniority": "manager", "department": "data"},
    # Finance
    "cfo": {"title": "CFO", "seniority": "c_suite", "department": "finance"},
    "vp_finance": {"title": "VP of Finance", "seniority": "vp", "department": "finance"},
    "finance_manager": {"title": "Finance Manager", "seniority": "manager", "department": "finance"},
    # IT & Infrastructure
    "vp_it": {"title": "VP of IT", "seniority": "vp", "department": "it"},
    "it_manager": {"title": "IT Manager", "seniority": "manager", "department": "it"},
    "sysadmin": {"title": "Systems Administrator", "seniority": "ic", "department": "it"},
    # Engineering & Development
    "vp_eng": {"title": "VP of Engineering", "seniority": "vp", "department": "engineering"},
    "eng_manager": {"title": "Engineering Manager", "seniority": "manager", "department": "engineering"},
    "senior_engineer": {"title": "Senior Engineer", "seniority": "senior_ic", "department": "engineering"},
    "engineer": {"title": "Software Engineer", "seniority": "ic", "department": "engineering"},
    # Operations & Procurement
    "vp_ops": {"title": "VP of Operations", "seniority": "vp", "department": "operations"},
    "ops_manager": {"title": "Operations Manager", "seniority": "manager", "department": "operations"},
    "procurement": {"title": "Procurement Manager", "seniority": "manager", "department": "procurement"},
    # Other
    "other": {"title": "Professional", "seniority": "unknown", "department": "unknown"},
}

# Company size mapping for personalization context
COMPANY_SIZE_MAPPING = {
    "startup": {"label": "startup", "employee_range": "1-50", "segment": "smb"},
    "small": {"label": "small business", "employee_range": "51-200", "segment": "smb"},
    "midmarket": {"label": "mid-market company", "employee_range": "201-1,000", "segment": "mid_market"},
    "enterprise": {"label": "enterprise", "employee_range": "1,001-10,000", "segment": "enterprise"},
    "large_enterprise": {"label": "large enterprise", "employee_range": "10,000+", "segment": "enterprise"},
}


def get_role_info(persona: str) -> Dict[str, str]:
    """Get role information from persona value."""
    return ROLE_MAPPING.get(persona, ROLE_MAPPING["other"])


def get_company_size_info(size: str) -> Dict[str, str]:
    """Get company size information."""
    return COMPANY_SIZE_MAPPING.get(size, {"label": "company", "employee_range": "unknown", "segment": "unknown"})


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
    Generates personalized intro hook and CTA using LLMs.
    Multi-provider support: Anthropic → OpenAI → Gemini → mock fallback.
    - Tries providers in order until one succeeds
    - Implements structured output with JSON validation
    - Retry logic for transient failures
    """

    def __init__(self):
        """
        Initialize LLM service with all available providers.
        Providers are tried in order: Anthropic → OpenAI → Gemini.
        """
        self.providers: List[Dict[str, Any]] = []

        # Initialize Anthropic
        if settings.ANTHROPIC_API_KEY:
            try:
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                self.providers.append({
                    "name": "anthropic",
                    "client": client,
                    "model": ANTHROPIC_MODEL
                })
                logger.info("Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic: {e}")

        # Initialize OpenAI
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                self.providers.append({
                    "name": "openai",
                    "client": client,
                    "model": OPENAI_MODEL
                })
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Initialize Gemini
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.providers.append({
                    "name": "gemini",
                    "client": genai,
                    "model": GEMINI_MODEL
                })
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        if not self.providers:
            logger.warning("No LLM providers available - will use mock responses")
        else:
            logger.info(f"LLM service initialized with providers: {[p['name'] for p in self.providers]}")

    def _call_provider(
        self,
        provider: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Call a specific LLM provider and return the response text.

        Args:
            provider: Provider config dict with name, client, model
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Max tokens for response

        Returns:
            Response text or None if failed
        """
        name = provider["name"]
        client = provider["client"]
        model = provider["model"]

        try:
            if name == "anthropic":
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": user_prompt}],
                    system=system_prompt
                )
                return response.content[0].text

            elif name == "openai":
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content

            elif name == "gemini":
                model_instance = client.GenerativeModel(model)
                # Gemini combines system + user in one prompt
                combined = f"{system_prompt}\n\n{user_prompt}"
                response = model_instance.generate_content(combined)
                return response.text

        except Exception as e:
            logger.warning(f"{name} provider failed: {type(e).__name__}: {e}")
            return None

        return None

    def _call_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500
    ) -> Tuple[Optional[str], str]:
        """
        Try each provider in order until one succeeds.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Max tokens

        Returns:
            Tuple of (response_text, provider_name) or (None, "none")
        """
        for provider in self.providers:
            for attempt in range(MAX_RETRIES):
                result = self._call_provider(provider, system_prompt, user_prompt, max_tokens)
                if result:
                    return result, provider["name"]
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)

        return None, "none"

    async def generate_personalization(
        self,
        normalized_profile: Dict[str, Any],
        use_opus: bool = False,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate intro hook and CTA from normalized profile.
        Uses multi-provider fallback: Anthropic → OpenAI → Gemini → mock.

        Args:
            normalized_profile: Normalized enrichment data
            use_opus: Whether to use Opus model (Anthropic only)
            user_context: User-provided context (goal, persona, industry)

        Returns:
            Dict with 'intro_hook', 'cta', and metadata
        """
        if not self.providers:
            return self._mock_response(normalized_profile, user_context)

        start_time = time.time()
        prompt = self._build_prompt(normalized_profile, user_context)
        system_prompt = self._get_system_prompt()

        # Try with fallback
        content, provider_name = self._call_with_fallback(system_prompt, prompt, max_tokens=500)

        if content:
            parsed = self._parse_response(content)

            if parsed:
                latency_ms = int((time.time() - start_time) * 1000)

                result = {
                    "intro_hook": parsed["intro_hook"],
                    "cta": parsed["cta"],
                    "model_used": provider_name,
                    "tokens_used": 0,  # Not tracking across providers
                    "latency_ms": latency_ms,
                    "raw_response": {"content": content}
                }

                logger.info(
                    f"Generated personalization: provider={provider_name}, latency={latency_ms}ms"
                )
                return result

        # All providers failed, return mock response
        logger.warning("All LLM providers failed, returning mock response")
        return self._mock_response(normalized_profile, user_context)

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

        # Goal/buying stage mapping for more natural language
        goal_descriptions = {
            "awareness": "just starting to research and explore options",
            "consideration": "actively evaluating and comparing different solutions",
            "decision": "ready to make a decision and need final validation",
            "implementation": "already implementing and looking for guidance",
            # Legacy values
            "exploring": "exploring modernization options and doing early research",
            "evaluating": "comparing different approaches for their organization",
            "learning": "learning about best practices and industry trends",
            "building_case": "building a business case to present internally"
        }

        # Persona/role mapping for richer context
        persona_descriptions = {
            "c_suite": "a C-suite executive (CEO, CTO, CIO, CFO) focused on strategic outcomes and ROI",
            "vp_director": "a VP or Director level leader balancing strategy with execution",
            "it_infrastructure": "an IT/Infrastructure manager overseeing technical operations",
            "engineering": "an engineering or DevOps professional focused on implementation",
            "data_ai": "a data science or AI/ML professional optimizing workloads",
            "security": "a security or compliance professional protecting systems and data",
            "procurement": "a procurement professional evaluating vendors and costs",
            # Legacy values
            "executive": "an executive leader (C-suite or VP level) focused on strategic decisions",
            "sales_gtm": "a sales or GTM leader driving revenue growth",
            "hr_people": "an HR/People Ops professional managing talent and culture",
            "other": "a professional seeking industry insights"
        }

        # Industry-specific angles (expanded to match frontend)
        industry_angles = {
            "technology": "innovation velocity, scalability, and technical excellence",
            "financial_services": "risk management, regulatory compliance, and digital transformation",
            "healthcare": "compliance, patient outcomes, and operational efficiency",
            "retail_ecommerce": "customer experience, omnichannel strategy, and real-time inventory",
            "manufacturing": "operational efficiency, supply chain optimization, and IoT",
            "telecommunications": "network performance, 5G adoption, and content delivery",
            "energy_utilities": "grid modernization, sustainability, and operational resilience",
            "government": "security, compliance, and citizen services modernization",
            "education": "research computing, student outcomes, and secure data management",
            "professional_services": "client delivery efficiency, knowledge management, and scale",
            # Legacy values
            "gaming_media": "user engagement, content delivery, and real-time performance",
            "retail": "customer experience, omnichannel strategy, and inventory management",
            "energy": "grid modernization, sustainability, and operational resilience"
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

    async def generate_ebook_personalization(
        self,
        profile: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        company_news: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized content for AMD ebook - 3 sections:
        1. Hook/Intro - Based on role, buying stage, company news
        2. Case Study Framing - Context for why selected case study is relevant
        3. CTA - Based on buying stage and role

        Uses multi-provider fallback: Anthropic → OpenAI → Gemini → mock.

        Args:
            profile: Normalized enrichment data
            user_context: User-provided context (goal, persona, industry)
            company_news: Recent company news from Tavily

        Returns:
            Dict with personalized_hook, case_study_framing, personalized_cta
        """
        if not self.providers:
            return self._mock_ebook_response(profile, user_context)

        user_context = user_context or {}
        start_time = time.time()

        prompt = self._build_ebook_prompt(profile, user_context, company_news)
        system_prompt = self._get_ebook_system_prompt()

        # Try with fallback
        content, provider_name = self._call_with_fallback(system_prompt, prompt, max_tokens=1000)

        if content:
            parsed = self._parse_ebook_response(content)

            if parsed:
                latency_ms = int((time.time() - start_time) * 1000)
                parsed["model_used"] = provider_name
                parsed["tokens_used"] = 0
                parsed["latency_ms"] = latency_ms
                logger.info(f"Generated ebook personalization: provider={provider_name}, latency={latency_ms}ms")
                return parsed

        # All providers failed
        logger.warning("All LLM providers failed for ebook personalization, using mock")
        return self._mock_ebook_response(profile, user_context)

    def _get_ebook_system_prompt(self) -> str:
        """System prompt for AMD ebook personalization."""
        return """You are a B2B marketing expert creating HYPER-PERSONALIZED content for AMD's enterprise AI readiness ebook.

ABSOLUTE REQUIREMENT: Every piece of content must feel like it was written SPECIFICALLY for this person. Generic content = failure.

The ebook covers:
- Three stages: Leaders (33% - fully modernized), Challengers (58% - in progress), Observers (9% - planning)
- Modernization strategies: "modernize in place" vs "refactor and shift"
- Case studies: KT Cloud (AI/GPU cloud), Smurfit Westrock (25% cost reduction), PQR (security/automation)

YOUR TASK: Generate 3 sections that feel individually crafted:

1. PERSONALIZED_HOOK (2-3 sentences) - Make them feel SEEN:
   REQUIRED FORMULA: "[Their name], [specific observation about their company/news/situation]... [relevance to AI readiness]"

   MUST use at least 2 of these - BE SPECIFIC:
   ✓ If news is provided: "With [Company]'s recent [specific news topic], now is the time to..."
   ✓ If growth data exists: "[Company]'s [X%] growth means your infrastructure needs are evolving..."
   ✓ If employee count: "At [X] employees, [Company] is at a critical inflection point for..."
   ✓ If funding stage: "As a [Series B/C] company, [Company] is positioned to..."
   ✓ Their title: "As [Title], you're balancing [specific priority for that role]..."

   BANNED: "organizations like yours", "companies in your industry", "professionals like you"

2. CASE_STUDY_FRAMING (2-3 sentences) - Create a DIRECT parallel:
   REQUIRED FORMULA: "[Case study company] faced [challenge] similar to what [Their company] is navigating... [specific result with metric]"

   MUST include:
   ✓ Case study name + their company name in same sentence
   ✓ A specific metric (25% cost reduction, 40% faster, etc.)
   ✓ Direct comparison: "Like [Company]..." or "[Company], like [Case Study]..."
   ✓ Industry/size relevance: "As a fellow [industry/size] organization..."

3. PERSONALIZED_CTA (1-2 sentences) - Drive ACTION specific to their stage:

   REQUIRED by buying stage - be DIRECT and SPECIFIC:
   - AWARENESS: "Discover where [Company] stands on the AI readiness curve—and what the 33% of Leaders are doing differently."
   - CONSIDERATION: "See exactly how [industry] organizations like [Company] are evaluating their modernization options."
   - DECISION: "Get the ROI data and validation [Their title]s need to greenlight [Company]'s AI infrastructure investment."
   - IMPLEMENTATION: "Access the implementation playbook that will accelerate [Company]'s AI infrastructure rollout."

   BANNED: "Download now", "Learn more", "Get started" (too generic)

QUALITY CHECK - Your output must pass these tests:
1. Could another company use this content? If yes, it's too generic - rewrite.
2. Does it mention a specific news item, metric, or company fact? If no, add one.
3. Does the CTA tell them exactly what they'll get for THEIR situation? If no, make it specific.

Output ONLY valid JSON:
{
  "personalized_hook": "Your personalized opening that makes them feel understood...",
  "case_study_framing": "Direct parallel between case study and their company...",
  "personalized_cta": "Stage-specific action that speaks to their exact situation..."
}"""

    def _build_ebook_prompt(
        self,
        profile: Dict[str, Any],
        user_context: Dict[str, Any],
        company_news: Optional[str]
    ) -> str:
        """Build prompt for ebook personalization with deep enrichment data from all APIs."""
        parts = ["Generate DEEPLY personalized AMD ebook content for this prospect.\n"]
        parts.append("IMPORTANT: You have access to comprehensive enrichment data. USE ALL OF IT to create highly specific, relevant content.\n")

        # === PERSON DATA ===
        parts.append("=== PERSON PROFILE ===")
        parts.append(f"Name: {profile.get('first_name', 'Reader')} {profile.get('last_name', '')}")
        parts.append(f"Title: {profile.get('title', 'Professional')}")

        if profile.get('seniority'):
            parts.append(f"Seniority Level: {profile.get('seniority')}")

        if profile.get('skills'):
            skills = profile.get('skills', [])
            if isinstance(skills, list) and skills:
                parts.append(f"Technical Skills: {', '.join(skills[:10])}")
                # Use skills to identify technical depth
                tech_skills = [s for s in skills if s and any(k in s.lower() for k in ['python', 'java', 'cloud', 'aws', 'azure', 'kubernetes', 'docker', 'ai', 'ml', 'data'])]
                if tech_skills:
                    parts.append(f"(IMPORTANT: This person has technical background in: {', '.join(tech_skills[:5])})")

        if profile.get('interests'):
            interests = profile.get('interests', [])
            if isinstance(interests, list) and interests:
                parts.append(f"Professional Interests: {', '.join(interests[:8])}")

        if profile.get('experience'):
            experience = profile.get('experience', [])
            if isinstance(experience, list) and experience:
                parts.append("Career History:")
                for exp in experience[:3]:
                    if isinstance(exp, dict):
                        exp_title = exp.get('title', {}).get('name', '') if isinstance(exp.get('title'), dict) else exp.get('title', '')
                        exp_company = exp.get('company', {}).get('name', '') if isinstance(exp.get('company'), dict) else exp.get('company', '')
                        if exp_title or exp_company:
                            parts.append(f"  - {exp_title} at {exp_company}")

        if profile.get('linkedin_url'):
            parts.append(f"LinkedIn: {profile.get('linkedin_url')}")

        # === COMPANY DATA (Enhanced with PDL Company API) ===
        parts.append("\n=== COMPANY PROFILE (Deep Enrichment) ===")
        company_name = profile.get('company_name') or profile.get('company_display_name') or user_context.get('company', 'their company')
        parts.append(f"Company: {company_name}")
        parts.append(f"Industry: {user_context.get('industry_input') or profile.get('industry', 'Technology')}")

        # Company size context - multiple data points
        if profile.get('employee_count'):
            parts.append(f"Employee Count: {profile.get('employee_count')}")
        if profile.get('employee_count_range'):
            parts.append(f"Size Range: {profile.get('employee_count_range')}")
        elif profile.get('company_size'):
            parts.append(f"Company Size: {profile.get('company_size')}")

        # Company type and status
        if profile.get('company_type'):
            parts.append(f"Company Type: {profile.get('company_type')}")
        if profile.get('ticker'):
            parts.append(f"Stock Ticker: {profile.get('ticker')} (PUBLIC COMPANY)")

        # Founding and maturity
        if profile.get('founded_year'):
            years_old = 2025 - int(profile.get('founded_year'))
            parts.append(f"Founded: {profile.get('founded_year')} ({years_old} years old)")

        # Funding context (important for understanding investment capacity)
        if profile.get('total_funding'):
            parts.append(f"Total Funding Raised: ${profile.get('total_funding'):,}")
        if profile.get('latest_funding_stage'):
            parts.append(f"Funding Stage: {profile.get('latest_funding_stage')}")
        if profile.get('inferred_revenue'):
            parts.append(f"Inferred Revenue: {profile.get('inferred_revenue')}")

        # Growth indicators
        if profile.get('employee_growth_rate'):
            growth = profile.get('employee_growth_rate')
            growth_desc = "rapidly growing" if growth > 0.2 else "growing steadily" if growth > 0 else "stable or contracting"
            parts.append(f"Employee Growth Rate: {growth:.1%} ({growth_desc})")

        # Company description
        if profile.get('company_summary'):
            parts.append(f"Company Summary: {profile.get('company_summary')[:400]}")
        elif profile.get('company_headline'):
            parts.append(f"Company Headline: {profile.get('company_headline')}")
        elif profile.get('company_description'):
            parts.append(f"Company Description: {profile.get('company_description')[:300]}")

        # Company tags (industry signals)
        if profile.get('company_tags'):
            tags = profile.get('company_tags', [])
            if isinstance(tags, list) and tags:
                parts.append(f"Industry Tags: {', '.join(tags[:10])}")
                # Identify AI/tech readiness from tags
                ai_tags = [t for t in tags if t and any(k in t.lower() for k in ['ai', 'machine learning', 'cloud', 'data', 'saas', 'technology'])]
                if ai_tags:
                    parts.append(f"(AI/TECH SIGNALS: Company is associated with: {', '.join(ai_tags)})")

        # NAICS/SIC codes for industry precision
        if profile.get('naics_codes'):
            parts.append(f"NAICS Codes: {profile.get('naics_codes')}")
        if profile.get('sic_codes'):
            parts.append(f"SIC Codes: {profile.get('sic_codes')}")

        # Location context
        location_parts = []
        if profile.get('city'):
            location_parts.append(profile.get('city'))
        if profile.get('state'):
            location_parts.append(profile.get('state'))
        if profile.get('country'):
            location_parts.append(profile.get('country'))
        if location_parts:
            parts.append(f"Location: {', '.join(location_parts)}")

        # Social presence
        if profile.get('company_linkedin'):
            parts.append(f"Company LinkedIn: {profile.get('company_linkedin')}")

        # === EMAIL VERIFICATION (Hunter) ===
        if profile.get('email_verified') is not None:
            parts.append("\n=== EMAIL VERIFICATION ===")
            parts.append(f"Email Verified: {profile.get('email_verified')}")
            if profile.get('email_score'):
                parts.append(f"Email Score: {profile.get('email_score')}")
            if profile.get('email_deliverable'):
                parts.append(f"Deliverable: {profile.get('email_deliverable')}")

        # === USER CONTEXT ===
        parts.append("\n=== BUYER CONTEXT ===")
        goal = user_context.get('goal', '')
        persona = user_context.get('persona', '')

        goal_map = {
            "awareness": "EARLY RESEARCH - just starting to explore, needs education and awareness",
            "consideration": "ACTIVE EVALUATION - comparing solutions, needs differentiation and proof points",
            "decision": "DECISION READY - needs final validation, ROI data, and confidence to proceed",
            "implementation": "IMPLEMENTING NOW - already committed, needs best practices and guidance",
            # Legacy values
            "exploring": "EARLY RESEARCH - discovering what's possible with AI infrastructure",
            "evaluating": "ACTIVE EVALUATION - comparing solutions and building a shortlist",
            "learning": "LEARNING PHASE - deepening expertise on best practices",
            "building_case": "BUILDING BUSINESS CASE - preparing internal proposal for investment"
        }

        persona_map = {
            # Executive Leadership
            "ceo": "CEO/PRESIDENT - cares about: strategic vision, competitive advantage, shareholder value, market leadership",
            "coo": "COO - cares about: operational excellence, efficiency, scalability, execution",
            "c_suite_other": "C-SUITE EXECUTIVE - cares about: strategic outcomes, ROI, competitive advantage, board-level metrics",
            # Technology Leadership
            "cto": "CTO - cares about: technical strategy, innovation, architecture decisions, engineering excellence",
            "cio": "CIO - cares about: IT strategy, digital transformation, system reliability, vendor management",
            "vp_engineering": "VP ENGINEERING - cares about: technical roadmap, team productivity, platform scalability, build vs buy",
            # Security & Compliance
            "ciso": "CISO - cares about: security posture, threat mitigation, compliance frameworks, zero trust",
            "vp_security": "VP SECURITY - cares about: security architecture, risk management, incident response",
            "security_manager": "SECURITY MANAGER - cares about: implementation details, tooling, daily security operations",
            # Data & AI
            "cdo": "CHIEF DATA OFFICER - cares about: data strategy, AI governance, analytics maturity, data monetization",
            "vp_data": "VP DATA/AI - cares about: ML platform, model performance, GPU utilization, MLOps",
            "data_manager": "DATA SCIENCE MANAGER - cares about: team productivity, model deployment, compute costs, training efficiency",
            # Finance
            "cfo": "CFO - cares about: ROI, TCO, capex vs opex, financial risk, budget allocation",
            "vp_finance": "VP FINANCE - cares about: cost optimization, vendor contracts, budget planning",
            "finance_manager": "FINANCE MANAGER - cares about: cost tracking, procurement process, financial controls",
            # IT & Infrastructure
            "vp_it": "VP IT - cares about: infrastructure strategy, reliability, modernization roadmap",
            "it_manager": "IT MANAGER - cares about: uptime, integration, operations, support burden, technical debt",
            "sysadmin": "SYSTEMS ADMIN - cares about: deployment, monitoring, maintenance, documentation",
            # Engineering & Development
            "vp_eng": "VP ENGINEERING - cares about: technical roadmap, team productivity, architecture, delivery velocity",
            "eng_manager": "ENGINEERING MANAGER - cares about: team efficiency, technical decisions, sprint delivery",
            "senior_engineer": "SENIOR ENGINEER - cares about: code quality, performance, architecture patterns, best practices",
            "engineer": "SOFTWARE ENGINEER - cares about: developer experience, tooling, learning opportunities",
            # Operations & Procurement
            "vp_ops": "VP OPERATIONS - cares about: operational efficiency, process optimization, cost control",
            "ops_manager": "OPERATIONS MANAGER - cares about: day-to-day efficiency, workflows, team coordination",
            "procurement": "PROCUREMENT MANAGER - cares about: TCO, vendor comparison, contract terms, risk mitigation",
            # Other
            "other": "PROFESSIONAL - cares about: relevant solutions for their specific challenges",
            # Legacy values (backward compatibility)
            "c_suite": "C-SUITE EXECUTIVE - cares about: strategic outcomes, ROI, competitive advantage, board-level metrics",
            "vp_director": "VP/DIRECTOR - cares about: balancing strategy with execution, team enablement, measurable impact",
            "it_infrastructure": "IT/INFRASTRUCTURE MANAGER - cares about: reliability, integration, operations, technical debt",
            "engineering": "ENGINEERING/DEVOPS - cares about: architecture patterns, deployment, automation, developer experience",
            "data_ai": "DATA/AI ENGINEER - cares about: model performance, GPU efficiency, training costs, inference latency",
            "security": "SECURITY/COMPLIANCE - cares about: data protection, governance, audit trails, regulatory compliance",
            "executive": "EXECUTIVE - cares about: strategic outcomes, ROI, competitive advantage",
            "sales_gtm": "SALES/GTM LEADER - cares about: revenue impact, competitive differentiation",
            "hr_people": "HR/PEOPLE OPS - cares about: workforce enablement, skill development"
        }

        if goal:
            parts.append(f"Buying Stage: {goal_map.get(goal, goal)}")
        if persona:
            parts.append(f"Role & Priorities: {persona_map.get(persona, persona)}")

        # Company size context from user input
        company_size = user_context.get('company_size', '')
        if company_size:
            size_info = get_company_size_info(company_size)
            parts.append(f"Company Segment: {size_info['label'].upper()} ({size_info['employee_range']} employees)")
            if size_info['segment'] == 'enterprise':
                parts.append("(ENTERPRISE CONTEXT: Focus on scale, compliance, integration with existing systems)")
            elif size_info['segment'] == 'mid_market':
                parts.append("(MID-MARKET CONTEXT: Balance cost efficiency with capability, growth-focused)")
            elif size_info['segment'] == 'smb':
                parts.append("(SMB CONTEXT: Focus on simplicity, time-to-value, cost-effectiveness)")

        # === COMPANY NEWS (Enhanced GNews with multi-query analysis) ===
        parts.append("\n=== COMPANY NEWS & MARKET INTELLIGENCE ===")
        if company_news and company_news.strip():
            parts.append(f"News Summary: {company_news[:700]}")

        # News themes detected
        news_themes = profile.get('news_themes', [])
        if news_themes and isinstance(news_themes, list):
            parts.append(f"Detected Themes: {', '.join(news_themes)}")
            # Highlight relevant themes for AMD positioning
            ai_themes = [t for t in news_themes if t and ('ai' in t.lower() or 'cloud' in t.lower() or 'digital' in t.lower())]
            if ai_themes:
                parts.append(f"(IMPORTANT - AI/CLOUD THEMES DETECTED: {', '.join(ai_themes)})")

        # News sentiment analysis
        sentiment = profile.get('news_sentiment', {})
        if sentiment and isinstance(sentiment, dict):
            pos = sentiment.get('positive', 0)
            neg = sentiment.get('negative', 0)
            if pos > neg + 2:
                parts.append(f"Sentiment: POSITIVE ({pos} positive indicators, {neg} negative)")
            elif neg > pos + 2:
                parts.append(f"Sentiment: CHALLENGING ({neg} negative indicators, {pos} positive)")
            else:
                parts.append(f"Sentiment: NEUTRAL/MIXED")

        # Categorized news by topic
        news_by_category = profile.get('news_by_category', {})
        if news_by_category and isinstance(news_by_category, dict):
            if news_by_category.get('ai_technology'):
                parts.append("AI/Tech News: Company has recent AI/technology coverage")
            if news_by_category.get('growth'):
                parts.append("Growth News: Company has recent growth/expansion coverage")
            if news_by_category.get('leadership'):
                parts.append("Leadership News: Company has recent leadership/strategy coverage")

        # Recent news headlines with source
        recent_news = profile.get('recent_news', [])
        if recent_news and isinstance(recent_news, list):
            parts.append("\nRecent Headlines:")
            for i, article in enumerate(recent_news[:5]):
                if isinstance(article, dict):
                    title = article.get('title', '')
                    source = article.get('source', '')
                    content = article.get('content', '')[:200] if article.get('content') else ''
                    category = article.get('query_category', '')
                    if title:
                        parts.append(f"  {i+1}. [{category.upper()}] {title}")
                        if source:
                            parts.append(f"     Source: {source}")
                        if content:
                            parts.append(f"     Summary: {content}...")

        if not recent_news and not company_news:
            parts.append("No recent news found - use industry trends instead")

        # === CASE STUDY SELECTION ===
        parts.append("\n=== CASE STUDY TO HIGHLIGHT ===")
        # IMPORTANT: Prioritize user-selected industry from form over API-derived data
        user_industry = (user_context.get('industry_input') or '').lower()
        api_industry = (profile.get('industry') or '').lower()

        # Map frontend industry values to case study categories
        industry_to_case_study = {
            # Healthcare -> PQR Healthcare
            'healthcare': 'healthcare',
            'life_sciences': 'healthcare',
            # Financial -> PQR Financial
            'financial_services': 'financial',
            'banking': 'financial',
            # Manufacturing/Retail/Energy -> Smurfit Westrock
            'manufacturing': 'manufacturing',
            'retail_ecommerce': 'manufacturing',
            'energy_utilities': 'manufacturing',
            # Telecom/Tech -> KT Cloud (only for explicitly tech companies)
            'technology': 'telecom_tech',
            'telecommunications': 'telecom_tech',
            # Others -> PQR General
            'government': 'general',
            'education': 'general',
            'professional_services': 'general',
        }

        # Determine case study based on USER-SELECTED industry first
        case_study = industry_to_case_study.get(user_industry, None)

        # If no user industry match, check API industry (but be more selective)
        if not case_study:
            if any(k in api_industry for k in ['health', 'pharma', 'medical', 'biotech', 'life science']):
                case_study = 'healthcare'
            elif any(k in api_industry for k in ['financ', 'bank', 'insurance']):
                case_study = 'financial'
            elif any(k in api_industry for k in ['manufact', 'industrial', 'energy', 'utilities', 'retail', 'consumer goods']):
                case_study = 'manufacturing'
            elif any(k in api_industry for k in ['telecom', 'media', 'entertainment', 'gaming']):
                case_study = 'telecom_tech'
            # Only use 'technology' as a last resort if it's very explicit
            elif 'software' in api_industry or api_industry == 'technology':
                case_study = 'telecom_tech'
            else:
                case_study = 'general'

        # Output the selected case study
        if case_study == 'healthcare':
            parts.append("Selected: PQR + Healthcare angle - compliance, patient data, security")
            parts.append("Key angles: HIPAA compliance, secure AI, data governance")
            parts.append("Metrics to highlight: Compliance, security, patient outcome improvements")
        elif case_study == 'financial':
            parts.append("Selected: PQR + Financial angle - security, compliance, automation")
            parts.append("Key angles: regulatory compliance, fraud detection, risk management")
            parts.append("Metrics to highlight: Compliance, processing speed, risk reduction")
        elif case_study == 'manufacturing':
            parts.append("Selected: SMURFIT WESTROCK - manufacturing, cost optimization, sustainability")
            parts.append("Key angles: 25% cost reduction, carbon footprint, operational efficiency")
            parts.append("Metrics to highlight: Cost savings, sustainability, operational uptime")
        elif case_study == 'telecom_tech':
            parts.append("Selected: KT CLOUD - AI/GPU cloud services, massive scale, innovation focus")
            parts.append("Key angles: cloud-native AI, GPU acceleration, developer platform")
            parts.append("Metrics to highlight: Scale, performance, time-to-market")
        else:
            parts.append("Selected: PQR - IT services, security, automation")
            parts.append("Key angles: automation, security, operational excellence")
            parts.append("Metrics to highlight: Efficiency, security posture, automation ROI")

        # === BUILD MANDATORY DATA SUMMARY ===
        # This tells the LLM exactly what data points it MUST use
        parts.append("\n=== MANDATORY DATA TO REFERENCE ===")
        parts.append("You MUST use these data points in your output:\n")

        mandatory_items = []
        mandatory_items.append(f"✓ COMPANY NAME: \"{company_name}\" (USE THIS EXACT NAME)")

        # News - most important for personalization
        if recent_news and isinstance(recent_news, list) and len(recent_news) > 0:
            first_article = recent_news[0]
            if isinstance(first_article, dict) and first_article.get('title'):
                news_title = first_article.get('title', '')[:80]
                mandatory_items.append(f"✓ RECENT NEWS: \"{news_title}\" - REFERENCE THIS IN THE HOOK")

        if news_themes and isinstance(news_themes, list) and len(news_themes) > 0:
            mandatory_items.append(f"✓ NEWS THEMES: {', '.join(news_themes[:3])} - WEAVE INTO HOOK")

        # Company size/scale
        if profile.get('employee_count'):
            emp = profile.get('employee_count')
            mandatory_items.append(f"✓ EMPLOYEE COUNT: {emp:,} employees - USE FOR SCALE CONTEXT" if isinstance(emp, int) else f"✓ EMPLOYEE COUNT: {emp} - USE FOR SCALE CONTEXT")
        elif profile.get('company_size'):
            mandatory_items.append(f"✓ COMPANY SIZE: {profile.get('company_size')} - USE FOR SCALE CONTEXT")

        # Funding/growth
        if profile.get('latest_funding_stage'):
            mandatory_items.append(f"✓ FUNDING STAGE: {profile.get('latest_funding_stage')} - MENTION IN CONTEXT")
        if profile.get('employee_growth_rate') and isinstance(profile.get('employee_growth_rate'), (int, float)):
            growth = profile.get('employee_growth_rate')
            if growth > 0:
                mandatory_items.append(f"✓ GROWTH RATE: {growth:.0%} employee growth - REFERENCE AS 'RAPID GROWTH'")

        # Person's role
        if profile.get('title'):
            mandatory_items.append(f"✓ THEIR TITLE: {profile.get('title')} - TAILOR TONE TO THIS ROLE")
        if profile.get('seniority'):
            mandatory_items.append(f"✓ SENIORITY: {profile.get('seniority')} - MATCH STRATEGIC VS TACTICAL")

        # Industry
        effective_industry = user_context.get('industry_input') or profile.get('industry', '')
        if effective_industry:
            mandatory_items.append(f"✓ INDUSTRY: {effective_industry} - USE INDUSTRY-SPECIFIC LANGUAGE")

        # Buying stage
        if goal:
            mandatory_items.append(f"✓ BUYING STAGE: {goal.upper()} - MATCH CTA TO THIS STAGE")

        for item in mandatory_items:
            parts.append(item)

        # Case study specifics
        parts.append(f"\n✓ CASE STUDY TO REFERENCE: Use the case study selected above")
        if case_study == 'healthcare':
            parts.append("   - Name: PQR")
            parts.append("   - Metric to cite: 40% faster threat detection, HIPAA compliance")
        elif case_study == 'financial':
            parts.append("   - Name: PQR")
            parts.append("   - Metric to cite: 40% faster threat detection, regulatory compliance")
        elif case_study == 'manufacturing':
            parts.append("   - Name: Smurfit Westrock")
            parts.append("   - Metric to cite: 25% cost reduction, 30% emissions reduction")
        elif case_study == 'telecom_tech':
            parts.append("   - Name: KT Cloud")
            parts.append("   - Metric to cite: Massive scale AI/GPU deployment, cloud-native platform")
        else:
            parts.append("   - Name: PQR")
            parts.append("   - Metric to cite: 40% efficiency gains, security automation")

        parts.append("\n=== OUTPUT REQUIREMENTS ===")
        parts.append("Your JSON output MUST pass these tests:")
        parts.append(f"\n1. PERSONALIZED_HOOK must:")
        parts.append(f"   ✓ Start with \"{company_name}\" (exact company name)")
        if recent_news and isinstance(recent_news, list) and len(recent_news) > 0:
            parts.append(f"   ✓ Reference a SPECIFIC news item or theme detected above")
        if profile.get('employee_count'):
            parts.append(f"   ✓ Reference the company scale ({profile.get('employee_count'):,} employees)" if isinstance(profile.get('employee_count'), int) else f"   ✓ Reference the company scale")
        if profile.get('latest_funding_stage'):
            parts.append(f"   ✓ Reference their growth stage ({profile.get('latest_funding_stage')})")
        parts.append(f"   ✗ DO NOT use generic phrases like 'organizations like yours' or 'companies in your industry'")
        parts.append(f"   ✗ DO NOT use clichés like 'in today's rapidly evolving landscape'")

        parts.append(f"\n2. CASE_STUDY_FRAMING must:")
        parts.append(f"   ✓ Name both the case study company AND \"{company_name}\" in the same sentence")
        parts.append(f"   ✓ Include at least ONE specific metric (percentage, number, timeframe)")
        parts.append(f"   ✓ Draw a DIRECT parallel: 'Like {company_name}, [case study] faced...'")
        parts.append(f"   ✗ DO NOT just describe the case study without connecting to their company")

        parts.append(f"\n3. PERSONALIZED_CTA must:")
        parts.append(f"   ✓ Include \"{company_name}\" explicitly")
        parts.append(f"   ✓ Use {goal.upper() if goal else 'AWARENESS'}-appropriate action verb:")
        if goal in ['awareness', 'exploring', 'learning']:
            parts.append(f"      (AWARENESS: discover, learn, see, understand)")
        elif goal in ['consideration', 'evaluating']:
            parts.append(f"      (CONSIDERATION: compare, evaluate, assess, explore options)")
        elif goal in ['decision', 'building_case']:
            parts.append(f"      (DECISION: get the data, validate, confirm, access the proof)")
        elif goal in ['implementation']:
            parts.append(f"      (IMPLEMENTATION: access the playbook, accelerate, implement)")
        else:
            parts.append(f"      (Match to their {goal or 'awareness'} stage)")
        parts.append(f"   ✗ DO NOT use generic CTAs like 'learn more' or 'get started'")

        parts.append("\n=== EXAMPLE OUTPUT FORMAT ===")
        parts.append("{")
        parts.append(f'  "personalized_hook": "{company_name}\'s [specific news/theme/growth signal]...",')
        parts.append(f'  "case_study_framing": "Like {company_name}, [Case Study] faced [similar challenge]...",')
        parts.append(f'  "personalized_cta": "[Action verb] where {company_name} stands on the AI readiness curve..."')
        parts.append("}")
        parts.append("\nGENERATE THE JSON NOW:")

        return "\n".join(parts)

    def _parse_ebook_response(self, content: str) -> Optional[Dict[str, str]]:
        """Parse ebook personalization response."""
        try:
            json_match = re.search(
                r'\{[^{}]*"personalized_hook"[^{}]*"case_study_framing"[^{}]*"personalized_cta"[^{}]*\}',
                content,
                re.DOTALL
            )
            if json_match:
                data = json.loads(json_match.group())
                if all(k in data for k in ["personalized_hook", "case_study_framing", "personalized_cta"]):
                    return data
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error for ebook response: {e}")
        return None

    def _mock_ebook_response(
        self,
        profile: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate personalized ebook content when LLM API not available.
        Uses all available enrichment data for maximum personalization."""
        user_context = user_context or {}
        first_name = profile.get('first_name', 'Reader')
        company = profile.get('company_name') or profile.get('company_display_name') or user_context.get('company', 'your organization')
        title = profile.get('title', 'leader')
        industry = user_context.get('industry_input') or profile.get('industry', 'your industry')
        goal = user_context.get('goal', 'awareness')
        persona = user_context.get('persona', 'c_suite')

        # Enhanced enrichment data
        company_size = profile.get('company_size', '')
        company_news = profile.get('company_context', '')
        recent_news = profile.get('recent_news', [])
        seniority = profile.get('seniority', '')
        employee_count = profile.get('employee_count', '')

        # New enhanced data points
        news_themes = profile.get('news_themes', [])
        sentiment = profile.get('news_sentiment', {})
        company_tags = profile.get('company_tags', [])
        company_summary = profile.get('company_summary', '')
        total_funding = profile.get('total_funding', '')
        funding_stage = profile.get('latest_funding_stage', '')
        growth_rate = profile.get('employee_growth_rate', 0)
        company_type = profile.get('company_type', '')
        skills = profile.get('skills', [])

        # Build news reference using actual headlines/themes
        news_ref = ""
        if recent_news and len(recent_news) > 0:
            first_headline = recent_news[0].get('title', '') if isinstance(recent_news[0], dict) else ''
            if first_headline:
                news_ref = f" With recent news like \"{first_headline[:60]}...\", "
        elif news_themes and len(news_themes) > 0 and news_themes[0]:
            news_ref = f" With {company}'s focus on {news_themes[0].lower()}, "
        elif company_news and len(company_news) > 20:
            news_ref = f" Given recent developments at {company}, "

        # Build rich company context
        size_context = ""
        if employee_count:
            size_context = f" As a {employee_count:,}-employee organization, " if isinstance(employee_count, int) else f" As a {employee_count}-person organization, "
        elif company_size:
            size_context = f" As a {company_size} company, "

        # Growth context
        growth_context = ""
        if growth_rate and isinstance(growth_rate, (int, float)):
            if growth_rate > 0.2:
                growth_context = f" With {company}'s rapid growth ({growth_rate:.0%} employee growth), "
            elif growth_rate > 0:
                growth_context = f" As {company} continues to scale, "

        # Funding/stage context
        funding_context = ""
        if funding_stage:
            funding_context = f" as a {funding_stage} company"
        elif company_type and company_type != 'private':
            funding_context = f" as a {company_type} company"

        # Technical skills context
        tech_context = ""
        if skills and isinstance(skills, list):
            ai_skills = [s for s in skills[:10] if s and any(k in s.lower() for k in ['ai', 'ml', 'python', 'data', 'cloud'])]
            if ai_skills:
                tech_context = f" Given your background in {', '.join(ai_skills[:2])}, "

        # Hook based on buying stage - hyper-personalized with specific data points
        # Build the hook dynamically to ensure we use available data
        hook_parts = []

        # Always start with their name
        hook_parts.append(f"{first_name},")

        # Add news reference if we have it (most specific signal)
        if news_ref:
            hook_parts.append(news_ref.strip())
        # Otherwise use growth or size context
        elif growth_context:
            hook_parts.append(growth_context.strip())
        elif size_context:
            hook_parts.append(size_context.strip())

        # Stage-specific core message with company name
        stage_messages = {
            "awareness": f"understanding where {company} stands on the AI readiness curve is the critical first step. Only 33% of enterprises have reached 'Leader' status—this guide shows you what separates them from the rest.",
            "consideration": f"as you evaluate AI infrastructure options for {company}, the key is finding what works for your specific {industry} challenges. This guide provides the comparison frameworks that {title}s need to make the right call.",
            "decision": f"you're at the decision point for {company}'s AI infrastructure. This guide delivers the ROI validation and proof points that will give you confidence to move forward—and help you bring your stakeholders along.",
            "implementation": f"with {company} already committed to this path, execution is everything. This guide provides the technical playbook and pitfalls to avoid that will accelerate your timeline.",
            # Legacy values
            "exploring": f"as {company} explores what's possible with AI infrastructure, this guide maps out the landscape. You'll see exactly where your peers stand and what's driving the 33% who've reached Leader status.",
            "evaluating": f"evaluating AI infrastructure for {company} means cutting through the noise. This guide provides the head-to-head comparisons and decision criteria that {title}s in {industry} are using.",
            "learning": f"staying ahead in {industry} requires understanding where AI infrastructure is heading. This guide distills the trends and strategies that matter most for {company}.",
            "building_case": f"building the business case for {company}'s AI investment requires hard data. This guide provides the ROI frameworks and proof points that resonate with executive stakeholders."
        }

        core_message = stage_messages.get(goal, stage_messages.get("awareness"))
        hook_parts.append(core_message)

        hook = " ".join(part for part in hook_parts if part).replace("  ", " ").strip()

        # Legacy hooks dict for backwards compatibility
        hooks = {
            "awareness": hook,
            "consideration": hook,
            "decision": hook,
            "implementation": hook,
            "exploring": hook,
            "evaluating": hook,
            "learning": hook,
            "building_case": hook
        }

        # CTA based on persona and stage - hyper-specific with action verbs
        # Stage-specific CTAs that include company name and speak to their priorities
        stage_ctas = {
            "awareness": {
                "c_suite": f"Discover where {company} ranks among the 33% of AI Leaders—and what it takes to join them.",
                "cto": f"See the technical indicators that separate AI Leaders from Challengers—and where {company}'s infrastructure stands today.",
                "cio": f"Get the IT transformation roadmap that {industry} CIOs are using to modernize for AI.",
                "cdo": f"Understand the data infrastructure patterns that enable AI at scale—built for organizations like {company}.",
                "vp_director": f"Learn the modernization playbook that's moving {industry} organizations from Challengers to Leaders.",
                "vp_engineering": f"Explore the architecture decisions that will shape {company}'s AI infrastructure for the next decade.",
                "it_infrastructure": f"See the technical blueprint for AI-ready data centers—validated by {industry} peers.",
                "data_ai": f"Learn how AMD Instinct accelerators are delivering the performance {company}'s AI workloads demand.",
                "security": f"Understand how {industry} security leaders are enabling AI while maintaining compliance.",
                "procurement": f"Get the TCO framework for evaluating {company}'s AI infrastructure investment options.",
                "default": f"Discover where {company} stands on the AI readiness curve—and what the Leaders are doing differently."
            },
            "consideration": {
                "c_suite": f"See the ROI data that {industry} executives are using to justify AI infrastructure investments.",
                "cto": f"Compare modernization approaches: the technical trade-offs {title}s at companies like {company} need to weigh.",
                "cio": f"Evaluate the infrastructure options: in-place modernization vs. refactor-and-shift for {company}.",
                "cdo": f"Compare data platform architectures: what's working for AI-first {industry} organizations.",
                "vp_director": f"See how {industry} leaders chose their AI infrastructure path—with the metrics that drove their decisions.",
                "vp_engineering": f"Get the technical comparison: architecture patterns, performance benchmarks, and integration paths for {company}.",
                "it_infrastructure": f"Compare in-place vs. refactor approaches: technical trade-offs, timelines, and risk profiles for {company}.",
                "data_ai": f"See the GPU benchmarks: training throughput, inference latency, and cost-per-model comparisons.",
                "security": f"Review the security architectures that regulated {industry} organizations are using for AI adoption.",
                "procurement": f"Access the vendor comparison framework with evaluation criteria tailored for {industry}.",
                "default": f"See how organizations like {company} are evaluating their AI infrastructure options—with real comparison data."
            },
            "decision": {
                "c_suite": f"Get the board-ready business case with ROI projections for {company}'s AI infrastructure investment.",
                "cto": f"Access the technical validation that will give you confidence to recommend {company}'s infrastructure direction.",
                "cio": f"Get the decision framework with the metrics that matter for {company}'s AI transformation.",
                "cdo": f"Validate your data infrastructure strategy with benchmarks from leading {industry} organizations.",
                "vp_director": f"Get the decision toolkit: ROI models, risk matrices, and stakeholder talking points for {company}.",
                "vp_engineering": f"Access the technical decision framework that will help you greenlight {company}'s AI infrastructure path.",
                "it_infrastructure": f"Get the technical proof points to confidently recommend {company}'s AI infrastructure direction.",
                "data_ai": f"Validate your GPU strategy with the performance data that justifies AMD Instinct for {company}.",
                "security": f"Get the compliance validation: how modern AI infrastructure meets {industry} security requirements.",
                "procurement": f"Access the final evaluation data: TCO comparisons and vendor assessments for {company}'s decision.",
                "default": f"Get the validation data and ROI framework that will help {company} make the right AI infrastructure decision."
            },
            "implementation": {
                "c_suite": f"Access the executive playbook for driving successful AI infrastructure adoption at {company}.",
                "cto": f"Get the implementation roadmap: architecture patterns, integration guides, and rollout timelines for {company}.",
                "cio": f"Access the change management playbook for {company}'s AI infrastructure transformation.",
                "cdo": f"Get the MLOps implementation guide: from data pipelines to model deployment at {company}.",
                "vp_director": f"Access the program management toolkit for {company}'s AI infrastructure rollout.",
                "vp_engineering": f"Get the engineering playbook: deployment patterns, testing strategies, and operational runbooks.",
                "it_infrastructure": f"Access the technical runbooks: infrastructure setup, monitoring, and day-2 operations for AI workloads.",
                "data_ai": f"Get the AI platform implementation guide: from GPU provisioning to production ML pipelines.",
                "security": f"Access the security implementation checklist for {company}'s AI infrastructure deployment.",
                "procurement": f"Get the vendor management guide for {company}'s ongoing AI infrastructure relationship.",
                "default": f"Access the implementation playbook that will accelerate {company}'s AI infrastructure rollout."
            }
        }

        # Map legacy goal values to new stages
        goal_stage_map = {
            "exploring": "awareness",
            "evaluating": "consideration",
            "learning": "awareness",
            "building_case": "decision"
        }
        mapped_goal = goal_stage_map.get(goal, goal) or "awareness"

        # Map persona to a lookup key
        persona_key = persona
        if persona in ["c_suite", "ceo", "coo", "c_suite_other"]:
            persona_key = "c_suite"
        elif persona in ["cfo", "vp_finance", "finance_manager"]:
            persona_key = "c_suite"  # Finance uses exec messaging
        elif persona in ["ciso", "vp_security", "security_manager"]:
            persona_key = "security"
        elif persona in ["vp_data", "data_manager"]:
            persona_key = "data_ai"
        elif persona in ["vp_it", "it_manager", "sysadmin"]:
            persona_key = "it_infrastructure"
        elif persona in ["vp_eng", "eng_manager", "senior_engineer", "engineer"]:
            persona_key = "vp_engineering"
        elif persona in ["vp_ops", "ops_manager"]:
            persona_key = "vp_director"

        # Get the stage-specific CTAs
        stage_dict = stage_ctas.get(mapped_goal, stage_ctas["awareness"])
        cta = stage_dict.get(persona_key, stage_dict.get("default", f"Get the insights that will help {company} accelerate its AI infrastructure journey."))

        # Legacy ctas dict for backward compatibility (not used but kept for structure)
        ctas = {}

        # Case study framing based on USER-SELECTED industry (not API tags which are often wrong)
        # Map frontend industry values to case study categories
        user_industry = (user_context.get('industry_input') or '').lower()

        industry_to_case_study = {
            # Healthcare -> PQR Healthcare
            'healthcare': 'healthcare',
            'life_sciences': 'healthcare',
            # Financial -> PQR Financial
            'financial_services': 'financial',
            'banking': 'financial',
            # Manufacturing/Retail/Energy -> Smurfit Westrock
            'manufacturing': 'manufacturing',
            'retail_ecommerce': 'manufacturing',
            'energy_utilities': 'manufacturing',
            # Telecom/Tech -> KT Cloud (only for explicitly tech companies)
            'technology': 'telecom_tech',
            'telecommunications': 'telecom_tech',
            # Others -> PQR General
            'government': 'general',
            'education': 'general',
            'professional_services': 'general',
        }

        # Determine case study based on USER-SELECTED industry first
        case_study = industry_to_case_study.get(user_industry, None)

        # If no user industry match, check API industry (but be more selective)
        if not case_study:
            industry_lower = (industry or "").lower()
            if any(k in industry_lower for k in ['health', 'pharma', 'medical', 'biotech', 'life science']):
                case_study = 'healthcare'
            elif any(k in industry_lower for k in ['financ', 'bank', 'insurance']):
                case_study = 'financial'
            elif any(k in industry_lower for k in ['manufact', 'industrial', 'energy', 'utilities', 'retail', 'consumer goods']):
                case_study = 'manufacturing'
            elif any(k in industry_lower for k in ['telecom', 'media', 'entertainment', 'gaming']):
                case_study = 'telecom_tech'
            elif 'software' in industry_lower or industry_lower == 'technology':
                case_study = 'telecom_tech'
            else:
                case_study = 'general'

        # Generate case framing based on selected case study - direct parallels with specific metrics
        if case_study == 'healthcare':
            size_parallel = f" Like {company}, they're a {company_size} organization" if company_size else ""
            case_framing = f"PQR faced the same challenge {company} navigates daily: enabling AI-driven innovation while maintaining HIPAA-grade data protection.{size_parallel}. Their result? 40% faster threat detection and automated compliance workflows—without compromising security. For {title}s in healthcare, this playbook shows exactly how to balance innovation with the compliance requirements that define your industry."
        elif case_study == 'financial':
            case_framing = f"{company}, like PQR, operates in an industry where a single security incident can mean regulatory action and reputational damage. PQR's modernization achieved 40% faster threat detection and automated compliance reporting—while actually strengthening their security posture.{funding_context} For financial services organizations evaluating AI infrastructure, this case study shows how to move fast without breaking trust."
        elif case_study == 'manufacturing':
            growth_parallel = f" {company}'s growth trajectory" if growth_rate and growth_rate > 0 else f" organizations like {company}"
            case_framing = f"Smurfit Westrock tackled the exact challenge facing{growth_parallel}: scaling operations while hitting sustainability targets. Their modernization delivered 25% cost reduction and 30% emissions cut simultaneously.{size_context}As a {title} driving operational efficiency, you'll see the specific infrastructure decisions that made this possible."
        elif case_study == 'telecom_tech':
            scale_ref = f" At {employee_count:,} employees," if isinstance(employee_count, int) else f" As a {company_size} organization," if company_size else ""
            case_framing = f"KT Cloud faced {company}'s exact challenge: scaling AI compute fast enough to meet demand while keeping costs sustainable.{scale_ref} their AMD Instinct deployment enabled massive GPU-accelerated workloads with the efficiency their business model demanded.{growth_context}The architecture decisions they made translate directly to {company}'s situation."
        else:
            case_framing = f"PQR's transformation mirrors what {company} is working toward: modernized infrastructure that enables AI workloads while maintaining enterprise-grade security. As a {title} at {company},{size_context}you'll recognize the challenges they solved—and see how their 40% efficiency gains were achieved step by step."

        # hook variable is already set above with the stage_messages logic
        # cta variable is already set above with the stage_ctas logic

        return {
            "personalized_hook": hook.strip(),
            "case_study_framing": case_framing.strip(),
            "personalized_cta": cta.strip(),
            "model_used": "mock",
            "tokens_used": 0,
            "latency_ms": 0,
            "enrichment_data_used": {
                "has_news_themes": bool(news_themes),
                "has_skills": bool(skills),
                "has_funding_data": bool(funding_stage or total_funding),
                "has_growth_data": bool(growth_rate),
                "has_company_tags": bool(company_tags),
                "news_article_count": len(recent_news)
            }
        }
