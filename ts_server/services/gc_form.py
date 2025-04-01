import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
GOOGLE_FORM_NAME = os.getenv("GOOGLE_FORM_NAME", "Subscribers_Form_Dev")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your-email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your-email-password")
SHARE_WITH_EMAILS = os.getenv("SHARE_WITH_EMAILS", "team@example.com").split(',')

SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.create",
    "https://www.googleapis.com/auth/forms.readonly",
    "https://www.googleapis.com/auth/drive"
]

form_questions_cache = {}
GOOGLE_FORM_ID = None

def get_google_form_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("forms", "v1", credentials=creds)

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

def send_admin_notification(message):
    try:
        msg = MIMEText(message)
        msg['Subject'] = "Google Form Created Notification"
        msg['From'] = SMTP_USERNAME
        msg['To'] = ADMIN_EMAIL

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, ADMIN_EMAIL, msg.as_string())
        print("Admin notification sent successfully.")
    except Exception as e:
        print(f"Failed to send admin notification: {str(e)}")

def share_google_sheet(sheet_id):
    drive_service = get_drive_service()
    for email in SHARE_WITH_EMAILS:
        try:
            drive_service.permissions().create(
                fileId=sheet_id,
                body={
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': email.strip()
                },
                fields='id'
            ).execute()
            print(f"Shared sheet with {email.strip()}.")
        except Exception as e:
            print(f"Failed to share sheet with {email.strip()}: {str(e)}")

def create_google_form():
    service = get_google_form_service()
    drive_service = get_drive_service()

    form_metadata = {"info": {"title": GOOGLE_FORM_NAME}}
    form = service.forms().create(body=form_metadata).execute()
    form_id = form.get("formId")

    questions = [
        {"title": "Name", "questionItem": {"question": {"required": True, "textQuestion": {}}}},
        {"title": "Email", "questionItem": {"question": {"required": True, "textQuestion": {}}}},
        {"title": "Subscribed Date", "questionItem": {"question": {"textQuestion": {}}}},
        {"title": "isSubscribed", "questionItem": {"question": {"textQuestion": {}}}}
    ]
    update_request = {"requests": [{"createItem": {"item": q}} for q in questions]}
    service.forms().batchUpdate(formId=form_id, body=update_request).execute()

    sheet_metadata = {
        "name": f"{GOOGLE_FORM_NAME}_Responses",
        "mimeType": "application/vnd.google-apps.spreadsheet"
    }
    sheet = drive_service.files().create(body=sheet_metadata, fields="id").execute()
    sheet_id = sheet.get("id")

    share_google_sheet(sheet_id)

    print(f"Created new Google Sheet for responses: {sheet_id}")
    # send_admin_notification(
    #     f"A new Google Form '{GOOGLE_FORM_NAME}' was created with ID {form_id}, linked to sheet ID {sheet_id}."
    # )
    return form_id

def find_or_create_google_form():
    global GOOGLE_FORM_ID
    if GOOGLE_FORM_ID:
        return GOOGLE_FORM_ID
    GOOGLE_FORM_ID = create_google_form()
    return GOOGLE_FORM_ID

def preload_form_questions():
    global form_questions_cache, GOOGLE_FORM_ID
    service = get_google_form_service()
    GOOGLE_FORM_ID = find_or_create_google_form()
    if not GOOGLE_FORM_ID:
        return
    try:
        form = service.forms().get(formId=GOOGLE_FORM_ID).execute()
        questions = {}
        for item in form.get("items", []):
            if "questionItem" in item:
                question_title = item["title"]
                question_id = item["questionItem"]["question"]["questionId"]
                questions[question_title] = question_id
        form_questions_cache = questions
        print("Google Form questions preloaded successfully.")
    except Exception as e:
        print(f"Failed to preload form questions: {str(e)}")

def get_existing_answers_by_email(email):
    service = get_google_form_service()
    try:
        responses = service.forms().responses().list(formId=GOOGLE_FORM_ID).execute()
        for response in responses.get("responses", []):
            email_found = False
            is_subscribed = "Unknown"
            answer_map = {}
            for question_id, answer in response.get("answers", {}).items():
                if "textAnswers" in answer:
                    values = [ans.get("value") for ans in answer["textAnswers"]["answers"] if ans.get("value")]
                    for val in values:
                        if val == email:
                            email_found = True
                        if val in ["True", "False"]:
                            is_subscribed = val
                        answer_map[question_id] = values[0] if values else None
            if email_found:
                return answer_map, is_subscribed
        return None, "Not Found"
    except Exception as e:
        return None, str(e)

def check_subscription_status(email):
    answers, status = get_existing_answers_by_email(email)
    if not answers:
        return status
    value = answers.get("isSubscribed", "Unknown")
    return value

def submit_to_google_form(name, email, is_subscribed=True):
    service = get_google_form_service()
    questions = form_questions_cache
    subscribed_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    is_subscribed_value = "True" if is_subscribed else "False"
    form_response = {
        "responses": [
            {"questionId": questions.get("Name"), "textAnswers": {"answers": [{"value": name}]}},
            {"questionId": questions.get("Email"), "textAnswers": {"answers": [{"value": email}]}},
            {"questionId": questions.get("Subscribed Date"), "textAnswers": {"answers": [{"value": subscribed_date}]}},
            {"questionId": questions.get("isSubscribed"), "textAnswers": {"answers": [{"value": is_subscribed_value}]}}
        ]
    }
    try:
        request = service.forms().responses().create(
            formId=GOOGLE_FORM_ID, body=form_response
        )
        return request.execute()
    except Exception as e:
        return str(e)

preload_form_questions()
