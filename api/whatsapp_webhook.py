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
    # Example format: "Register Finance 12345"
    parts = text.split()
    if len(parts) >= 3 and parts[0].lower() == "register":
        dept = parts[1].lower()  # "finance", "legal", "health"
        emp_id = parts[2]
        MOCK_REDIS_SESSIONS[sender] = {"department": dept, "vertical": dept, "state_code": "TN", "emp_id": emp_id}
        return f"Successfully registered {emp_id} under {dept.capitalize()} mode. You can now send queries, voice notes, or photos."
    return "You are not registered. Please reply with: Register [Vertical] [Emp_ID] (e.g. Register Finance 12345)"

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
            twiml.message("Please register first. Send: Register [Vertical] [Emp_ID] (e.g. Register Legal 12345)")
            return str(twiml)
            
    dept = session["department"]
    
    # Import router instance safely inside function
    from api.main import router_instance
    if not router_instance:
        twiml.message("System is currently booting or AI router is offline. Please try again later.")
        return str(twiml)

    def build_citation_footer(result):
        footer = ""
        if result.get("cited_cases") and len(result["cited_cases"]) > 0:
            footer += "\n\n⚖ Sources:\n"
            for c in result["cited_cases"]:
                footer += f"- {c['name']} ({c['year']}) {c['citation']}\n"
        if result.get("circulars_cited") and len(result["circulars_cited"]) > 0:
            footer += "\n\n📄 Sources:\n"
            for c in result["circulars_cited"]:
                footer += f"- Circular No. {c['number']}\n"
        return footer
    
    try:
        if message_type == "audio" or num_media > 0 and form_data.get("MediaContentType0", "").startswith("audio/"):
            # Voice Message
            media_url = form_data.get("MediaUrl0")
            audio_bytes = await download_twilio_media(media_url)
            
            transcript = voice_engine.transcribe(audio_bytes, format="ogg")
            question = transcript["text"]
            
            # Real Query Router
            result = router_instance.route_and_query(question, dept)
            answer = result["answer"]
            footer = build_citation_footer(result)
            
            twiml.message(f"🎤 {transcript['language_name']} detected:\n{question}\n\n🤖 Answer:\n{answer}{footer}")
            
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
            result = router_instance.route_and_query(body, dept)
            answer = result["answer"]
            footer = build_citation_footer(result)
            
            twiml.message(f"🤖 {answer}{footer}")
            
    except Exception as e:
        log.error(f"WhatsApp Error: {e}")
        twiml.message("Sorry, an error occurred while processing your request.")

    return str(twiml)
