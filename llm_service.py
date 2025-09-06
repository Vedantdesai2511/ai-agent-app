import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure and initialize the Google (Gemini) client
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')


# --- Main Functions ---

def parse_user_input_with_gemini(text):
    """
    Uses Gemini to parse user input, now prioritizing phone_number over email.
    """
    prompt = f"""
    You are an expert at parsing user requests into structured JSON. Analyze the user's text and extract the required information.
    The user can provide any number of details about the offender. You must capture all of them in a nested JSON object called "offender_details".

    ---
    **Example 1 (Simple case):**
    **User text:** "report name John Doe, phone 555-123-4567, target officials@texas.gov"
    **Your JSON output:**
    ```json
    {{
      "name": "John Doe",
      "offender_phone_number": "555-123-4567",
      "official_email": "officials@texas.gov",
      "offender_details": {{}}
    }}
    ```

    **Example 2 (Complex case with multiple details):**
    **User text:** "please file report for john pape their phone is 832-555-1234, send it to vedantdesai07@gmail.com. His address is 123 Texas Rd, Houston, TX 77001. He sells veg catering."
    **Your JSON output:**
    ```json
    {{
      "name": "John Pape",
      "offender_phone_number": "832-555-1234",
      "official_email": "vedantdesai07@gmail.com",
      "offender_details": {{
        "Address": "123 Texas Rd, Houston, TX 77001",
        "Notes": "He sells veg catering."
      }}
    }}
    ```
    ---
    **Actual User Request:**
    **User text:** "{text}"
    **Your JSON output:**
    """
    try:
        response = gemini_model.generate_content(prompt)
        response_text = response.text
        start_index = response_text.find('{')
        end_index = response_text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_string = response_text[start_index: end_index + 1]
            return json.loads(json_string)
        else:
            raise ValueError("Could not find a valid JSON object in the model's response.")
    except Exception as e:
        print(f"An error occurred with Gemini parsing: {e}")
        print(f"Failed to parse response: {response.text if 'response' in locals() else 'No response text available'}")
        return None


def generate_email_with_gemini(name, offender_phone_number, gist=None): # <-- Add gist parameter
    """Generates a formal email draft using Gemini."""
    prompt = _build_email_prompt(name, offender_phone_number, gist) # <-- Pass gist to helper
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred with Gemini generation: {e}")
        return "Error: Could not generate email draft."


def generate_follow_up_email(name, offender_phone_number, offender_details=None):
    """
    Generates the BODY of a follow-up email.
    Returns a single string.
    """
    prompt = _build_follow_up_prompt(name, offender_phone_number, offender_details)

    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"An error occurred with Gemini follow-up generation: {e}")
        return "Error: Could not generate follow-up email draft."


# --- Helper Functions ---


def _build_email_prompt(name, offender_phone_number, offender_details=None):
    """A helper to create the prompt for the email body, using phone_number."""
    details_section = ""
    if offender_details:
        details_section += "\nAdditional user-provided details about the operation are as follows:\n"
        for key, value in offender_details.items():
            details_section += f"- {key}: {value}\n"

    return f"""
    Generate the body for a highly formal and professional email to a Texas government official to report an illegitimate catering business.

    Key points for the body:
    1. The business is operated by '{name}' (phone: {offender_phone_number}).
    2. It is not registered with the state (operating illegally).
    3. It negatively impacts legitimate, tax-paying businesses.
    4. It creates fire and food safety hazards in a residential zone.
    5. The state is losing tax revenue.
    {details_section} The tone should be serious and direct. Start the body with a formal salutation like "Dear Texas 
    Government Official," and end it with "Sincerely,". Do not include a subject line."""


def _build_follow_up_prompt(name, offender_phone_number, offender_details=None):
    """A helper to create the prompt for the follow-up email body, using phone_number."""
    details_section = ""
    if offender_details:
        details_section += "\nThe original report included these details:\n"
        for key, value in offender_details.items():
            details_section += f"- {key}: {value}\n"

    return f"""
    Generate the body for a polite but firm follow-up email to a Texas government official about a previously reported illegitimate catering business.

    Key details of the original report:
    - Business operated by: {name} (phone: {offender_phone_number})
    {details_section}
    The follow-up body should:
    1. Reference the previous email.
    2. Briefly reiterate the key concerns (unregistered business, safety hazards, tax evasion).
    3. Politely inquire about the status of the investigation.
    4. Maintain a professional tone. Do not include a subject line.
    """


# Update the wrapper function to accept the new argument
def generate_email_draft(name, offender_phone_number, offender_details=None):
    """Generates a formal email draft using Gemini, now with a details dictionary."""
    prompt = _build_email_prompt(name, offender_phone_number, offender_details)
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred with Gemini generation: {e}")
        return "Error: Could not generate email draft."


# --- Test Block ---
if __name__ == '__main__':
    test_input_with_gist = ("please file report for john pape their email is john.pape@gmail.com, send it to "
                            "vedantdesai07@gmail.com. email should say, john pape restaurant is located at 123 indian "
                            "street in huston, you can go to their website to see that you can order things there for "
                            "catering but they don't have legit business")

    print("--- 1. Testing Input Parsing with Gist ---")
    parsed_data = parse_user_input_with_gemini(test_input_with_gist)
    print(json.dumps(parsed_data, indent=2))
    assert 'email_gist' in parsed_data

    print("\n--- 2. Testing Email Generation with Gist ---")
    if parsed_data:
        draft = generate_email_draft(
            parsed_data['name'],
            parsed_data['offender_email'],
            parsed_data['email_gist']
        )
        print(draft)
