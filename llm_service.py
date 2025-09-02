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
    Uses Gemini to parse user input into structured JSON, including a flexible details dictionary.
    """
    prompt = f"""
    You are an expert at parsing user requests into structured JSON. Analyze the user's text and extract the required information.
    The user can provide any number of details about the offender. You must capture all of them in a nested JSON object called "offender_details".

    ---
    **Example 1 (Simple case):**
    **User text:** "report name John Doe, email john.doe@example.com, target officials@texas.gov"
    **Your JSON output:**
    ```json
    {{
      "name": "John Doe",
      "offender_email": "john.doe@example.com",
      "official_email": "officials@texas.gov",
      "offender_details": {{}}
    }}
    ```

    **Example 2 (Complex case with multiple details):**
    **User text:** "please file report for john pape their email is john.pape@gmail.com, send it to vedantdesai07@gmail.com. His address is 123 Texas Rd, Houston, TX 77001 and phone is 832-555-1234. He sells veg catering to Indians nearby, it works by word of mouth."
    **Your JSON output:**
    ```json
    {{
      "name": "John Pape",
      "offender_email": "john.pape@gmail.com",
      "official_email": "vedantdesai07@gmail.com",
      "offender_details": {{
        "Address": "123 Texas Rd, Houston, TX 77001",
        "Phone Number": "832-555-1234",
        "Notes": "He sells veg catering to Indians nearby, it works by word of mouth."
      }}
    }}
    ```
    ---
    **Actual User Request:**
    **User text:** "{text}"
    **Your JSON output:**
    """
    try:
        # ... (The Gemini call and JSON extraction logic remains the same) ...
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


def generate_email_with_gemini(name, offender_email, gist=None): # <-- Add gist parameter
    """Generates a formal email draft using Gemini."""
    prompt = _build_email_prompt(name, offender_email, gist) # <-- Pass gist to helper
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred with Gemini generation: {e}")
        return "Error: Could not generate email draft."


def generate_follow_up_email(name, offender_email, original_draft):
    """Generates a follow-up email."""
    prompt = f""" Please generate a polite but firm follow-up email. The original email was sent to a Texas 
    government official to report an illegitimate catering business.

    The key details of the original report are:
    - Business operated by: {name} ({offender_email})
    - The original email is provided below for context.

    The follow-up email should:
    1.  Reference the previous email about this issue.
    2.  Briefly reiterate the key concerns (unregistered business, safety hazards, tax evasion).
    3.  Inquire about the status of the investigation.
    4.  Maintain a professional and respectful tone.
    5.  Start with "Dear Texas Government Official," and end with "Sincerely,".

    --- ORIGINAL EMAIL CONTEXT ---
    {original_draft}
    ---
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred with Gemini follow-up generation: {e}")
        return "Error: Could not generate follow-up email draft."

# --- Helper Function ---


def _build_email_prompt(name, offender_email, offender_details=None):
    """A helper to create the email prompt, now with a dynamic details section."""

    details_section = ""
    if offender_details:
        # Start the section with a clear header
        details_section += "\nAdditional user-provided details about the operation are as follows:\n"
        # Loop through the dictionary and format each key-value pair
        for key, value in offender_details.items():
            details_section += f"- {key}: {value}\n"

    return f"""
    Please generate a highly formal and professional email to be sent to a Texas government official. The purpose of this email is to report an illegitimate catering business.

    The key points to include are:
    1. The business is being operated by a person named '{name}' (email: {offender_email}).
    2. This business is not registered with the state and is therefore operating illegally.
    3. This operation negatively impacts legitimate, tax-paying restaurant businesses in the area.
    4. It creates significant hazards in a residential zone, including potential fire hazards and food safety hazards.
    5. The state is losing tax revenue as this business is not paying taxes.
    {details_section}
    The tone should be serious, direct, and to the point. Make it clear that we are requesting an investigation. Start with a formal salutation like "Dear Texas Government Official," and end it with "Sincerely,". Do not include a placeholder for the sender's name.
    """


# ... (The rest of the file, including the wrapper functions, can stay the same) ...
# Update the wrapper function to accept the new argument
def generate_email_draft(name, offender_email, offender_details=None):
    """Generates a formal email draft using Gemini, now with a details dictionary."""
    prompt = _build_email_prompt(name, offender_email, offender_details)
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
