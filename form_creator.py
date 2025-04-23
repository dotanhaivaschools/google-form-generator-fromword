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

        # Nhận diện tiêu đề câu hỏi
        if re.match(r"Câu \d+:", text):
            if current_question and any(opt.strip() for opt in current_question["options"]):
                questions.append(current_question)
            current_question = {
                "question": re.sub(r"Câu \d+:\s*", "", text),
                "options": [],
                "answer_key": ""
            }

        # Nhận diện đáp án A., B., C., D.
        elif re.match(r"[A-D]\.", text):
            raw_option = text[2:].strip()

            # Nếu rỗng hoặc chỉ là dấu chấm → gán "Tùy chọn n"
            if not raw_option or all(c == "." for c in raw_option.strip()):
                raw_option = f"Tùy chọn {len(current_question['options']) + 1}"

            # Đáp án đúng nếu có dấu gạch chân hoặc dòng
            if "____" in text or "_" in text:
                current_question["answer_key"] = raw_option

            current_question["options"].append(raw_option)

    # Thêm câu cuối
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
        drive_service.permissions().create(
            fileId=form_id,
            body=permission,
            fields='id',
            sendNotificationEmail=True
        ).execute()
    except Exception as e:
        print(f"Lỗi chia sẻ với {user_email}: {e}")

def create_google_form(questions, form_title, user_email):
    SCOPES = [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/drive"
    ]

    # Đọc thông tin xác thực từ secrets môi trường (Streamlit Cloud)
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
    form_response = service.forms().create(body=form).execute()
    form_id = form_response['formId']

    requests = []

    for q in questions:
        # Làm sạch & loại trùng đáp án
        cleaned_options = [opt.strip() for opt in q["options"] if opt.strip()]
        unique_options = list(dict.fromkeys(cleaned_options))

        if not unique_options:
            continue

        requests.append({
            "createItem": {
                "item": {
                    "title": q["question"],
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
        })

    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # Chia sẻ quyền chỉnh sửa form với người dùng
    if user_email:
        share_form_with_user(form_id, user_email, credentials)

    return f"https://docs.google.com/forms/d/{form_id}/edit"
