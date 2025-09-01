import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import our custom services
import llm_service
import database_service
import email_service

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


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
    """Handles a new report request, drafts an email, and sets it up for approval."""
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if 'pending_approval_id' in context.chat_data:
        await context.bot.send_message(chat_id=chat_id,
                                       text="I'm currently waiting for your response on the last draft. Please approve or cancel it first.")
        return

    await context.bot.send_message(chat_id=chat_id, text="Analyzing and drafting...")

    parsed_data = llm_service.parse_user_input(user_message)

    if not parsed_data or not all(
            key in parsed_data and parsed_data[key] for key in ['name', 'offender_email', 'official_email']):
        await context.bot.send_message(chat_id=chat_id,
                                       text="Sorry, I couldn't extract all the required details. Please provide the person's name, their email, and the official's email.")
        return

    # *** KEY CHANGE: Pass the gist to the email generator ***
    # The .get('email_gist') will return None if the key doesn't exist, which is perfect.
    email_gist = parsed_data.get('email_gist')

    email_draft = llm_service.generate_email_draft(
        name=parsed_data['name'],
        offender_email=parsed_data['offender_email'],
        gist=email_gist  # <-- Pass the extracted gist here
    )

    report_id = database_service.create_report(
        chat_id, parsed_data['name'], parsed_data['offender_email'], parsed_data['official_email'], email_draft
    )

    context.chat_data['pending_approval_id'] = report_id

    # ... (the rest of the function remains the same) ...
    response_message = (
        f"**New Report Draft (ID: {report_id})**\n\n"
        "Here is the draft I've prepared based on your details. Please review it carefully.\n\n"
        "-------------------------------------\n"
        f"{email_draft}\n"
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
        del context.chat_data['pending_approval_id']  # Clear state on error
        return

    # *** KEY CHANGES START HERE ***

    # 1. Update status to 'sending' to prevent duplicate sends
    database_service.update_report_status(report_id, 'sending')
    await update.message.reply_text(
        f"✅ Approved! Sending the email for Report {report_id} to {report['official_email']}...")

    # 2. Prepare and send the email
    subject = f"Urgent Report Regarding Illegitimate Business Operation: {report['name']}"

    email_sent_successfully = email_service.send_email(
        recipient_email=report['official_email'],
        subject=subject,
        body=report['draft']
    )

    # 3. Update the user and the database based on the result
    if email_sent_successfully:
        database_service.update_report_status(report_id, 'sent')
        await update.message.reply_text(f"✔️ Email sent successfully for Report {report_id}.")
    else:
        database_service.update_report_status(report_id, 'send_error')
        await update.message.reply_text(
            f"❌ Report {report_id} was approved, but I failed to send the email. Please check the logs. I will not attempt to send it again automatically.")

    # 4. Clear the state
    del context.chat_data['pending_approval_id']


async def handle_cancellation_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's 'cancel' or 'no' response."""
    if 'pending_approval_id' not in context.chat_data:
        return

    report_id = context.chat_data['pending_approval_id']
    database_service.update_report_status(report_id, 'cancelled')

    # Clear the state
    del context.chat_data['pending_approval_id']

    await update.message.reply_text("❌ Okay, the report has been cancelled. You can start a new one anytime.")


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Regular expressions to catch conversational replies
    approval_filter = filters.Regex(re.compile(r'^(approve|yes|okay|ok|looks good|send it|yep)$', re.IGNORECASE))
    cancel_filter = filters.Regex(re.compile(r'^(cancel|no|stop|nevermind|dont send|don\'t send|nope)$', re.IGNORECASE))

    # Register handlers - ORDER IS IMPORTANT
    application.add_handler(CommandHandler("start", start))

    # Add the specific conversational handlers first
    application.add_handler(MessageHandler(approval_filter, handle_approval_response))
    application.add_handler(MessageHandler(cancel_filter, handle_cancellation_response))

    # Add the general message handler last as a fallback
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report))

    print("Bot is running...")
    application.run_polling()


if __name__ == '__main__':
    main()

    # email app password - jyor dtep fjce lwkt - name of the app - restaurant_reporter_bot