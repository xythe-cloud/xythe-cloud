"""
WhatsApp Webhook Handler
Receives incoming messages from Meta and routes them to the message processor.
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from src.database.connection import get_db, SessionLocal
from src.services.whatsapp_client import WhatsAppClient
from src.engine.message_processor import MessageProcessor
from src.utils.logging import logger

router = APIRouter(prefix="/webhook", tags=["webhooks"])
whatsapp = WhatsAppClient()


@router.get("/whatsapp")
async def verify_webhook(request: Request):
    """
    WhatsApp verification endpoint.
    Meta sends a GET request to verify you own this URL.
    """
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
    db = SessionLocal()
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    # Check this is a message notification
    if body.get("object") != "whatsapp_business_account":
        return {"status": "ok"}

    # Process each entry
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue

            value = change.get("value", {})
            messages = value.get("messages", [])
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")

            for message in messages:
                # Only handle text messages for now
                if message.get("type") != "text":
                    continue

                from_number = message.get("from")
                message_id = message.get("id")
                text = message.get("text", {}).get("body", "")

                if not from_number or not text:
                    continue

                logger.info(f"Message from {from_number}: {text[:100]}")

                # Mark as read (blue ticks)
                await whatsapp.mark_as_read(phone_number_id, message_id)

                # Process the message
                try:
                    processor = MessageProcessor(db, phone_number_id)
                    result = await processor.process(from_number, text)

                    # Send response
                    if result.get("response"):
                        await whatsapp.send_text(
                            phone_number_id=phone_number_id,
                            to=from_number,
                            text=result["response"]
                        )

                except Exception as e:
                    logger.error(f"Processing failed: {e}")
                    # Send fallback
                    await whatsapp.send_text(
                        phone_number_id=phone_number_id,
                        to=from_number,
                        text="Sorry, I encountered an issue. My owner will get back to you shortly."
                    )

        db.close()
    return {"status": "ok"}