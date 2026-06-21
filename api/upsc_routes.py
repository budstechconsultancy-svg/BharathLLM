from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user, get_db
from api.db_models import MCQQuiz, MCQQuestion, MCQAttempt
import logging
from pipeline.upsc_engine import UPSCEngine

logger = logging.getLogger("UPSCRoutes")
router = APIRouter(prefix="/upsc", tags=["UPSC"])

class QuizGenerateRequest(BaseModel):
    topic: str
    num_questions: Optional[int] = 10

class QuizAnswerSubmission(BaseModel):
    question_id: str
    selected_option: str # A, B, C, D

class QuizSubmitRequest(BaseModel):
    answers: List[QuizAnswerSubmission]

@router.post("/quiz/generate")
def generate_quiz(req: QuizGenerateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Generate a new UPSC Prelims quiz on a specific topic."""
    from api.main import router_instance
    if not router_instance:
        raise HTTPException(status_code=503, detail="Document Intelligence Router offline.")
        
    upsc_engine = UPSCEngine(rag_engine=router_instance.rag_engine)
    
    try:
        mcqs = upsc_engine.generate_mcq_quiz(req.topic, req.num_questions)
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate quiz. Try again.")
        
    if not mcqs:
        raise HTTPException(status_code=400, detail="Could not generate valid questions.")
        
    # Save to Database
    quiz = MCQQuiz(topic=req.topic, num_questions=len(mcqs))
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    
    saved_questions = []
    for q in mcqs:
        question = MCQQuestion(
            quiz_id=quiz.id,
            question_text=q["question_text"],
            option_a=q["option_a"],
            option_b=q["option_b"],
            option_c=q["option_c"],
            option_d=q["option_d"],
            correct_option=q["correct_option"],
            explanation=q["explanation"]
        )
        db.add(question)
        saved_questions.append(question)
        
    db.commit()
    
    return {
        "message": "Quiz generated successfully",
        "quiz_id": str(quiz.id),
        "topic": quiz.topic,
        "num_questions": quiz.num_questions
    }

@router.get("/quiz/{quiz_id}")
def get_quiz(quiz_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Fetch quiz questions without answers for taking the test."""
    quiz = db.query(MCQQuiz).filter(MCQQuiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")
        
    questions = db.query(MCQQuestion).filter(MCQQuestion.quiz_id == quiz_id).all()
    
    # Return questions without the correct_option and explanation
    qs = []
    for q in questions:
        qs.append({
            "id": str(q.id),
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d
        })
        
    return {
        "quiz_id": str(quiz.id),
        "topic": quiz.topic,
        "questions": qs
    }

@router.post("/quiz/{quiz_id}/submit")
def submit_quiz(quiz_id: str, req: QuizSubmitRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Evaluate quiz answers with UPSC negative marking (+2, -0.66)."""
    quiz = db.query(MCQQuiz).filter(MCQQuiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")
        
    questions = db.query(MCQQuestion).filter(MCQQuestion.quiz_id == quiz_id).all()
    q_map = {str(q.id): q for q in questions}
    
    correct_count = 0
    incorrect_count = 0
    unattempted_count = len(questions) - len(req.answers)
    
    results = []
    for ans in req.answers:
        q = q_map.get(ans.question_id)
        if not q:
            continue
            
        is_correct = ans.selected_option.upper() == q.correct_option.upper()
        if is_correct:
            correct_count += 1
        else:
            incorrect_count += 1
            
        results.append({
            "question_id": str(q.id),
            "is_correct": is_correct,
            "selected_option": ans.selected_option.upper(),
            "correct_option": q.correct_option,
            "explanation": q.explanation
        })
        
    # Calculate UPSC Score: +2 for correct, -0.66 for incorrect
    score = (correct_count * 2.0) - (incorrect_count * 0.6667)
    score = max(score, 0.0) # Floor at 0, though UPSC can technically be negative
    score = round(score, 2)
    
    attempt = MCQAttempt(
        quiz_id=quiz.id,
        user_id=user.get("user_id"),
        score=score,
        total_questions=len(questions)
    )
    db.add(attempt)
    db.commit()
    
    return {
        "score": score,
        "correct": correct_count,
        "incorrect": incorrect_count,
        "unattempted": unattempted_count,
        "detailed_results": results
    }
