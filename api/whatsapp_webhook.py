import logging
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from twilio.twiml.messaging_response import MessagingResponse
from pipeline.voice_engine import VoiceEngine
from pipeline.vision_engine import VisionEngine
import httpx
import os

router = APIRouter()
log = logging.getLogger("WhatsAppWebhook")

voice_engine = VoiceEngine()
vision_engine = VisionEngine()

# In a real environment, we'd use Redis for this session mapping
# Mapping: WhatsApp_Number -> {"department": str, "state_code": str, "emp_id": str}
MOCK_REDIS_SESSIONS = {}

async def download_twilio_media(media_url: str) -> bytes:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        log.warning("Twilio credentials missing. Using mock bytes.")
        return b"mock_media_bytes"
        
    async with httpx.AsyncClient() as client:
        response = await client.get(media_url, auth=(account_sid, auth_token))
        if response.status_code == 200:
            return response.content
        raise ValueError(f"Failed to download media: {response.status_code}")

def handle_registration(sender: str, text: str) -> str:
    # Example format: "Register Health 12345"
    parts = text.split()
    if len(parts) >= 3 and parts[0].lower() == "register":
        dept = parts[1]
        emp_id = parts[2]
        MOCK_REDIS_SESSIONS[sender] = {"department": dept, "state_code": "TN", "emp_id": emp_id}
        return f"Successfully registered {emp_id} under {dept} department. You can now send voice notes or photos."
    return "You are not registered. Please reply with: Register [Department] [Emp_ID]"

@router.post("/api/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    sender = form_data.get("From", "")
    body = form_data.get("Body", "").strip()
    num_media = int(form_data.get("NumMedia", 0))
    message_type = form_data.get("MessageType", "text")
    
    twiml = MessagingResponse()
    
    # Check registration
    session = MOCK_REDIS_SESSIONS.get(sender)
    if not session:
        if body.lower().startswith("register"):
            reply = handle_registration(sender, body)
            twiml.message(reply)
            return str(twiml)
        else:
            twiml.message("Please register first. Send: Register [Department] [Emp_ID]")
            return str(twiml)
            
    dept = session["department"]
    
    try:
        if message_type == "audio" or num_media > 0 and form_data.get("MediaContentType0", "").startswith("audio/"):
            # Voice Message
            media_url = form_data.get("MediaUrl0")
            audio_bytes = await download_twilio_media(media_url)
            
            transcript = voice_engine.transcribe(audio_bytes, format="ogg")
            question = transcript["text"]
            
            # Mock Query Router
            answer = f"[Mock WhatsApp Voice Answer] Department: {dept}. Understood: {question}"
            
            twiml.message(f"🎤 {transcript['language_name']} detected:\n{question}\n\n🤖 Answer:\n{answer}")
            
        elif message_type == "image" or num_media > 0 and form_data.get("MediaContentType0", "").startswith("image/"):
            # Image Message
            media_url = form_data.get("MediaUrl0")
            image_bytes = await download_twilio_media(media_url)
            
            question = body if body else "Explain this image."
            result = vision_engine.process_image_query(image_bytes, question, dept, "TN")
            
            answer = f"🖼 Image processed ({result['image_type']}):\n{result['answer']}"
            twiml.message(answer)
            
        else:
            # Text Message
            # Mock Query Router
            answer = f"[Mock WhatsApp Text Answer] Department: {dept}. You asked: {body}"
            twiml.message(answer)
            
    except Exception as e:
        log.error(f"WhatsApp Error: {e}")
        twiml.message("Sorry, an error occurred while processing your request.")

    return str(twiml)
