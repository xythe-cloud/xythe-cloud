"""
Message Processor
The central pipeline. Every incoming WhatsApp message flows through here.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.models.tenant import Tenant
from src.models.interaction import Interaction, DailyStats
from src.engine.intent_classifier import IntentClassifier
from src.services.vector_store import VectorStoreManager
from src.utils.logging import logger


class MessageProcessor:
    """
    Main message processing pipeline.
    
    Flow:
    1. Look up tenant by WhatsApp phone number ID
    2. Classify the message intent
    3. Search tenant's knowledge base
    4. Generate response
    5. Log everything
    """

    def __init__(self, db: Session, phone_number_id: str):
        self.db = db
        self.phone_number_id = phone_number_id
        self.classifier = IntentClassifier()
        self.vector_store = VectorStoreManager()
        self.tenant = None

    async def process(
        self, from_number: str, message_text: str
    ) -> Dict[str, Any]:
        """
        Process an incoming message.
        Returns response dict with text and optional quote info.
        """
        start_time = datetime.utcnow()

        # Step 1: Find the tenant
        self.tenant = await self._find_tenant()
        if not self.tenant:
            logger.warning(f"No tenant found for phone_number_id: {self.phone_number_id}")
            return {"response": None}

        # Step 2: Check limits
        if self.tenant.query_limit_reached:
            return {
                "response": "You've reached your monthly query limit. Upgrade to continue using Xythe."
            }

        # Step 3: Classify intent
        intent, confidence, entities = await self.classifier.classify(
            message_text, self.tenant.mode
        )

        # Get detected language from entities
        detected_language = entities.get("language", "en") if entities else "en"

        # Step 4: Route to handler based on intent
        response_text = await self._handle_intent(
            intent, entities, message_text, detected_language
        )

        # Step 5: Log interaction
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        await self._log_interaction(
            from_number, message_text, intent, confidence,
            response_text, response_time
        )

        # Step 6: Update daily stats
        await self._update_stats()

        return {"response": response_text}

    async def _find_tenant(self) -> Optional[Tenant]:
        """Find tenant by WhatsApp phone number ID."""
        result = await self.db.execute(
            select(Tenant).where(
                Tenant.whatsapp_phone_id == self.phone_number_id,
                Tenant.subscription_status == "active"
            )
        )
        return result.scalar_one_or_none()

    async def _handle_intent(
        self, intent: str, entities: Dict[str, Any], original_message: str, language: str = "en"
    ) -> str:
        """Route to the appropriate handler based on intent."""
        
        handlers = {
            "product_inquiry": lambda: self._handle_product_inquiry(entities, original_message, language),
            "price_inquiry": lambda: self._handle_price_inquiry(entities, original_message, language),
            "comparison": lambda: self._handle_comparison(entities, original_message, language),
            "quotation_request": lambda: self._handle_quotation_request(entities, original_message, language),
            "general_faq": lambda: self._handle_faq(entities, original_message, language),
            "human_escalation": lambda: self._handle_escalation(entities, original_message, language),
            "off_topic": lambda: self._handle_off_topic(entities, original_message, language),
        }

        handler = handlers.get(intent, lambda: self._handle_faq(entities, original_message, language))
        return handler()

    async def _handle_product_inquiry(
        self, entities: Dict, original: str, language: str = "en"
    ) -> str:
        """Customer asking about product features or coverage."""
        product_name = entities.get("product_name", original)
        provider = entities.get("provider")

        # Build filter if provider specified
        filters = None
        if provider:
            filters = {"provider": provider}

        # Search knowledge base
        results = await self.vector_store.search(
            tenant_id=self.tenant.id,
            query=product_name or original,
            top_k=3,
            filter_criteria=filters
        )

        if not results or results[0]["score"] < 0.5:
            if language == "bm":
                return (
                    "Maaf, saya tidak jumpa maklumat tentang tu. "
                    "Boleh tanya dengan lebih spesifik? "
                    "Pemilik saya juga telah dimaklumkan."
                )
            return (
                "I couldn't find specific information about that. "
                "Could you rephrase your question or specify which product "
                "you're asking about? My owner has also been notified."
            )

        # Build response from top results
        if language == "bm":
            response = "Ini yang saya jumpa:\n\n"
            for i, result in enumerate(results[:2]):
                response += f"{result['text']}\n"
                if i < len(results[:2]) - 1:
                    response += "---\n"
            response += "\nNak saya sediakan sebut harga atau bandingkan dengan produk lain?"
            return response

        response = "Here's what I found:\n\n"
        for i, result in enumerate(results[:2]):
            response += f"{result['text']}\n"
            if i < len(results[:2]) - 1:
                response += "---\n"
        response += "\nWould you like me to generate a quotation or compare this with other products?"
        return response

    async def _handle_price_inquiry(
        self, entities: Dict, original: str, language: str = "en"
    ) -> str:
        """Customer asking about price or premium."""
        product_name = entities.get("product_name", original)

        results = await self.vector_store.search(
            tenant_id=self.tenant.id,
            query=f"price premium cost {product_name}",
            top_k=3
        )

        if not results or results[0]["score"] < 0.5:
            if language == "bm":
                return (
                    "Saya tak jumpa maklumat harga untuk tu. "
                    "Pemilik saya akan dapatkan butiran dan hubungi anda sebentar lagi."
                )
            return (
                "I couldn't find pricing information for that. "
                "My owner will get back to you with the details shortly."
            )

        if language == "bm":
            response = "Ini maklumat harga:\n\n"
            response += results[0]["text"]
            response += "\n\nNak saya sediakan sebut harga rasmi?"
            return response

        response = "Here's the pricing information:\n\n"
        response += results[0]["text"]
        response += "\n\nWould you like a formal quotation?"
        return response

    async def _handle_comparison(
        self, entities: Dict, original: str, language: str = "en"
    ) -> str:
        """Customer wants to compare products."""
        # Search for both products
        results = await self.vector_store.search(
            tenant_id=self.tenant.id,
            query=original,
            top_k=5
        )

        if len(results) < 2:
            if language == "bm":
                return (
                    "Saya perlukan lebih maklumat untuk buat perbandingan. "
                    "Boleh nyatakan produk mana yang nak dibandingkan?"
                )
            return (
                "I need more information to make a comparison. "
                "Could you specify which products you'd like to compare?"
            )

        if language == "bm":
            response = "Perbandingan:\n\n"
            for result in results[:4]:
                response += f"• {result['text'][:300]}\n\n"
            response += "Nak saya bantu pilih yang terbaik untuk keperluan anda?"
            return response

        response = "Here's a comparison:\n\n"
        for result in results[:4]:
            response += f"• {result['text'][:300]}\n\n"
        response += "Would you like me to help you decide which is better for your needs?"
        return response

    async def _handle_quotation_request(
        self, entities: Dict, original: str, language: str = "en"
    ) -> str:
        """Customer wants a formal quote."""
        # For MVP, we acknowledge and notify the owner
        # Full quote generation comes in Week 4
        if language == "bm":
            return (
                "Baik! Saya akan sediakan sebut harga. "
                "Pemilik saya akan sahkan butiran dan hantar segera. "
                "Ada apa-apa yang nak ditambah?"
            )
        return (
            "I can help with that! Let me prepare a quotation for you. "
            "I'll need to confirm a few details with my owner first. "
            "You'll receive your quotation shortly. "
            "Is there anything specific you'd like included?"
        )

    async def _handle_faq(
        self, entities: Dict, original: str, language: str = "en"
    ) -> str:
        """General FAQ or process question."""
        results = await self.vector_store.search(
            tenant_id=self.tenant.id,
            query=original,
            top_k=2
        )

        if results and results[0]["score"] > 0.5:
            return results[0]["text"]

        if language == "bm":
            return (
                "Saya tak pasti tentang tu. "
                "Boleh tanya semula? "
                "Atau taip 'help' untuk bercakap dengan pemilik saya."
            )
        return (
            "I'm not sure about that. Could you rephrase your question? "
            "Or type 'help' to speak with my owner directly."
        )

    async def _handle_escalation(
        self, entities: Dict, original: str, language: str = "en"
    ) -> str:
        """Customer wants to speak to a human."""
        if language == "bm":
            return (
                "Saya faham. Pemilik saya akan hubungi anda secepat mungkin. "
                "Ada perkara lain yang boleh saya bantu sementara menunggu?"
            )
        return (
            "I understand you'd like to speak with someone directly. "
            "I've notified my owner and they'll get back to you as soon as possible. "
            "Is there anything urgent I can help with in the meantime?"
        )

    async def _handle_off_topic(
        self, entities: Dict, original: str, language: str = "en"
    ) -> str:
        """Message not related to business."""
        if language == "bm":
            return (
                "Saya Xythe, pembantu AI untuk urusan perniagaan. "
                "Saya boleh bantu dengan soalan produk, harga, dan sebut harga. "
                "Ada yang boleh saya bantu?"
            )
        return (
            "I'm Xythe, an AI assistant focused on helping with business inquiries. "
            "I can help with product questions, pricing, and quotations. "
            "What can I help you with today?"
        )

    async def _log_interaction(
        self,
        from_number: str,
        message_text: str,
        intent: str,
        confidence: float,
        response_text: str,
        response_time_ms: int
    ):
        """Log the interaction to database."""
        interaction_id = f"int_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        interaction = Interaction(
            id=interaction_id,
            tenant_id=self.tenant.id,
            customer_phone=from_number,
            direction="inbound",
            channel="whatsapp",
            message_text=message_text[:1000],
            intent=intent,
            confidence=confidence,
            response_text=response_text[:1000] if response_text else None,
            action_taken="answered",
            llm_model=settings.OPENAI_MODEL if hasattr(settings, 'OPENAI_MODEL') else None,
            response_time_ms=response_time_ms,
        )

        self.db.add(interaction)
        await self.db.flush()

    async def _update_stats(self):
        """Update daily stats counter."""
        today = datetime.utcnow().date()

        # Check if stats row exists for today
        result = await self.db.execute(
            select(DailyStats).where(
                DailyStats.tenant_id == self.tenant.id,
                DailyStats.date == today
            )
        )
        stats = result.scalar_one_or_none()

        if stats:
            stats.queries_total += 1
            stats.queries_answered += 1
        else:
            stats = DailyStats(
                tenant_id=self.tenant.id,
                date=today,
                queries_total=1,
                queries_answered=1,
            )
            self.db.add(stats)

        # Update tenant usage counter
        self.tenant.monthly_queries_used += 1
        self.tenant.last_active = datetime.utcnow()

        await self.db.flush()