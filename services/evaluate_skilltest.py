from typing import List, Dict, Any
from utils.database import skill_test_collection, freelancer_portfolio_collection, verified_skills
from utils.validator import validate_user_exists
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate

# --- AI GRADING SCHEMA ---
class PracticalGrade(BaseModel):
    score: int = Field(description="Score from 0 to 100 based on the rubric.")
    feedback: str = Field(description="Brief feedback on what was good or missing in the code/answer.")

async def grade_practical(practical_data: dict, user_answer: str, llm) -> dict:
    """Uses the LLM to grade the user's practical code submission out of 100."""
    
    if not user_answer or len(user_answer.strip()) < 5:
        return {"score": 0, "feedback": "No meaningful answer provided."}

    structured_llm = llm.with_structured_output(PracticalGrade)
    prompt = PromptTemplate.from_template("""
    You are an expert technical evaluator. Grade the user's practical response.
    
    Problem Statement: {problem}
    Expected Concept: {expected}
    Evaluation Rubric: {rubric}
    
    User's Answer:
    {answer}
    
    Provide a score from 0 to 100 and brief, constructive feedback.
    """)
    
    try:
        result = await structured_llm.ainvoke(prompt.format(
            problem=practical_data["problem_statement"],
            expected=practical_data["expected_solution_concept"],
            rubric=practical_data["evaluation_rubric"],
            answer=user_answer
        ))
        return {"score": result.score, "feedback": result.feedback}
    except Exception as e:
        print(f"Grading failed: {e}")
        return {"score": 50, "feedback": "Automatic fallback grade due to evaluation system error."}


async def evaluate_test(mcqs: List[Dict], practical: Dict, user_answers: Dict[str, str], llm) -> Dict[str, Any]:
    """
    Grades the MCQs (50% weight) and the Practical (50% weight).
    """
    analysis_report = []
    
    # 1. Grade MCQs (5 questions, worth 10 points each -> 50 points total)
    mcq_score = 0
    for index, q in enumerate(mcqs):
        q_id = f"mcq_{index}" # Matches the safe frontend payload
        user_choice = user_answers.get(q_id, "").upper()
        correct_choice = q["correct_answer"].upper()
        
        is_correct = (user_choice == correct_choice)
        if is_correct:
            mcq_score += 10 
            
        analysis_report.append({
            "type": "MCQ",
            "subtopic": q["subtopic"],
            "question": q["question_text"],
            "user_answer": user_choice,
            "correct_answer": correct_choice,
            "is_correct": is_correct,
            "explanation": q["explanation"]
        })
        
    # 2. Grade Practical Question (Scaled to 50 points total)
    prac_answer = user_answers.get("practical_1", "")
    prac_eval = await grade_practical(practical, prac_answer, llm)
    
    # Scale the 0-100 LLM score down to a maximum of 50 points
    prac_weighted_score = prac_eval["score"] * 0.50
    
    analysis_report.append({
        "type": "Practical",
        "problem": practical["problem_statement"],
        "user_answer": prac_answer,
        "score_out_of_100": prac_eval["score"],
        "feedback": prac_eval["feedback"]
    })

    # 3. Calculate Final Results
    total_score = mcq_score + prac_weighted_score
    passed = total_score >= 70.0
    
    return {
        "status": "Evaluated",
        "score": round(total_score, 2),
        "passed": passed,
        "analysis_report": analysis_report
    }


async def submit_test_for_evaluation(test_id: str, user_id: str, user_answers: Dict[str, str], llm) -> dict:
    """Fetches the secure test, grades it, updates DB, and issues Badges."""
    
    # 1. Fetch original test
    test_doc = await skill_test_collection.find_one({"test_id": test_id, "user_id": user_id})
    if not test_doc:
        raise ValueError("Test session not found.")
    if test_doc.get("status") == "Evaluated":
        raise ValueError("This test has already been submitted.")

    # 2. Run the full evaluation
    evaluation_result = await evaluate_test(
        test_doc["mcq_questions"], 
        test_doc["practical_question"], 
        user_answers, 
        llm
    )

    # 3. Mark the test as evaluated in the database (FIXED: changed delete_one to update_one)
    await skill_test_collection.update_one(
        {"test_id": test_id},
        {"$set": {
            "status": "Evaluated",
            "score": evaluation_result["score"],
            "passed": evaluation_result["passed"],
            "user_answers": user_answers
        }}
    )

    # 4. If passed, award the Verified Developer badge
    if evaluation_result["passed"]:
        badge_name = f"Verified {test_doc['skill']} Developer"
        evaluation_result["awarded_badge"] = badge_name
        
        # Add to the generic verified_skills tracking
        await verified_skills.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {
                    "verified_skills": {
                        "skill": test_doc["skill"],
                        "badge": badge_name,
                        "test_id": test_id
                    }
                }
            },
            upsert=True  
        )
        
        # Bonus: Add it directly to their portfolio so clients see it immediately!
        await freelancer_portfolio_collection.update_one(
            {"user_id": user_id},
            {"$addToSet": {"badges": badge_name}}
        )
    else:
        evaluation_result["awarded_badge"] = None
        evaluation_result["action_required"] = "Review feedback and retry later."

    return evaluation_result