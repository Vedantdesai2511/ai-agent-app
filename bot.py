import os
import re
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import our custom services
import llm_service
import database_service
import email_service
import email_reader_service

# Load environment variables
load_dotenv()

# --- CONFIGURATION CONSTANT ---
# The single source of truth for the follow-up period in days.
FOLLOW_UP_DAYS = 7
DEFAULT_RECIPIENT_EMAIL = "vedantdesai07@gmail.com"
STANDARD_SUBJECT_LINE = ("Urgent: Reporting Unlicensed and Illegal Food Catering Operations - Potential Public Safety Hazard - "
                         "Requesting Action to stop this catering operation: {name}")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# --- Scheduler Setup Function ---
scheduler = AsyncIOScheduler(timezone="UTC")


async def post_init_jobs(application: Application):
    """
    This function adds jobs to the GLOBAL scheduler and starts it.
    """
    # --- 2. ADD JOBS TO THE GLOBAL SCHEDULER ---
    # We are no longer creating a new scheduler here, just using the global one.

    # For your testing:
    scheduler.add_job(send_follow_ups, 'interval', days=FOLLOW_UP_DAYS, args=[application])
    scheduler.add_job(check_for_replies_job, 'interval', minutes=15, args=[application])

    # For production:
    # scheduler.add_job(send_follow_ups, 'interval', days=FOLLOW_UP_DAYS, args=[application])
    # scheduler.add_job(check_for_replies_job, 'interval', minutes=5, args=[application])

    # --- 3. START THE SCHEDULER ---
    if not scheduler.running:
        scheduler.start()
        print(f"Scheduled jobs started.")

# --- Bot Command Handlers & Message Handlers ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and clears any state."""
    user_name = update.effective_user.first_name
    welcome_message = (
        f"Hello {user_name}!\n\n"
        "To start a report, send me the details, for example:\n"
        "'File a report for name: John Doe, email: john.d@example.com, send to officials@texas.gov'"
    )
    # Clear any leftover state from previous conversations
    context.chat_data.pop('pending_approval_id', None)
    await update.message.reply_text(welcome_message)


async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles a new report, requiring name and phone_number."""
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if 'pending_approval_id' in context.chat_data:
        await context.bot.send_message(chat_id=chat_id,
                                       text="I'm currently waiting for your response on the last draft. Please approve or cancel it first.")
        return

    await context.bot.send_message(chat_id=chat_id, text="Analyzing your report and drafting the email...")

    parsed_data = llm_service.parse_user_input_with_gemini(user_message)

    # We check for name and email BEFORE generating the draft to save API calls.
    if not parsed_data or not parsed_data.get('name') or not parsed_data.get('offender_phone_number'):
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, I couldn't create a report. Please make sure to include the offender's **name** and **phone "
                 "number** of offender."
        )
        return

    await context.bot.send_message(chat_id=chat_id, text="Drafting the email...")

    recipient_email = parsed_data.get('official_email')
    if not recipient_email:
        recipient_email = DEFAULT_RECIPIENT_EMAIL
        print(f"No recipient email provided. Using default: {DEFAULT_RECIPIENT_EMAIL}")

    offender_details = parsed_data.get('offender_details')

    email_draft_body = llm_service.generate_email_draft(
        name=parsed_data['name'],
        offender_phone_number=parsed_data['offender_phone_number'],
        offender_details=offender_details
    )

    # Pass all required details, including the now-guaranteed recipient_email
    report_id = database_service.create_report(
        chat_id, parsed_data['name'], parsed_data['offender_phone_number'], recipient_email,
        email_draft_body, offender_details
    )

    context.chat_data['pending_approval_id'] = report_id

    subject_for_preview = STANDARD_SUBJECT_LINE.format(name=parsed_data['name'])
    response_message = (
        f"**New Report Draft (ID: {report_id})**\n\n"
        "Here is the draft I've prepared based on your details. Please review it carefully.\n\n"
        "-------------------------------------\n"
        f"**Subject:** {subject_for_preview}\n\n"
        f"{email_draft_body}\n"
        "-------------------------------------\n\n"
        "**To approve and send, reply with 'approve' or 'yes'.**\n"
        "**To cancel, reply with 'cancel' or 'no'.**"
    )
    await context.bot.send_message(chat_id=chat_id, text=response_message)


async def handle_approval_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's 'approve' or 'yes' response and sends the email."""
    chat_id = update.effective_chat.id

    if 'pending_approval_id' not in context.chat_data:
        return

    report_id = context.chat_data['pending_approval_id']
    report = database_service.get_report_by_id(report_id)

    if not report:
        await update.message.reply_text("Something went wrong, I can't find that report. Please start over.")
        del context.chat_data['pending_approval_id']
        return

    database_service.update_report_status(report_id, 'sending')
    await update.message.reply_text(
        f"✅ Approved! Sending the email for Report {report_id} to {report['official_email']}...")

    subject = STANDARD_SUBJECT_LINE.format(name=report['name'])

    email_sent_successfully, message_id = email_service.send_email(
        recipient_email=report['official_email'],
        subject=subject,
        body=report['draft'],
        report_id=report_id
    )

    if email_sent_successfully:
        database_service.update_report_message_id(report_id, message_id)
        database_service.update_report_status(report_id, 'sent')
        await update.message.reply_text(f"✔️ Email sent successfully for Report {report_id}.")
    else:
        database_service.update_report_status(report_id, 'send_error')
        await update.message.reply_text(
            f"❌ Report {report_id} was approved, but I failed to send the email. I will not attempt to send it again automatically.")

    del context.chat_data['pending_approval_id']


