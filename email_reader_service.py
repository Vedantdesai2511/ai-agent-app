import os
import imaplib
import email
from email.header import decode_header
import re
from dotenv import load_dotenv

load_dotenv()

IMAP_SERVER = "imap.gmail.com"
IMAP_USER = os.getenv("SENDER_EMAIL")
IMAP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")


def _decode_subject(header):
    """
    Decodes an email subject header to a readable string.
    """
    if header is None:
        return ""

    decoded_parts = decode_header(header)
    subject = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            # If charset is None, default to a common encoding like 'utf-8'
            subject.append(part.decode(charset or 'utf-8', 'ignore'))
        else:
            subject.append(part)
    return "".join(subject)


def _parse_report_id_from_subject(subject):
    if not subject: return None
    match = re.search(r"\[Report ID: (\d+)\]", subject)
    if match: return int(match.group(1))
    return None


def check_for_reply_to_report(report_id):
    """
    Checks the inbox for a reply to a specific report ID.

    Returns:
        bool: True if a reply is found, False otherwise.
    """
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("inbox")

        # Search specifically for an unread email with the report ID in the subject
        search_criteria = f'(UNSEEN SUBJECT "[Report ID: {report_id}]")'
        status, messages = mail.search(None, search_criteria)

        mail.logout()

        if status == "OK" and messages[0]:
            print(f"Found a reply for report {report_id}.")
            return True
        return False

    except Exception as e:
        print(f"An error occurred during targeted reply check for Report ID {report_id}: {e}")
        return False


def check_for_replies():
    """
    Checks for ALL unread email replies and extracts the report ID.
    This remains as a general catch-all.
    """
    # ... (This entire function remains exactly the same as the last version) ...
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            mail.logout()
            return []
        message_numbers = messages[0].split()
        if not message_numbers or message_numbers == [b'']:
            mail.logout()
            return []
        replies = []
        for num in message_numbers:
            status, data = mail.fetch(num, "(RFC822)")
            if status != "OK": continue
            msg_data = data[0][1]
            msg = email.message_from_bytes(msg_data)
            subject = _decode_subject(msg["Subject"])
            parsed_id = _parse_report_id_from_subject(subject)
            if parsed_id:
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                            try: body = part.get_payload(decode=True).decode(); break
                            except: continue
                else:
                    try: body = msg.get_payload(decode=True).decode()
                    except: body = ""
                replies.append({"report_id": parsed_id, "snippet": body[:200]})
        mail.logout()
        return replies
    except Exception as e:
        print(f"An error occurred while checking for replies: {e}")
        return []


if __name__ == '__main__':
    print("--- Testing Email Reader Service ---")
    replies = check_for_replies()
    if replies:
        print(f"Found {len(replies)} replies:")
        for reply in replies:
            print(f"  - Report ID: {reply['report_id']}, Snippet: {reply['snippet']}")
    else:
        print("No new replies found.")