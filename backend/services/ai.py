import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from the .env file in the root/backend directory
load_dotenv()

api_key = os.environ.get("BEDROCK_API_KEY") or os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("BEDROCK_BASE_URL") or os.environ.get("OPENAI_BASE_URL")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

def analyze_cv(cv_text: str, job_description: str) -> dict:
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) and HR recruiter.
    I will provide you with a candidate's CV and a Job Description.
    Analyze the CV against the Job Description. Provide a suitability score out of 100, and a list of improvements that could be made to the cv to better fit the job.
    Return ONLY a valid JSON object with exactly these two keys:
    "score": <integer from 0 to 100 taking into account factors: if the candidate has the relevant technical skills, years of experience, related personal projects, related education, relevant achievements>,
    "improvements": "<String of the improvements in a bulleted list format, ensure to tailor towards the information on the CV, do not include fake experiences, instead suggest personal projects/workshops/certs to obtain this experience>"
    
    Job Description:
    {job_description}
    
    CV:
    {cv_text}
    """
    try:
        response = client.chat.completions.create(
            model="openai.gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}]
        )
        # Parse the JSON response
        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:-3]
        elif result_text.startswith("```"):
            result_text = result_text[3:-3]
        return json.loads(result_text)
    except Exception as e:
        print(f"Error in analyze_cv: {e}")
        return {"score": 0, "improvements": "Error analyzing CV. Check API key or try again later."}

def generate_cover_letter(cv_text: str, job_description: str) -> str:
    prompt = f"""
    You are an expert career coach and copywriter.
    Write a professional and personalized cover letter based on the following candidate's CV and Job Description.
    Do not include placeholder text like [Your Name] if it can be found in the CV, but if it can't, use placeholders.
    Return ONLY the string of the cover letter.
    
    Job Description:
    {job_description}
    
    CV:
    {cv_text}
    """
    try:
        response = client.chat.completions.create(
            model="openai.gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in generate_cover_letter: {e}")
        return "Error generating cover letter. Check API key or try again later."

def apply_cv_improvements(cv_text: str, improvements: str, job_description: str) -> str:
    prompt = f"""
    You are an expert ATS resume writer and career specialist.
    I will provide a candidate's base CV, a Job Description, and recommended improvements.
    Rewrite the candidate's CV incorporating these improvements cleanly while adhering STRICTLY to the following constraints:

    CRITICAL CONSTRAINTS:
    1. STRICT 1-PAGE LIMIT: Keep the entire generated CV concise so it fits on exactly 1 single page (maximum 350-400 words total). Do not create overly long bullet points or unnecessary padding.
    2. PRESERVE FORMATTING & STRUCTURE: Retain the original markdown layout, section titles (e.g. ## Contact, ## Experience, ## Education, ## Skills), bullet point structure, and text styling.
    3. NO INVENTED EXPERIENCE: Keep all true details (real work history, education, contact info) accurate. Optimize phrasing and add relevant keywords naturally.

    Return ONLY the full text of the revised 1-page CV. Do not include markdown code block markers (```) or conversational intro/outro text.

    Base CV:
    {cv_text}

    Job Description:
    {job_description}

    Suggested Improvements:
    {improvements}
    """
    try:
        response = client.chat.completions.create(
            model="openai.gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        return content
    except Exception as e:
        print(f"Error in apply_cv_improvements: {e}")
        return cv_text

