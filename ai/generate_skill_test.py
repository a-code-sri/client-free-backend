import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from ai.taxonomy import HARDCODED_SKILL_TAXONOMY
import uuid
import random
from datetime import datetime, timezone
from utils.database import skill_test_collection

search_tool = DuckDuckGoSearchRun()

class MCQQuestion(BaseModel):
    subtopic: str = Field(description="The specific subtopic being tested.")
    question_text: str = Field(description="The technical multiple-choice question.")
    option_a: str = Field(description="Option A text")
    option_b: str = Field(description="Option B text")
    option_c: str = Field(description="Option C text")
    option_d: str = Field(description="Option D text")
    correct_answer: str = Field(description="Must be exactly 'A', 'B', 'C', or 'D'.")
    explanation: str = Field(description="Brief explanation of why the answer is correct for the analysis report.")

class PracticalQuestion(BaseModel):
    problem_statement: str = Field(description="A short, real-world practical scenario or coding problem for the skill.")
    expected_solution_concept: str = Field(description="What the ideal text/code answer should look like.")
    evaluation_rubric: str = Field(description="Instructions for how the grading AI should score this out of 100.")

async def generate_single_question(skill: str, subtopic: str, structured_llm) -> MCQQuestion:
    """Fetches real-world context for a subtopic and generates a structured MCQ."""
    try:
        search_query = f"{skill} {subtopic} best practices documentation"
        context = search_tool.invoke(search_query)
        
        prompt_template = PromptTemplate.from_template("""
        You are an expert technical interviewer assessing a senior developer.
        Generate a highly technical multiple-choice question for the skill: {skill}.
        Specific subtopic: {subtopic}.
        
        Use this recent web context to make the question realistic and modern:
        {context}
        
        The question should test deep understanding, not just basic definitions.
        """)
        
        return await structured_llm.ainvoke(prompt_template.format(
            skill=skill, 
            subtopic=subtopic, 
            context=context[:1500]
        ))
    except Exception as e:
        print(f"Failed generating MCQ for {subtopic}: {e}")
        return MCQQuestion(
            subtopic=subtopic,
            question_text=f"What is the primary function of {subtopic} in {skill}?",
            option_a="Configuration", option_b="Optimization", 
            option_c="Execution", option_d="Logging",
            correct_answer="B", explanation="General fallback execution due to generation error."
        )

async def generate_practical_question(skill: str, structured_llm) -> PracticalQuestion:
    """Generates a single, text-based practical scenario for the user to solve."""
    try:
        prompt_template = PromptTemplate.from_template("""
        You are a lead engineer creating a technical assessment for {skill}.
        Create a short, practical problem statement where the candidate must write a brief code snippet 
        or architectural explanation to solve a specific, real-world issue in {skill}.
        
        It should take them about 5 minutes to write out their answer.
        Provide the problem statement, the expected conceptual solution, and a brief grading rubric.
        """)
        
        return await structured_llm.ainvoke(prompt_template.format(skill=skill))
    except Exception as e:
        print(f"Failed generating practical question for {skill}: {e}")
        return PracticalQuestion(
            problem_statement=f"Write a brief explanation or pseudo-code demonstrating a core feature of {skill}.",
            expected_solution_concept="A valid, logical demonstration of the skill's syntax or architecture.",
            evaluation_rubric="Award full points if the logic is fundamentally sound."
        )

async def generate_and_save_skill_test(user_id: str, skill: str, llm) -> dict:
    """Generates a short test (5 MCQs + 1 Practical), saves securely to DB, and returns a safe frontend version."""
    
    if skill not in HARDCODED_SKILL_TAXONOMY:
        raise ValueError(f"Skill taxonomy not found for: {skill}")
    
    mcq_llm = llm.with_structured_output(MCQQuestion)
    practical_llm = llm.with_structured_output(PracticalQuestion)
    
    # 1. Select 5 subtopics for a "short" test
    available_subtopics = HARDCODED_SKILL_TAXONOMY[skill]
    sample_size = min(5, len(available_subtopics))
    selected_subtopics = random.sample(available_subtopics, sample_size)
    
    # 2. Generate MCQs and the Practical Question concurrently
    mcq_tasks = [generate_single_question(skill, subtopic, mcq_llm) for subtopic in selected_subtopics]
    
    # Gather MCQs and Practical Question
    results = await asyncio.gather(
        *mcq_tasks, 
        generate_practical_question(skill, practical_llm)
    )
    
    mcq_results = results[:-1] # Everything except the last item
    practical_result = results[-1] # The last item
    
    test_id = f"test_{uuid.uuid4().hex[:8]}"
    
    # 3. Store the FULL data securely in MongoDB
    full_mcqs_dict = [q.model_dump() for q in mcq_results]
    practical_dict = practical_result.model_dump()
    
    test_doc = {
        "test_id": test_id,
        "user_id": user_id,
        "skill": skill,
        "mcq_questions": full_mcqs_dict,
        "practical_question": practical_dict,
        "status": "Pending",
        "created_at": datetime.now(timezone.utc)
    }
    await skill_test_collection.insert_one(test_doc)
    
    # 4. Prepare the SAFE payload for the frontend (hiding answers and rubrics)
    safe_mcqs = []
    for index, q in enumerate(full_mcqs_dict):
        safe_mcqs.append({
            "question_id": f"mcq_{index}",
            "subtopic": q["subtopic"],
            "question_text": q["question_text"],
            "options": {
                "A": q["option_a"],
                "B": q["option_b"],
                "C": q["option_c"],
                "D": q["option_d"]
            }
        })
        
    safe_practical = {
        "question_id": "practical_1",
        "problem_statement": practical_dict["problem_statement"]
    }
        
    return {
        "test_id": test_id,
        "skill": skill,
        "mcq_questions": safe_mcqs,
        "practical_question": safe_practical
    }