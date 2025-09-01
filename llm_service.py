import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- Initialize Both AI Clients ---

# Configure and initialize the Google (Gemini) client
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')  # A fast and capable model


def parse_user_input(text, model_choice='gemini'):
    """
    Parses user input using the selected AI model.
    Defaults to Gemini.
    """
    return parse_user_input_with_gemini(text)

# --- Model Agnostic Wrapper Functions ---
# These are the main functions our bot will call.
# We can change the implementation here to switch models easily.

def generate_email_draft(name, offender_email):
    """
    Generates an email draft using the selected AI model.
    Defaults to OpenAI for its strong creative/formal writing.
    """
    return generate_email_with_gemini(name, offender_email)

# --- Google (Gemini) Implementations ---

def parse_user_input_with_gemini(text):
    """Uses Gemini to parse user input."""
    prompt = f"""
    Analyze the following text and extract the required information.
    Text: "{text}"

    Return a JSON object with the keys: 'name', 'offender_email', 'official_email'. If a value is missing, set it to null.
    """
    try:
        # Gemini needs the response schema instruction within the prompt for JSON output
        response = gemini_model.generate_content(prompt)
        # Clean up the response to extract the JSON part
        clean_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_response)
    except Exception as e:
        print(f"An error occurred with Gemini parsing: {e}")
        return None


def generate_email_with_gemini(name, offender_email):
    """Generates a formal email draft using Gemini."""
    prompt = _build_email_prompt(name, offender_email)
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred with Gemini generation: {e}")
        return "Error: Could not generate email draft."


# --- Helper Function ---
def _build_email_prompt(name, offender_email):
    """A helper to create the consistent email prompt for both models."""
    return f"""
    Please generate a highly formal and professional email to be sent to a Texas government official. The purpose of this email is to report an illegitimate catering business.

    The key points to include are:
    1. The business is being operated by a person named '{name}' (email: {offender_email}).
    2. This business is not registered with the state and is therefore operating illegally.
    3. This operation negatively impacts legitimate, tax-paying restaurant businesses in the area.
    4. It creates significant hazards in a residential zone, including potential fire hazards from improper cooking setups and food safety hazards from an unregulated kitchen.
    5. The state is losing tax revenue as this business is not paying taxes.

    The tone should be serious, direct, and to the point. Make it clear that we are requesting an investigation into this matter. Start the email with a formal salutation like "Dear Texas Government Official," and end it with "Sincerely,". Do not include a placeholder for the sender's name.
    """


# --- Test Block ---
if __name__ == '__main__':
    test_input = "Please file a report for name: Jane Doe, their email is jane.doe@illegalcatering.com, and send it to compliance@texas.gov"

    print("--- 1. Testing Input Parsing ---")

    print("\n[Using Gemini for Parsing...]")
    parsed_data_gemini = parse_user_input(test_input)
    print(parsed_data_gemini)

    print("\n--- 2. Testing Email Draft Generation ---")

    print("\n[Using Gemini for Email Draft...]")
    draft_gemini = generate_email_draft(parsed_data_gemini['name'], parsed_data_gemini['offender_email'])
    print(draft_gemini)