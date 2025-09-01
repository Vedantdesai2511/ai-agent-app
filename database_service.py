from tinydb import TinyDB, Query
import time

# Initialize the database. This will create a file named 'reports_db.json'
db = TinyDB('reports_db.json', indent=4)


def create_report(chat_id, name, offender_email, official_email, draft):
    """
    Saves a new report to the database with a unique ID and initial status.

    Returns:
        The integer ID of the newly created report.
    """
    # Generate a unique ID based on the current timestamp
    report_id = int(time.time())

    db.insert({
        'report_id': report_id,
        'chat_id': chat_id,
        'status': 'awaiting_approval',  # The initial state of any new report
        'name': name,
        'offender_email': offender_email,
        'official_email': official_email,
        'draft': draft,
        'created_at': time.time(),
        'follow_up_count': 0
    })

    print(f"Report {report_id} created for chat {chat_id}.")
    return report_id


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
    updated_count = db.update({'status': new_status}, Report.report_id == report_id)
    if updated_count:
        print(f"Report {report_id} status updated to '{new_status}'.")
        return True
    return False


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
    update_report_status(test_id, 'approved')

    # Retrieve it again to confirm the change
    retrieved_report_after_update = get_report_by_id(test_id)
    print("\nRetrieved Report After Update:")
    print(retrieved_report_after_update)
    assert retrieved_report_after_update['status'] == 'approved'

    print("\nDatabase tests passed!")