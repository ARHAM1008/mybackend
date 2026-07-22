"""
AI Service: Integrates with OpenAI GPT to evaluate system design interviews.
Falls back to mock responses when API key is not configured.
"""

import json
import random
from typing import Optional
from app.core.config import settings
from loguru import logger


def _build_evaluation_prompt(challenge: dict, answer: dict) -> str:
    """Build the system design evaluation prompt for OpenAI."""
    return f"""You are a Senior Staff Software Engineer conducting a System Design interview at a top tech company (Google, Amazon, Meta level).

## Challenge
Title: {challenge.get('title', 'Unknown')}
Description: {challenge.get('description', '')}
Requirements: {challenge.get('requirements', '')}
Functional Requirements: {challenge.get('functional_requirements', '')}
Non-Functional Requirements: {challenge.get('non_functional_requirements', '')}
Expected Scale: {challenge.get('expected_scale', '')}

## Candidate's Design Choices
- Database: {answer.get('database_choice', 'Not specified')}
- Cache: {answer.get('cache_choice', 'Not specified')}
- Authentication: {answer.get('auth_choice', 'Not specified')}
- Architecture: {answer.get('architecture_choice', 'Not specified')}
- Communication: {answer.get('communication_choice', 'Not specified')}
- Object Storage: {answer.get('storage_choice', 'Not specified')}
- Message Queue: {answer.get('queue_choice', 'Not specified')}
- Monitoring: {answer.get('monitoring_choice', 'Not specified')}

## Candidate's Explanations
Architecture: {answer.get('architecture_explanation', 'Not provided')}
API Design: {answer.get('api_design', 'Not provided')}
Scaling Strategy: {answer.get('scaling_strategy', 'Not provided')}
Database Design: {answer.get('database_design', 'Not provided')}
Failure Handling: {answer.get('failure_handling', 'Not provided')}
Security Design: {answer.get('security_design', 'Not provided')}
Cost Optimization: {answer.get('cost_optimization', 'Not provided')}

## Instructions
Evaluate this candidate's system design. Be thorough but encouraging. Score each category from 0-100. Provide specific, actionable feedback. Ask challenging follow-up questions that would help them deepen their understanding.

Respond ONLY with valid JSON in this exact format:
{{
  "scores": {{
    "architecture_score": <0-100>,
    "database_score": <0-100>,
    "scalability_score": <0-100>,
    "availability_score": <0-100>,
    "consistency_score": <0-100>,
    "security_score": <0-100>,
    "api_design_score": <0-100>,
    "cost_score": <0-100>,
    "monitoring_score": <0-100>,
    "overall_score": <0-100>
  }},
  "feedback": {{
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2", "weakness3"],
    "recommendations": ["recommendation1", "recommendation2", "recommendation3"],
    "follow_up_questions": ["question1", "question2", "question3", "question4", "question5"],
    "overall_feedback": "Comprehensive paragraph of overall feedback",
    "architecture_feedback": "Specific feedback on architecture choices",
    "database_feedback": "Specific feedback on database design",
    "scalability_feedback": "Specific feedback on scaling strategy",
    "security_feedback": "Specific feedback on security design"
  }}
}}"""


def _build_followup_prompt(challenge: dict, answer: dict, question: str) -> str:
    """Build a follow-up question evaluation prompt."""
    return f"""You are a Senior Staff Software Engineer conducting a System Design interview. The candidate designed a system for: {challenge.get('title', 'Unknown')}.

Their architecture choices: Database={answer.get('database_choice', 'N/A')}, Cache={answer.get('cache_choice', 'N/A')}, Architecture={answer.get('architecture_choice', 'N/A')}.

Follow-up question asked: {question}

Provide a thoughtful response that:
1. Acknowledges the question
2. Explains the trade-offs involved
3. Suggests what a strong answer would cover
4. Does NOT give away the complete solution - guide the student to think

Respond in JSON format:
{{
  "response": "Your detailed response here",
  "hints": ["hint1", "hint2"],
  "key_concepts": ["concept1", "concept2"]
}}"""