async def handle_cancellation_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's 'cancel' or 'no' response."""
    if 'pending_approval_id' not in context.chat_data:
        return

    report_id = context.chat_data['pending_approval_id']
    database_service.update_report_status(report_id, 'cancelled')

    del context.chat_data['pending_approval_id']

    await update.message.reply_text("❌ Okay, the report has been cancelled. You can start a new one anytime.")


# --- Scheduled Job Functions ---

async def send_follow_ups(context: ContextTypes.DEFAULT_TYPE):
    """
    Job to send follow-up emails for reports that haven't been responded to.
    """
    # ... (This function remains exactly the same as the last version) ...
    print("--- Running follow-up job ---")
    reports = database_service.get_reports_for_follow_up(days_since_last_update=FOLLOW_UP_DAYS)
    if not reports:
        print("No reports due for a follow-up.")
        return
    print(f"Found {len(reports)} candidate(s) for follow-up.")
    for report in reports:
        report_id = report['report_id']
        has_reply = email_reader_service.check_for_reply_to_report(report_id)
        if has_reply:
            print(f"Reply found for Report {report_id}. Cancelling follow-up and updating status.")
            database_service.update_report_status(report_id, 'reply_received')
            continue
        print(f"No reply found for Report {report_id}. Proceeding with follow-up.")
        if not report.get('message_id'):
            print(f"Skipping follow-up for report {report_id} because it has no Message-ID.")
            continue

        follow_up_draft = llm_service.generate_follow_up_email(
            report['name'],
            report['offender_phone_number'],
            report.get('offender_details')
        )

        # --- KEY CHANGE: A standardized subject is used for follow-ups ---
        follow_up_subject = f"Follow-Up: Urgent Report Regarding {report['name']}"

        email_service.send_email(
            recipient_email=report['official_email'],
            subject=follow_up_subject,
            body=follow_up_draft,
            report_id=report['report_id'],
            thread_message_id=report['message_id']
        )
        database_service.increment_follow_up_count(report['report_id'])


async def check_for_replies_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job to check for email replies and notify the user with the full reply content.
    """
    print("--- Running job: Checking for email replies ---")
    replies = email_reader_service.check_for_replies()

    if not replies:
        print("No new email replies found.")
        return

    print(f"Found {len(replies)} new email(s). Processing...")
    for reply in replies:
        report_id = reply['report_id']
        report = database_service.get_report_by_id(report_id)

        if not report:
            print(f"Warning: Found reply for a report ID ({report_id}) that is not in the database. Skipping.")
            continue

        # Check the status BEFORE deciding to send
        if report.get('status') == 'reply_received':
            print(f"Reply for Report {report_id} has already been processed. Skipping notification.")
            continue

        # If we've reached here, it's a new reply that needs processing.
        print(f"Processing new reply for Report {report_id}...")

        # 1. Send the notification FIRST
        full_reply_text = reply.get('full_reply', "Could not extract reply content.")
        if len(full_reply_text) > 4000:
            full_reply_text = full_reply_text[:4000] + "\n\n[Message truncated due to length]"

        notification_message = (
            f"📢 **Reply Received for Report {report_id}**\n\n"
            "--- Reply Content ---\n"
            f"{full_reply_text}"
        )

        try:
            await context.bot.send_message(
                chat_id=report['chat_id'],
                text=notification_message
            )
            print(f"Successfully sent Telegram notification for Report {report_id}.")

            # 2. Update the status in the database AFTER successful notification
            database_service.update_report_status(report_id, 'reply_received')
            print(f"Updated status for Report {report_id} to 'reply_received'.")

        except Exception as e:
            print(f"Error sending Telegram notification for Report {report_id}: {e}")


async def main() -> None:
    """
    Starts the bot, the scheduler, and runs them until interrupted.
    """
    # --- 1. Create the Application and Scheduler ---
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    scheduler = AsyncIOScheduler(timezone="UTC")

    # --- 2. Add handlers to the application ---
    approval_filter = filters.Regex(re.compile(r'^(approve|yes|okay|ok|looks good|send it|yep)$', re.IGNORECASE))
    cancel_filter = filters.Regex(re.compile(r'^(cancel|no|stop|nevermind|dont send|don\'t send|nope)$', re.IGNORECASE))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(approval_filter, handle_approval_response))
    application.add_handler(MessageHandler(cancel_filter, handle_cancellation_response))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report))

    # --- 3. Manage the application lifecycle with an async context manager ---
    async with application:
        # --- 4. Initialize the application and scheduler ---
        await application.initialize()  # Initializes the bot and gets it ready

        # Add jobs to the scheduler
        scheduler.add_job(send_follow_ups, 'interval', days=FOLLOW_UP_DAYS, args=[application])
        scheduler.add_job(check_for_replies_job, 'interval', minutes=5, args=[application])
        scheduler.start()
        print(f"Scheduled jobs started. Follow-ups will be sent every {FOLLOW_UP_DAYS} days.")

        # --- 5. Start the bot's polling mechanism ---
        await application.start()
        await application.updater.start_polling()
        print("Bot is running...")

        # --- 6. Run indefinitely until a stop signal is received ---
        # This part is to keep the script alive. You can use a simple sleep loop.
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, or any long duration


# --- 7. Run the main async function ---
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")