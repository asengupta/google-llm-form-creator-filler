from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json
import os

SCOPES = ["https://www.googleapis.com/auth/forms.body"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds


def create_form(title, questions):
    """Create a Google Form with the given title and questions.

    Args:
        title: Form title string.
        questions: List of dicts with keys:
            - title: Question text
            - type: "SHORT_ANSWER", "PARAGRAPH", "MULTIPLE_CHOICE", "CHECKBOX", "DROPDOWN"
            - required: bool (default False)
            - options: list of strings (for MULTIPLE_CHOICE, CHECKBOX, DROPDOWN)
    """
    creds = get_credentials()
    service = build("forms", "v1", credentials=creds)

    # Create the form with just a title
    form = service.forms().create(body={"info": {"title": title}}).execute()
    form_id = form["formId"]

    # Build batch update requests to add questions
    requests = []
    for i, q in enumerate(questions):
        question_item = {
            "title": q["title"],
            "questionItem": {
                "question": {
                    "required": q.get("required", False),
                }
            },
        }

        q_type = q.get("type", "SHORT_ANSWER")

        if q_type in ("SHORT_ANSWER", "PARAGRAPH"):
            question_item["questionItem"]["question"]["textQuestion"] = {
                "paragraph": q_type == "PARAGRAPH"
            }
        elif q_type in ("MULTIPLE_CHOICE", "CHECKBOX", "DROPDOWN"):
            type_map = {
                "MULTIPLE_CHOICE": "RADIO",
                "CHECKBOX": "CHECKBOX",
                "DROPDOWN": "DROP_DOWN",
            }
            question_item["questionItem"]["question"]["choiceQuestion"] = {
                "type": type_map[q_type],
                "options": [{"value": opt} for opt in q.get("options", [])],
            }

        requests.append({
            "createItem": {
                "item": question_item,
                "location": {"index": i},
            }
        })

    if requests:
        service.forms().batchUpdate(
            formId=form_id, body={"requests": requests}
        ).execute()

    print(f"Form created: https://docs.google.com/forms/d/{form_id}/edit")
    print(f"Responder URL: https://docs.google.com/forms/d/e/{form_id}/viewform")
    return form_id


if __name__ == "__main__":
    # Example: create a sample form
    form_id = create_form(
        title="Sample Survey",
        questions=[
            {"title": "What is your name?", "type": "SHORT_ANSWER", "required": True},
            {"title": "Tell us about yourself", "type": "PARAGRAPH"},
            {
                "title": "Favorite color?",
                "type": "MULTIPLE_CHOICE",
                "options": ["Red", "Blue", "Green", "Other"],
            },
            {
                "title": "Which languages do you know?",
                "type": "CHECKBOX",
                "options": ["Python", "JavaScript", "Go", "Rust"],
            },
        ],
    )
