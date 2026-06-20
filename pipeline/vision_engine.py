import os
import io
import base64
import logging
from PIL import Image

log = logging.getLogger("VisionEngine")

class VisionEngine:
    def __init__(self):
        self.engine_type = os.getenv("VISION_ENGINE", "llava_local")
        self.detect_type = os.getenv("VISION_DETECT_TYPE", "true").lower() == "true"
        
        # MOCK INITIALIZATION
        # In a real environment, we load LLaVA or GPT-4o here:
        # if self.engine_type == "llava_local":
        #     self.llava = Llama(model_path=os.getenv("LLAVA_MODEL_PATH"), chat_handler=clip_handler)
        
        log.info(f"VisionEngine loaded. Engine: {self.engine_type}, Auto-detect: {self.detect_type}")

    def detect_image_type(self, image: Image) -> str:
        """
        Detect whether the image is a document, chart, form, handwritten, mixed, or photo.
        Mocking logic for tests.
        """
        # In real logic, convert to grayscale, check unique gray values, lines, etc.
        return "document"

    def preprocess_image(self, image_bytes: bytes) -> Image:
        """Load and resize image from bytes."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image = image.convert("RGB")
            return image
        except Exception as e:
            raise ValueError(f"Invalid image format: {e}")

    def extract_text_from_document(self, image: Image) -> dict:
        """
        Extract text using Tesseract.
        Mocking inference.
        """
        log.info("Extracting text using OCR")
        # In a real environment:
        # data = pytesseract.image_to_data(image, lang="tam+eng", config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT)
        
        mock_text = "TAMIL NADU GOVERNMENT GAZETTE\nGOVERNMENT ORDER NO. 45\nEligible beneficiaries for CMHIS..."
        
        return {
            "text": mock_text,
            "avg_confidence": 92.5,
            "scripts_detected": {"Latin": 0.8, "Tamil": 0.2},
            "word_count": len(mock_text.split()),
            "method": "tesseract"
        }

    def understand_image(self, image: Image, question: str, language: str = "en") -> dict:
        """
        Understand charts, forms, tables using LLaVA or GPT4o.
        Mocking inference.
        """
        log.info(f"Understanding image via {self.engine_type} for question: {question}")
        
        mock_answer = "Based on the image provided, the bar chart shows a 25% increase in beneficiary enrollment for the month of August compared to July."
        
        return {
            "answer": mock_answer,
            "method": self.engine_type,
            "question_asked": question,
            "image_type": "chart"
        }

    def process_image_query(self, image_bytes: bytes, question: str, org_unit: str, state_code: str, router_instance=None) -> dict:
        """
        Full pipeline: Image -> OCR/LLaVA -> RAG (if needed) -> Answer
        """
        image = self.preprocess_image(image_bytes)
        img_type = self.detect_image_type(image) if self.detect_type else "mixed"
        
        log.info(f"Detected image type: {img_type}")
        
        extracted_text = ""
        image_analysis = ""
        combined_question = question
        
        if img_type == "document":
            ocr_res = self.extract_text_from_document(image)
            extracted_text = ocr_res["text"]
            combined_question = f"User question: {question}\n\nDocument text provided by user:\n{extracted_text}"
            method = "ocr+rag"
            scripts = ocr_res["scripts_detected"]
        else:
            vision_res = self.understand_image(image, question)
            image_analysis = vision_res["answer"]
            combined_question = f"The user uploaded an image. Image contains:\n{image_analysis}\n\nUser question: {question}"
            method = f"{self.engine_type}+rag"
            scripts = {}

        # MOCK RAG ENGINE QUERY
        rag_answer = f"According to the {org_unit} guidelines and the provided image text, the requirements are met."
        
        return {
            "answer": rag_answer,
            "extracted_text": extracted_text,
            "image_analysis": image_analysis,
            "image_type": img_type,
            "method": method,
            "scripts_detected": scripts,
            "sources": [{"type": "IMAGE", "title": "User Uploaded Image"}],
            "confidence": 0.89
        }
