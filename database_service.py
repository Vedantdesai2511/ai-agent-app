from tinydb import TinyDB, Query
import time

# Initialize the database. This will create a file named 'reports_db.json'
db = TinyDB('reports_db.json', indent=4)


def create_report(chat_id, name, offender_phone_number, official_email, draft, offender_details):
    """
    Saves a new report to the database. The subject is no longer stored.
    """
    report_id = int(time.time())

    db.insert({
        'report_id': report_id,
        'chat_id': chat_id,
        'status': 'awaiting_approval',
        'name': name,
        'offender_phone_number': offender_phone_number,
        'official_email': official_email,
        'draft': draft,
        'offender_details': offender_details,
        'created_at': time.time(),
        'last_updated_at': time.time(),
        'follow_up_count': 0,
        'message_id': None
    })

    print(f"Report {report_id} created for chat {chat_id}.")
    return report_id


def update_report_message_id(report_id, message_id):
    """
    Stores the Message-ID for the initial email sent.
    """
    Report = Query()
    db.update({'message_id': message_id}, Report.report_id == report_id)
    print(f"Message-ID for report {report_id} saved.")


def get_report_by_id(report_id):
    """
    Retrieves a single report from the database by its ID.
    """
    Report = Query()
    result = db.get(Report.report_id == report_id)
    return result


def update_report_status(report_id, new_status):
    """
    Updates the status of a specific report.
    """
    Report = Query()
    updated_count = db.update({'status': new_status, 'last_updated_at': time.time()}, Report.report_id == report_id)
    if updated_count:
        print(f"Report {report_id} status updated to '{new_status}'.")
        return True
    return False


def get_reports_for_follow_up(days_since_last_update):
    """
    Retrieves reports that need a follow-up email.

    Args:
        days_since_last_update (int): The number of days to look back.
    """
    Report = Query()

    # Calculate the time delta based on the argument passed from the bot
    time_delta_seconds = days_since_last_update * 24 * 60 * 60
    # cutoff_time = time.time() - time_delta_seconds

    # For your testing, you could temporarily use a smaller value:
    cutoff_time = time.time() - 15  # 15 seconds for testing

    print(f"Searching for reports last updated before {cutoff_time}...")

    reports = db.search(
        (Report.status.one_of(['sent', 'followup_sent'])) &
        (Report.last_updated_at < cutoff_time)
    )
    return reports


def increment_follow_up_count(report_id):
    """
    Increments the follow-up count and updates the timestamp for a report.
    """
    Report = Query()
    report = db.get(Report.report_id == report_id)
    if report:
        new_count = report['follow_up_count'] + 1
        db.update({
            'follow_up_count': new_count,
            'last_updated_at': time.time(),
            'status': 'followup_sent'
        }, Report.report_id == report_id)
        print(f"Report {report_id} follow-up count incremented to {new_count}.")
        return True
    return False


def get_all_reports():
    """
    Retrieves all reports currently in the database.
    """
    return db.all()


def delete_old_reports():
    """
    Deletes any report from the database that was created more than 30 days ago.
    """
    Report = Query()
    # 30 days in seconds (30 * 24 hours * 60 minutes * 60 seconds)
    one_month_ago = time.time() - (30 * 24 * 60 * 60)

    # Find and remove reports where the 'created_at' timestamp is less than one_month_ago
    deleted_reports = db.remove(Report.created_at < one_month_ago)

    if deleted_reports:
        print(f"Successfully purged {len(deleted_reports)} report(s) older than 30 days.")
    else:
        print("No old reports to purge.")
    return len(deleted_reports)


# --- Test Block ---
if __name__ == '__main__':
    print("--- Testing Database Service ---")

    # Create a dummy report
    test_id = create_report(
        chat_id=12345,
        name="Test Subject",
        offender_email="test@example.com",
        official_email="official@gov.com",
        draft="This is a test email draft."
    )

    # Retrieve the report we just created
    retrieved_report = get_report_by_id(test_id)
    print("\nRetrieved Report:")
    print(retrieved_report)
    assert retrieved_report['status'] == 'awaiting_approval'

    # Update its status
    update_report_status(test_id, 'sent')

    # Retrieve it again to confirm the change
    retrieved_report_after_update = get_report_by_id(test_id)
    print("\nRetrieved Report After Update:")
    print(retrieved_report_after_update)
    assert retrieved_report_after_update['status'] == 'sent'

    # Test follow-up functionality
    print("\n--- Testing Follow-up Logic ---")
    # Manually set the last_updated_at to be old
    db.update({'last_updated_at': time.time() - (8 * 24 * 60 * 60)}, Query().report_id == test_id)
    reports_to_follow_up = get_reports_for_follow_up()
    print(f"\nFound {len(reports_to_follow_up)} reports needing follow-up.")
    assert len(reports_to_follow_up) > 0

    increment_follow_up_count(test_id)
    report_after_follow_up = get_report_by_id(test_id)
    print("\nReport after incrementing follow-up:")
    print(report_after_follow_up)
    assert report_after_follow_up['follow_up_count'] == 1
    assert report_after_follow_up['status'] == 'followup_sent'

    print("\nDatabase tests passed!")