import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from typing import Optional
from auth.dependencies import get_current_user
from pipeline.voice_engine import VoiceEngine
from pipeline.vision_engine import VisionEngine

router = APIRouter()

voice_engine = VoiceEngine()
vision_engine = VisionEngine()

# ----------------- VOICE ENDPOINTS -----------------

@router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    hint_language: Optional[str] = Form(None),
    user=Depends(get_current_user)
):
    try:
        audio_bytes = await audio.read()
        format = audio.filename.split('.')[-1] if '.' in audio.filename else "webm"
        result = voice_engine.transcribe(audio_bytes, format, hint_language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/query")
async def voice_query(
    audio: UploadFile = File(...),
    top_k: Optional[int] = Form(5),
    user=Depends(get_current_user)
):
    try:
        audio_bytes = await audio.read()
        format = audio.filename.split('.')[-1] if '.' in audio.filename else "webm"
        
        # 1. Transcribe
        transcript = voice_engine.transcribe(audio_bytes, format)
        if not transcript["success"]:
            raise ValueError(transcript.get("error", "Failed to transcribe"))
            
        # 2. Query via Real Router call
        from api.main import router_instance
        if not router_instance:
            raise HTTPException(status_code=503, detail="Document Intelligence Router engine offline.")
            
        filters = {}
        if user.get("state_code"):
            filters["state_code"] = user.get("state_code")
            
        router_response = router_instance.route_and_query(transcript["text"], user.get("department"), filters)
        answer = router_response["answer"]
        
        # 3. TTS
        audio_answer_bytes = voice_engine.text_to_speech(answer, transcript["language"])
        import base64
        audio_b64 = base64.b64encode(audio_answer_bytes).decode()
        
        return {
            "transcribed_text": transcript["text"],
            "detected_language": transcript["language"],
            "answer": answer,
            "audio_answer_base64": audio_b64,
            "audio_format": "mp3",
            "sources": router_response.get("sources", []),
            "confidence": router_response.get("confidence", 0.0),
            "query_id": str(uuid.uuid4())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/tts")
async def generate_tts(
    text: str = Form(...),
    language: str = Form(...),
    format: str = Form("mp3"),
    user=Depends(get_current_user)
):
    try:
        audio_bytes = voice_engine.text_to_speech(text, language, format)
        return Response(content=audio_bytes, media_type=f"audio/{format}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- VISION ENDPOINTS -----------------

@router.post("/vision/query")
async def vision_query(
    image: UploadFile = File(...),
    question: Optional[str] = Form("Extract and explain all text and information in this image."),
    top_k: Optional[int] = Form(5),
    user=Depends(get_current_user)
):
    try:
        image_bytes = await image.read()
        result = vision_engine.process_image_query(image_bytes, question, user.get("department"), "TN")
        result["query_id"] = str(uuid.uuid4())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vision/extract")
async def extract_vision(
    image: UploadFile = File(...),
    user=Depends(get_current_user)
):
    try:
        image_bytes = await image.read()
        img = vision_engine.preprocess_image(image_bytes)
        result = vision_engine.extract_text_from_document(img)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- UNIFIED MULTIMODAL ENDPOINT -----------------

@router.post("/multimodal/query")
async def multimodal_query(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    top_k: Optional[int] = Form(5),
    user=Depends(get_current_user)
):
    if not any([audio, image, text]):
        raise HTTPException(status_code=400, detail="Must provide at least one of audio, image, or text.")
        
    inputs = []
    transcript_lang = "en"
    
    try:
        if audio:
            ab = await audio.read()
            # Fix 3.3: Payload size check (20MB)
            if len(ab) > 20 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Audio file too large. Maximum upload size is 20MB.")
            fmt = audio.filename.split('.')[-1] if '.' in audio.filename else "webm"
            tr = voice_engine.transcribe(ab, fmt)
            # Fix 3.1: Handle low-confidence or unsupported language
            if not tr.get("success", True):
                raise HTTPException(status_code=400, detail=tr.get("message", "Audio transcription failed."))
            transcript_lang = tr["language"]
            inputs.append(f"[Voice query in {tr['language_name']}]: {tr['text']}")
            
        if image:
            ib = await image.read()
            # Fix 3.3: Payload size check (20MB)
            if len(ib) > 20 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Image file too large. Maximum upload size is 20MB.")
            img_q = text or "Describe this image"
            img_res = vision_engine.process_image_query(ib, img_q, user.get("department"), "TN")
            content = img_res.get("extracted_text") or img_res.get("image_analysis")
            inputs.append(f"[Image content]: {content}")
            
        if text and not image:
            inputs.append(f"[Typed query]: {text}")
            
        unified_question = "\n".join(inputs)
        
        # Real Router call
        from api.main import router_instance
        if not router_instance:
            raise HTTPException(status_code=503, detail="Document Intelligence Router engine offline.")
            
        # Optional filters based on User
        filters = {}
        if user.get("state_code"):
            filters["state_code"] = user.get("state_code")
            
        # Route and Query using the main pipeline
        router_response = router_instance.route_and_query(unified_question, user.get("department"), filters)
        
        answer = router_response["answer"]
        
        response = {
            "answer": answer,
            "query_id": str(uuid.uuid4()),
            "unified_query": unified_question,
            "sources": router_response.get("sources", []),
            "query_type": router_response.get("query_type", "MULTIMODAL")
        }
        
        if audio and voice_engine.tts_enabled:
            import base64
            audio_ans = voice_engine.text_to_speech(answer, transcript_lang)
            response["audio_answer_base64"] = base64.b64encode(audio_ans).decode()
            
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
