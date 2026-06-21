import json
import logging
import re
from .rag_engine import RAGEngine

logger = logging.getLogger("UPSCEngine")

class UPSCEngine:
    def __init__(self, rag_engine=None):
        logger.info("Initializing UPSCEngine...")
        self.rag_engine = rag_engine or RAGEngine()

    def generate_mcq_quiz(self, topic: str, num_questions: int = 10) -> list:
        """
        Generates a set of UPSC-style MCQs based on the given topic.
        """
        logger.info(f"Generating {num_questions} MCQs for topic: {topic}")
        
        # 1. Retrieve context for the topic
        chunks = self.rag_engine.retrieve(topic, department="Unknown", top_k=5)
        
        # Construct context string
        context_parts = []
        for chunk in chunks:
            context_parts.append(chunk["payload"].get("text", ""))
        context = "\n---\n".join(context_parts)
        
        if not context.strip():
            context = "No specific context found. Use general knowledge regarding Indian Polity, Economy, History, Geography, and Current Affairs."
            
        # 2. Build the specialized prompt
        system_prompt = (
            "You are an expert UPSC Civil Services Examination setter. "
            "Your task is to generate high-quality Multiple Choice Questions (MCQs) for the Preliminary Examination. "
            "Questions should be conceptual, statement-based (e.g., 'Consider the following statements...'), and challenging. "
            "Always return the output in pure JSON format as a list of objects. Do not include any markdown formatting like ```json. "
            "Each object must have exactly these keys: 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option' (A/B/C/D), 'explanation'."
        )
        
        user_prompt = f"Topic: {topic}\nNumber of questions to generate: {num_questions}\n\nContext to base questions on (if applicable):\n{context}"
        
        if not self.rag_engine.model:
            # DEV MODE mock response
            return [
                {
                    "question_text": f"[DEV MODE] Sample question about {topic}?",
                    "option_a": "Statement 1 is correct",
                    "option_b": "Statement 2 is correct",
                    "option_c": "Both 1 and 2 are correct",
                    "option_d": "Neither 1 nor 2",
                    "correct_option": "C",
                    "explanation": "This is a mocked explanation."
                }
            ]
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            prompt = self.rag_engine.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.rag_engine.tokenizer(prompt, return_tensors="pt").to(self.rag_engine.model.device)
            
            outputs = self.rag_engine.model.generate(
                **inputs,
                temperature=0.3,
                do_sample=True,
                max_new_tokens=2048,
                pad_token_id=self.rag_engine.tokenizer.eos_token_id
            )
            
            input_len = inputs.input_ids.shape[1]
            response_text = self.rag_engine.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
            
            # 3. Parse JSON
            # Try to extract JSON if the model wrapped it in markdown
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
                
            questions = json.loads(response_text)
            
            # Validate output structure
            valid_questions = []
            for q in questions:
                if all(k in q for k in ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation"]):
                    valid_questions.append(q)
                    
            return valid_questions[:num_questions]
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}\nRaw Output: {response_text}")
            raise ValueError("LLM failed to return valid JSON.")
        except Exception as e:
            logger.error(f"LLM Generation call failed: {e}")
            raise RuntimeError(f"Error generating MCQs: {e}")