def _generate_mock_evaluation(challenge: dict, answer: dict) -> dict:
    """Generate a realistic mock evaluation when OpenAI is unavailable."""
    base_score = 55
    has_explanation = bool(answer.get('architecture_explanation', '').strip())
    if has_explanation:
        base_score += 15

    def score():
        return min(100, max(20, base_score + random.randint(-15, 25)))

    scores = {
        "architecture_score": score(),
        "database_score": score(),
        "scalability_score": score(),
        "availability_score": score(),
        "consistency_score": score(),
        "security_score": score(),
        "api_design_score": score(),
        "cost_score": score(),
        "monitoring_score": score(),
    }
    scores["overall_score"] = round(sum(scores.values()) / 9, 1)

    db = answer.get('database_choice', 'your database')
    arch = answer.get('architecture_choice', 'your architecture')
    cache = answer.get('cache_choice', 'your cache')
    challenge_title = challenge.get('title', 'the system')

    feedback = {
        "strengths": [
            f"Good choice of {db} for {challenge_title}'s data requirements",
            f"The {arch} approach shows understanding of system boundaries",
            "Consideration of caching strategy demonstrates awareness of performance needs",
        ],
        "weaknesses": [
            "Scaling strategy could be more detailed with specific metrics and thresholds",
            "Failure handling needs more concrete fallback mechanisms",
            "Security design should address more edge cases and threat models",
        ],
        "recommendations": [
            f"Consider how {db} handles partition tolerance at the expected scale",
            "Add specific SLA targets (99.9% uptime, <200ms P95 latency)",
            f"Elaborate on how {cache} invalidation works in your design",
            "Include capacity estimation for storage and bandwidth",
        ],
        "follow_up_questions": [
            f"Why did you choose {db} over alternatives? What trade-offs did you consider?",
            f"How would your {arch} handle a 10x traffic spike during peak hours?",
            f"What happens if your {cache or 'cache layer'} goes down? Describe the fallback path.",
            "How do you ensure data consistency across services during network partitions?",
            "Walk me through a write path - from user action to data persistence. Where are the failure points?",
        ],
        "overall_feedback": f"Your design for {challenge_title} shows a solid foundation. You've made reasonable technology choices and demonstrated understanding of core concepts. To strengthen your design, focus on providing more detailed scaling strategies with specific numbers, elaborate failure handling paths, and consider edge cases in your security model. Think about how each component interacts under failure conditions.",
        "architecture_feedback": f"Your {arch} approach is reasonable for this scale. Consider documenting the boundaries between services more clearly and how they communicate during failure scenarios.",
        "database_feedback": f"Using {db} is a defensible choice. Elaborate on your schema design, indexing strategy, and how you'd handle data that grows over time (archival, partitioning).",
        "scalability_feedback": "The scaling strategy needs more specificity. Include concrete numbers: expected QPS, storage growth rate, and at what thresholds you'd trigger scaling events.",
        "security_feedback": "Security considerations are present but need depth. Address authentication, authorization, rate limiting, input validation, and data encryption at rest and in transit.",
    }

    return {"scores": scores, "feedback": feedback}


async def evaluate_interview(challenge: dict, answer: dict) -> dict:
    """
    Evaluate an interview submission using OpenAI GPT or mock fallback.
    Returns dict with 'scores' and 'feedback' keys.
    """
    # Try OpenAI if API key is configured
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key":
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = _build_evaluation_prompt(challenge, answer)

            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a senior system design interviewer. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=3000,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            logger.info("AI evaluation completed successfully via OpenAI")
            return result

        except Exception as e:
            logger.error(f"OpenAI evaluation failed: {e}. Falling back to mock.")
            return _generate_mock_evaluation(challenge, answer)
    else:
        logger.info("No OpenAI API key configured. Using mock evaluation.")
        return _generate_mock_evaluation(challenge, answer)


async def generate_followup_response(challenge: dict, answer: dict, question: str) -> dict:
    """
    Generate a response to a follow-up question.
    """
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key":
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = _build_followup_prompt(challenge, answer, question)

            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a senior system design mentor. Respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"OpenAI follow-up failed: {e}")

    # Mock follow-up response
    return {
        "response": f"Great question! When thinking about '{question}', consider the trade-offs between consistency and availability. A strong answer would discuss specific failure modes, recovery strategies, and how your system degrades gracefully under load.",
        "hints": [
            "Think about what happens when individual components fail",
            "Consider the CAP theorem trade-offs for your specific use case",
        ],
        "key_concepts": ["fault tolerance", "graceful degradation", "circuit breakers"],
    }
