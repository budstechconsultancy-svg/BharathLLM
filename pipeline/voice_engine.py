import os
import io
import tempfile
import logging

log = logging.getLogger("VoiceEngine")

WHISPER_LANG_MAP = {
    "ta": "Tamil",   "hi": "Hindi",   "te": "Telugu",
    "kn": "Kannada", "ml": "Malayalam","bn": "Bengali",
    "mr": "Marathi", "gu": "Gujarati", "pa": "Punjabi",
    "or": "Odia",    "as": "Assamese","ur": "Urdu",
    "sa": "Sanskrit","en": "English"
}

class VoiceEngine:
    def __init__(self):
        self.model_size = os.getenv("WHISPER_MODEL_SIZE", "medium")
        self.tts_enabled = os.getenv("TTS_ENABLED", "true").lower() == "true"
        
        # MOCK INITIALIZATION
        # In a real environment, we would load faster-whisper and TTS here:
        # self.model = WhisperModel(self.model_size, device="cuda", compute_type="float16")
        # self.tts = TTS(os.getenv("TTS_MODEL"), gpu=True)
        
        log.info(f"VoiceEngine loaded. Whisper size: {self.model_size}, TTS Enabled: {self.tts_enabled}")

    def convert_audio(self, audio_bytes: bytes, source_format: str) -> bytes:
        """
        Convert any audio format to WAV 16kHz mono.
        Mocking pydub implementation to avoid ffmpeg requirement for tests.
        """
        log.info(f"Converting audio from {source_format} to wav 16kHz mono")
        # In a real environment:
        # audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=source_format)
        # audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        # buf = io.BytesIO()
        # audio.export(buf, format="wav")
        # return buf.getvalue()
        return audio_bytes # return mock bytes

    def transcribe(self, audio_bytes: bytes, format: str = "webm", hint_language: str = None) -> dict:
        """
        Convert voice audio to text in any Indian language.
        Mocking inference.
        """
        log.info(f"Transcribing audio bytes. Hint lang: {hint_language}")
        
        # In a real environment:
        # wav_bytes = self.convert_audio(audio_bytes, format)
        # Write wav_bytes to temp_path
        # segments, info = self.model.transcribe(temp_path, language=hint_language, beam_size=5, vad_filter=True)
        # text = " ".join([seg.text for seg in segments]).strip()
        
        # Return mock Tamil output for testing
        mock_text = "சென்னை மாவட்டத்தில் CMHIS திட்டத்தில் பயன் பெற தகுதி என்ன?"
        detected_language = "ta"
        language_probability = 0.98
        duration_sec = 4.5
        
        return {
            "success": True,
            "text": mock_text,
            "language": detected_language,
            "language_name": WHISPER_LANG_MAP.get(detected_language, "Unknown"),
            "language_probability": language_probability,
            "duration_sec": duration_sec,
            "word_count": len(mock_text.split()),
            "original_format": format
        }

    def text_to_speech(self, text: str, language: str, output_format: str = "mp3") -> bytes:
        """
        Convert text back to voice.
        Mocking inference.
        """
        if not self.tts_enabled:
            raise NotImplementedError("TTS is not enabled.")
            
        log.info(f"Generating TTS for {language} in {output_format}")
        
        # In a real environment:
        # voice = VOICE_MAP.get(language, "female_en")
        # with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        #     self.tts.tts_to_file(text=text[:2000], file_path=tmp.name, language=language, speaker=voice)
        #     wav_bytes = open(tmp.name, "rb").read()
        # Convert to mp3
        
        # Return a tiny valid mock byte string to prevent 500 errors
        return b"mock_mp3_audio_data"

    def transcribe_from_url(self, audio_url: str) -> dict:
        log.info(f"Downloading and transcribing from {audio_url}")
        return self.transcribe(b"mock", format="mp3")
