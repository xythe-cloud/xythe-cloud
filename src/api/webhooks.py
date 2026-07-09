"""
WhatsApp Webhook Handler
Receives incoming messages and sends auto-replies.
"""
from fastapi import APIRouter, Request, HTTPException
from src.services.whatsapp_client import WhatsAppClient
from src.engine.intent_classifier import IntentClassifier
from src.services.vector_store import VectorStoreManager
from src.utils.logging import logger

router = APIRouter(prefix="/webhook", tags=["webhooks"])
whatsapp = WhatsAppClient()

# Initialize services
classifier = IntentClassifier()
vector_store = VectorStoreManager()


@router.get("/whatsapp")
async def verify_webhook(request: Request):
    """WhatsApp verification endpoint."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    result = await whatsapp.verify_webhook(mode, token, challenge)

    if result is not None:
        logger.info("WhatsApp webhook verified successfully")
        return result
    else:
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_message(request: Request):
    """
    Receive incoming WhatsApp messages and send auto-replies.
    This is the core loop: Receive → Understand → Search → Reply
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    if body.get("object") != "whatsapp_business_account":
        return {"status": "ok"}

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue

            value = change.get("value", {})
            messages = value.get("messages", [])
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")

            for message in messages:
                if message.get("type") != "text":
                    continue

                from_number = message.get("from")
                message_id = message.get("id")
                text = message.get("body", "")

                if not from_number or not text:
                    continue

                logger.info(f"📱 Message from {from_number}: {text[:100]}")

                # Mark as read
                await whatsapp.mark_as_read(phone_number_id, message_id)

                # ─── PROCESS THE MESSAGE ───
                try:
                    # Step 1: Classify intent
                    intent, confidence, entities = await classifier.classify(
                        text, mode="agent"
                    )
                    language = entities.get("language", "en") if entities else "en"
                    logger.info(f"🧠 Intent: {intent} ({confidence:.0%}) | Language: {language}")

                    # Step 2: Handle based on intent
                    reply = await build_reply(intent, entities, text, language)

                    # Step 3: Send reply
                    if reply:
                        await whatsapp.send_text(
                            phone_number_id=phone_number_id,
                            to=from_number,
                            text=reply
                        )
                        logger.info(f"✅ Reply sent to {from_number}")

                except Exception as e:
                    logger.error(f"Processing failed: {e}")
                    # Send fallback message
                    await whatsapp.send_text(
                        phone_number_id=phone_number_id,
                        to=from_number,
                        text="I'm having trouble processing your request right now. My owner will get back to you shortly."
                    )

    return {"status": "ok"}


async def build_reply(intent: str, entities: dict, original_text: str, language: str) -> str:
    """
    Build a reply based on intent and search results.
    """
    tenant_id = "demo_workspace"  # Hardcoded for now — will be dynamic after auth

    # ─── HUMAN ESCALATION ───
    if intent == "human_escalation":
        if language == "bm":
            return (
                "Saya faham. Saya telah memaklumkan pemilik saya dan mereka akan menghubungi anda secepat mungkin. "
                "Ada perkara lain yang boleh saya bantu sementara menunggu?"
            )
        return (
            "I understand. I've notified my owner and they'll get back to you as soon as possible. "
            "Is there anything else I can help with in the meantime?"
        )

    # ─── OFF TOPIC ───
    if intent == "off_topic":
        if language == "bm":
            return (
                "Saya Xythe, pembantu AI untuk urusan perniagaan. "
                "Saya boleh bantu dengan soalan tentang produk, harga, dan sebut harga. "
                "Ada yang boleh saya bantu hari ini?"
            )
        return (
            "I'm Xythe, an AI assistant focused on business inquiries. "
            "I can help with product questions, pricing, and quotations. "
            "How can I help you today?"
        )

    # ─── SEARCH KNOWLEDGE BASE ───
    product_name = entities.get("product_name", original_text)
    provider = entities.get("provider")

    filters = None
    if provider:
        filters = {"provider": provider}

    results = await vector_store.search(
        tenant_id=tenant_id,
        query=product_name or original_text,
        top_k=3,
        filter_criteria=filters
    )

    # ─── NO RESULTS ───
    if not results or results[0]["score"] < 0.4:
        if language == "bm":
            return (
                "Maaf, saya tidak jumpa maklumat tentang perkara itu dalam dokumen yang dimuat naik. "
                "Pemilik saya akan membantu anda sebentar lagi. "
                "Boleh saya tahu lebih lanjut tentang apa yang anda cari?"
            )
        return (
            "I couldn't find specific information about that in the uploaded documents. "
            "My owner will get back to you shortly. "
            "Could you tell me more about what you're looking for?"
        )

    # ─── BUILD RESPONSE FROM RESULTS ───
    best = results[0]
    response_text = best["text"]

    # ─── PRODUCT INQUIRY ───
    if intent == "product_inquiry":
        if language == "bm":
            reply = "Ini yang saya jumpa tentang produk tersebut:\n\n"
            reply += response_text
            reply += "\n\nNak saya sediakan sebut harga atau bandingkan dengan produk lain?"
            return reply
        else:
            reply = "Here's what I found about that product:\n\n"
            reply += response_text
            reply += "\n\nWould you like me to generate a quotation or compare this with other products?"
            return reply

    # ─── PRICE INQUIRY ───
    if intent == "price_inquiry":
        if language == "bm":
            reply = "Ini maklumat harga yang saya jumpa:\n\n"
            reply += response_text
            reply += "\n\nNak sebut harga rasmi untuk produk ini?"
            return reply
        else:
            reply = "Here's the pricing information I found:\n\n"
            reply += response_text
            reply += "\n\nWould you like a formal quotation for this?"
            return reply

    # ─── COMPARISON ───
    if intent == "comparison":
        comparison_text = "\n\n".join([r["text"][:300] for r in results[:2]])
        if language == "bm":
            reply = "Ini perbandingan yang saya jumpa:\n\n"
            reply += comparison_text
            reply += "\n\nNak saya bantu pilih yang terbaik untuk keperluan anda?"
            return reply
        else:
            reply = "Here's a comparison based on the documents:\n\n"
            reply += comparison_text
            reply += "\n\nWould you like me to help you decide which is best for your needs?"
            return reply

    # ─── QUOTATION REQUEST ───
    if intent == "quotation_request":
        if language == "bm":
            return (
                "Baik! Saya akan sediakan sebut harga untuk anda. "
                "Pemilik saya akan menyemak dan menghantarnya segera. "
                "Ada apa-apa yang spesifik yang anda mahu masukkan?"
            )
        return (
            "Sure! I'll prepare a quotation for you. "
            "My owner will review and send it shortly. "
            "Is there anything specific you'd like included?"
        )

    # ─── GENERAL FAQ ───
    if language == "bm":
        reply = "Ini yang saya jumpa:\n\n"
        reply += response_text
        reply += "\n\nAda soalan lain yang boleh saya bantu?"
        return reply
    else:
        reply = "Here's what I found:\n\n"
        reply += response_text
        reply += "\n\nIs there anything else I can help with?"
        return reply