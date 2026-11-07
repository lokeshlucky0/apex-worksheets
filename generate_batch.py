import os
import json
import asyncio
from datetime import datetime
import markdown
from jinja2 import Template
from weasyprint import HTML
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Anchor date used to track the repeating 14-day cycle
ANCHOR_DATE = datetime(2026, 1, 1)

def get_current_cycle_day():
    delta_days = (datetime.utcnow() - ANCHOR_DATE).days
    return str(delta_days % 14)

async def generate_subject_content(grade: str, subject: str) -> str:
    prompt = f"""
    You are an expert school educator.
    Create a 1-page printable daily practice worksheet for:
    Grade: {grade}
    Subject: {subject}
    Curriculum: CBSE / State Board aligned

    STRICT RULES:
    1. Do NOT include any answer key, solutions, or explanations.
    2. Format questions in clean Markdown.
    3. Include:
       - Section A: Conceptual Recall / Fill-in / Objective (5 Questions)
       - Section B: Short Practice / Working Problems (4 Questions)
       - Section C: Application / Critical Thinking (2 Questions)
    4. Provide adequate spacing and question clarity for solving on paper.
    5. Output ONLY the questions in markdown format. No introductory or closing remarks.
    """
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
    )
    return response.text

async def build_worksheet_pdf(grade: str, subject: str, template: Template, output_dir: str):
    print(f"Generating: {grade} - {subject}...")
    try:
        md_text = await generate_subject_content(grade, subject)
        html_inner = markdown.markdown(md_text, extensions=['extra', 'tables'])
        
        rendered_html = template.render(
            grade=grade,
            subject=subject,
            html_content=html_inner
        )
        
        safe_subject = subject.replace(" ", "_").replace("&", "and").lower()
        safe_grade = grade.replace(" ", "_").lower()
        pdf_path = os.path.join(output_dir, f"{safe_grade}_{safe_subject}.pdf")
        
        HTML(string=rendered_html).write_pdf(pdf_path)
        print(f"Compiled PDF: {pdf_path}")
    except Exception as e:
        print(f"Error compiling {grade} {subject}: {e}")

async def main():
    with open("data/rotation_schedule.json", "r", encoding="utf-8") as f:
        schedule = json.load(f)
        
    cycle_day = get_current_cycle_day()
    day_plan = schedule.get(cycle_day)
    grade = day_plan["grade"]
    subjects = day_plan["subjects"]
    
    date_stamp = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = os.path.join("output", date_stamp, grade.replace(" ", "_").lower())
    os.makedirs(out_dir, exist_ok=True)
    
    with open("templates/worksheet_template.html", "r", encoding="utf-8") as f:
        template = Template(f.read())
        
    print(f"Starting Day {int(cycle_day) + 1} Batch | Grade: {grade} | Subjects: {len(subjects)}")
    
    tasks = [build_worksheet_pdf(grade, sub, template, out_dir) for sub in subjects]
    await asyncio.gather(*tasks)
    print("Batch complete!")

if __name__ == "__main__":
    asyncio.run(main())
