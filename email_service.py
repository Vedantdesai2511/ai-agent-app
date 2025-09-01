import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")


def send_email(recipient_email, subject, body):
    """
    Sends an email using credentials from the .env file.

    Args:
        recipient_email (str): The email address of the recipient.
        subject (str): The subject line of the email.
        body (str): The main content of the email.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        print("Error: Sender email or app password not configured in .env file.")
        return False

    # Create the email message object
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg.set_content(body)

    try:
        # Connect to the SMTP server (using Gmail's server as an example)
        # The 'with' statement ensures the connection is automatically closed
        print("Connecting to email server...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            print("Login successful. Sending email...")
            smtp_server.send_message(msg)
            print(f"Email successfully sent to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication Error: Check your SENDER_EMAIL and SENDER_APP_PASSWORD.")
        return False
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
        return False


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
