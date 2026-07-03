"""
Intent Classifier
Uses LLM to understand what a customer's message means.
Returns intent type and extracted entities.
"""
import json
from typing import Dict, Any, Tuple
from openai import AsyncOpenAI
from src.config import settings
from src.utils.logging import logger


class IntentClassifier:
    """
    Classifies customer messages into intents.
    
    Intents:
    - product_inquiry: Asking about product features, coverage, benefits
    - price_inquiry: Asking about price, premium, cost
    - comparison: Comparing two or more products
    - quotation_request: Asking for a formal quote
    - general_faq: Business hours, location, process questions
    - human_escalation: Complaint or demand to speak to human
    - off_topic: Not business related
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def classify(self, message: str, mode: str = "agent") -> Tuple[str, float, Dict[str, Any]]:
        """
        Classify a customer message.
        
        Returns:
            intent: The classified intent
            confidence: How confident the LLM is (0.0 - 1.0)
            entities: Extracted information (product names, quantities, etc.)
        """
        
        prompt = self._build_prompt(message, mode)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent classifier. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            
            # Clean up - remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]

            result = json.loads(result_text)
            
            intent = result.get("intent", "general_faq")
            confidence = float(result.get("confidence", 0.5))
            entities = result.get("entities", {})
            language = result.get("language", "en")

            logger.info(f"Intent: {intent} (confidence: {confidence}, language: {language})")
            return intent, confidence, entities

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return "general_faq", 0.3, {}
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "general_faq", 0.3, {}

    def _build_prompt(self, message: str, mode: str) -> str:
        """Build the classification prompt based on mode."""
        
        if mode == "agent":
            context = """
You are classifying messages for an insurance/property/car agent's AI assistant.
Customers may use informal Bahasa Melayu mixed with English (Malaysian WhatsApp style).
Understand slang like: "plan medical best utk family", "brp harga sebulan", "nak quote boleh", "ada cover hospital gov ke", "yg ni cover apa".
Understand short forms: yg (yang), utk (untuk), nak (hendak), tak/takde (tidak), dah (sudah), pun, je (sahaja), ke (kah).
Understand code-switching between BM and English.

INTENTS:
- product_inquiry: Asking about coverage, features, benefits of a policy/property/car
- price_inquiry: Asking about premium, price, cost, monthly payment
- comparison: Comparing two or more products/policies/properties
- quotation_request: Explicitly asking for a quote, quotation, or formal document
- general_faq: Business hours, location, process, warranty, claims process
- human_escalation: Complaint, angry tone, demanding human, complex issue
- off_topic: Not business related at all
"""
        elif mode == "shop":
            context = """
You are classifying messages for a retail shop's AI assistant.
Customers may use informal Bahasa Melayu mixed with English (Malaysian WhatsApp style).
Understand slang like: "ada stock ke", "brp harga", "nak beli", "boleh order tak".
Understand short forms: yg (yang), utk (untuk), nak (hendak), tak/takde (tidak), dah (sudah).

INTENTS:
- stock_check: Asking if something is available or in stock
- price_inquiry: Asking how much something costs
- quotation_request: Asking for a formal quote or bulk pricing
- general_faq: Business hours, location, return policy, warranty
- human_escalation: Complaint, demanding human, complex issue
- off_topic: Not business related
"""
        else:
            context = """
You are classifying messages for a service provider's AI assistant.
Customers may use informal Bahasa Melayu mixed with English (Malaysian WhatsApp style).
Understand slang like: "ada slot tak", "brp harga", "nak booking", "available ke".
Understand short forms: yg (yang), utk (untuk), nak (hendak), tak/takde (tidak), dah (sudah).

INTENTS:
- availability_check: Asking about available dates or slots
- price_inquiry: Asking about pricing or packages
- booking_request: Wanting to make a booking or reservation
- general_faq: Business hours, location, service details
- human_escalation: Complaint, demanding human, complex issue
- off_topic: Not business related
"""

        return f"""{context}

CUSTOMER MESSAGE: "{message}"

Return ONLY a JSON object (no markdown, no explanation):
{{
    "intent": "one of the intents above",
    "confidence": 0.0-1.0,
    "language": "en" or "bm",
    "entities": {{
        "product_name": "extracted product/policy/property name or null",
        "quantity": number or null,
        "provider": "company name if mentioned or null",
        "specific_question": "what they are actually asking or null"
    }}
}}"""