import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")


def send_email(recipient_email, subject, body, report_id=None, thread_message_id=None):
    """
    Sends an email using credentials from the .env file.

    Args:
        recipient_email (str): The email address of the recipient.
        subject (str): The subject line of the email.
        body (str): The main content of the email.
        report_id (int, optional): The report ID to include in the subject. Defaults to None.
        thread_message_id (str, optional): The Message-ID of the original email to create a thread.

    Returns:
        A tuple of (bool: success, str: message_id)
    """
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        print("Error: Sender email or app password not configured in .env file.")
        return False, None

    # Create the email message object
    msg = EmailMessage()

    # Add the report ID to the subject if provided
    final_subject = f"{subject} [Report ID: {report_id}]" if report_id else subject
    msg['Subject'] = final_subject

    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg.set_content(body)

    # --- THREADING LOGIC ---
    # Generate a new unique Message-ID for this email
    msg_id = make_msgid()
    msg['Message-ID'] = msg_id

    # If this is a follow-up, link it to the original email
    if thread_message_id:
        msg['In-Reply-To'] = thread_message_id
        msg['References'] = thread_message_id
        # For follow-ups, it's common to prefix the subject with "Re:"
        msg.replace_header('Subject', f"Re: {final_subject}")

    try:
        # Connect to the SMTP server (using Gmail's server as an example)
        print("Connecting to email server...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            print("Login successful. Sending email...")
            smtp_server.send_message(msg)
            print(f"Email successfully sent to {recipient_email}")
        return True, msg_id  # Return success and the new Message-ID
    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication Error: Check your SENDER_EMAIL and SENDER_APP_PASSWORD.")
        return False, None
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
        return False, None


# --- Test Block ---
if __name__ == '__main__':
    print("--- Testing Email Service ---")
    # IMPORTANT: Replace with a real email address you can check for the test
    test_recipient = "some-real-email@example.com"

    success = send_email(
        recipient_email=test_recipient,
        subject="Email Service Test",
        body="This is a test email from the Python Agentic App."
    )

    if success:
        print("\nTest email sent successfully! Please check the recipient's inbox.")
    else:
        print("\nFailed to send the test email. Please check the error messages above.")
