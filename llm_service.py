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
    """Uses Gemini to parse user input."""
    # *** KEY CHANGE: Updated prompt to look for an 'email_gist' ***
    prompt = f"""
    Analyze the following text and extract the required information.
    Text: "{text}"

    Return a JSON object with the keys: 'name', 'offender_email', 'official_email', and 'email_gist'.
    The 'email_gist' should contain any specific details the user wants to include in the email body.
    If a value is missing, set it to null.
    """
    try:
        response = gemini_model.generate_content(prompt)
        clean_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_response)
    except Exception as e:
        print(f"An error occurred with Gemini parsing: {e}")
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


# --- Helper Function ---

def _build_email_prompt(name, offender_email, gist=None):  # <-- Add gist parameter
    """A helper to create the consistent email prompt for both models."""

    # *** KEY CHANGE: Conditionally add the user's gist to the prompt ***
    gist_section = ""
    if gist:
        gist_section = f"""
        In addition to the standard points, it is crucial to professionally integrate the following user-provided details into the body of the email:
        ---
        {gist}
        ---
        """

    return f"""
    Please generate a highly formal and professional email to be sent to a Texas government official. The purpose of this email is to report an illegitimate catering business.

    The key points to include are:
    1. The business is being operated by a person named '{name}' (email: {offender_email}).
    2. This business is not registered with the state and is therefore operating illegally.
    3. This operation negatively impacts legitimate, tax-paying restaurant businesses in the area.
    4. It creates significant hazards in a residential zone, including potential fire hazards and food safety hazards.
    5. The state is losing tax revenue as this business is not paying taxes.
    {gist_section}
    The tone should be serious, direct, and to the point. Make it clear that we are requesting an investigation. Start with a formal salutation like "Dear Texas Government Official," and end it with "Sincerely,". Do not include a placeholder for the sender's name.
    """


# ... (The rest of the file, including the wrapper functions, can stay the same) ...
# Update the wrapper function to accept the new argument
def generate_email_draft(name, offender_email, gist=None):
    return generate_email_with_gemini(name, offender_email, gist)


# --- Test Block ---
if __name__ == '__main__':
    test_input_with_gist = "please file report for john pape their email is john.pape@gmail.com, send it to vedantdesai07@gmail.com. email should say, john pape restaurant is located at 123 indian street in huston, you can go to their website to see that you can order things there for catering but they don't have legit business"

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