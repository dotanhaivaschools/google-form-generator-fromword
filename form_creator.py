import re
import json
import os
from docx import Document
from google.oauth2 import service_account
from googleapiclient.discovery import build

def parse_docx(file_path):
    doc = Document(file_path)
    questions = []
    current_question = {}

    for para in doc.paragraphs:
        text = para.text.strip()

        if re.match(r"Câu \d+:", text):
            if current_question and any(opt.strip() for opt in current_question["options"]):
                questions.append(current_question)
            current_question = {
                "question": re.sub(r"Câu \d+:\s*", "", text),
                "options": [],
                "answer_key": ""
            }

        elif re.match(r"[A-D]\.", text):
            raw_option = text[2:].strip()
            if not raw_option or all(char == '.' for char in raw_option):
                raw_option = f"Tùy chọn {len(current_question['options']) + 1}"

            if "____" in text or "_" in text:
                current_question["answer_key"] = raw_option

            current_question["options"].append(raw_option)

    if current_question and any(opt.strip() for opt in current_question["options"]):
        questions.append(current_question)

    return questions

def share_form_with_user(form_id, user_email, credentials):
    drive_service = build('drive', 'v3', credentials=credentials)

    permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': user_email
    }

    try:
        result = drive_service.permissions().create(
            fileId=form_id,
            body=permission,
            fields='id',
            sendNotificationEmail=True
        ).execute()
        print(f"✅ Đã chia sẻ Form cho {user_email}. ID phân quyền: {result.get('id')}")
    except Exception as e:
        print(f"⚠️ Lỗi chia sẻ với {user_email}: {e}")

def create_google_form(questions, form_title, user_email):
    SCOPES = [
        'https://www.googleapis.com/auth/forms.body',
        'https://www.googleapis.com/auth/drive'
    ]

    # Đọc credentials từ biến môi trường GOOGLE_CREDENTIALS (đã cấu hình trong Streamlit Secrets)
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_CREDENTIALS"]),
        scopes=SCOPES
    )

    service = build('forms', 'v1', credentials=credentials)

    form = {
        "info": {
            "title": form_title,
            "documentTitle": form_title
        }
    }
    result = service.forms().create(body=form).execute()
    form_id = result['formId']

    requests = []

    for q in questions:
        cleaned_options = [opt.strip() for opt in q["options"] if opt.strip()]
        unique_options = list(dict.fromkeys(cleaned_options))

        if not unique_options:
            continue

        question_request = {
            "createItem": {
                "item": {
                    "title": q['question'],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": opt} for opt in unique_options],
                                "shuffle": False
                            }
                        }
                    }
                },
                "location": {"index": 0}
            }
        }
        requests.append(question_request)

    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    if user_email:
        share_form_with_user(form_id, user_email, credentials)

    return f"https://docs.google.com/forms/d/{form_id}/edit"
