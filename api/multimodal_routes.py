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
            
        # 2. Query (Mocked call to query_router for testing without full pipeline coupling here)
        # In real code: result = query_router.route_and_query(transcript["text"], user.department, "TN")
        answer = f"Mock Answer for transcribed text: {transcript['text']}"
        
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
            "sources": [],
            "confidence": 0.95,
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
        result = vision_engine.process_image_query(image_bytes, question, user.department, "TN")
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
            fmt = audio.filename.split('.')[-1] if '.' in audio.filename else "webm"
            tr = voice_engine.transcribe(ab, fmt)
            transcript_lang = tr["language"]
            inputs.append(f"[Voice query in {tr['language_name']}]: {tr['text']}")
            
        if image:
            ib = await image.read()
            img_q = text or "Describe this image"
            img_res = vision_engine.process_image_query(ib, img_q, user.department, "TN")
            content = img_res.get("extracted_text") or img_res.get("image_analysis")
            inputs.append(f"[Image content]: {content}")
            
        if text and not image:
            inputs.append(f"[Typed query]: {text}")
            
        unified_question = "\n".join(inputs)
        
        # Mock Router call
        answer = f"Multimodal Answer based on: {unified_question}"
        
        response = {
            "answer": answer,
            "query_id": str(uuid.uuid4()),
            "unified_query": unified_question,
            "sources": []
        }
        
        if audio and voice_engine.tts_enabled:
            import base64
            audio_ans = voice_engine.text_to_speech(answer, transcript_lang)
            response["audio_answer_base64"] = base64.b64encode(audio_ans).decode()
            
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
