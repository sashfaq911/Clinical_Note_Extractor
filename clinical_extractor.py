from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException

from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model_name="llama-3.3-70b-versatile")


def extract_clinical_data(note_text: str):
    """
    Extract structured clinical information from a (de-identified) clinical note.
    Returns a JSON-like dict with keys:
    - patient_age (int or null)
    - patient_sex ("male" | "female" | "other" | null)
    - chief_complaint (str or null)
    - primary_diagnosis (str or null)
    - secondary_diagnoses (list[str])
    - medications (list[dict])
    - allergies (list[str])
    - tests_or_imaging (list[str])
    - follow_up_instructions (str or null)
    - return_precautions (str or null)
    """

    prompt = """
    You are a highly reliable medical scribe assistant.

    Clinical notes below are exported from common North American EMRs
    (such as Epic, Accuro, Cerner, Allscripts, OSCAR, MedAccess) and may
    use SOAP-style sections like:
    
    - Chief Complaint
    - History of Present Illness (HPI)
    - Review of Systems (ROS)
    - Past Medical History
    - Medications
    - Allergies
    - Assessment and Plan

    From the clinical note below, extract structured data as a single JSON object
    with exactly the following keys:

    - "patient_age": integer or null
    - "patient_sex": one of ["male", "female", "other", null]
    - "chief_complaint": string or null
    - "primary_diagnosis": string or null
    - "secondary_diagnoses": array of strings (can be empty)
    
    - "current_medications": array of objects for medications the patient is
          already taking (home meds, chronic meds). Each object must have:
        - "name": string
        - "dose": string or null (e.g. "500 mg")
        - "route": string or null (e.g. "oral", "IV")
        - "frequency": string or null (e.g. "once daily", "BID", "day 1, then 250 mg daily × 4 days")
        - "duration": string or null (e.g. "chronic", "as needed", "unknown")

    - "prescribed_medications": array of objects for medications started,
      changed, or explicitly prescribed as part of THIS VISIT's plan.
      Same structure as above:
        - "name": string
        - "dose": string or null
        - "route": string or null
        - "frequency": string or null
        - "duration": string or null (e.g. "7 days", "5 days", "short course")
    
    VERY IMPORTANT MEDICATION PARSING RULES:

    1. If the plan uses a complex regimen like:
       "Start Azithromycin 500 mg PO day 1, then 250 mg daily × 4 days"
    
       Then create a single medication object with:
       - "name": "Azithromycin"
       - "dose": "500 mg"
       - "route": "oral"
       - "frequency": "day 1, then 250 mg daily × 4 days"
       - "duration": "5 days"   (or the best explicit total duration you can infer)
    
    2. If the regimen does not clearly separate dose vs frequency vs duration,
       still try to:
       - put the NUMERIC + UNIT part into "dose" (e.g. "500 mg")
       - put the SCHEDULE text (e.g. "BID", "q6h", "once daily", or full phrases
         like "day 1, then 250 mg daily × 4 days") into "frequency"
       - put the COURSE LENGTH (e.g. "7 days", "10 days") into "duration" if
         explicitly stated.
    
    3. Do NOT leave "frequency" as null if any dosing schedule or pattern is
       described. If there is any text describing when/how often to take the
       medication, put that entire phrase into "frequency".
        
        - "allergies": array of strings (can be empty)
        - "tests_or_imaging": array of strings (e.g. "CBC", "Chest X-ray")
        - "follow_up_instructions": string or null
        - "return_precautions": string or null

    If a piece of information is not present, use null (for single values)
    or an empty array (for lists).

    Only return valid JSON. No preamble, no explanation.

    Clinical note
    =============
    {note}
    """

    pt = PromptTemplate.from_template(prompt)

    global llm
    chain = pt | llm
    response = chain.invoke({"note": note_text})

    parser = JsonOutputParser()

    try:
        res = parser.parse(response.content)
    except OutputParserException:
        raise OutputParserException("Content too big or malformed. Unable to parse clinical data.")

    return res
