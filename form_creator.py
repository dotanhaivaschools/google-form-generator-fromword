import re
from docx import Document
from googleapiclient.discovery import build
from google.oauth2 import service_account
import streamlit as st
import json

def get_credentials():
    """Lấy credentials từ Streamlit Secrets (GOOGLE_CREDENTIALS)"""
    info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    return service_account.Credentials.from_service_account_info(info)


def parse_docx(file_path):
    doc = Document(file_path)
    questions = []
    current_question = {}

    for para in doc.paragraphs:
        text = para.text.strip()

        # Câu hỏi bắt đầu bằng "Câu 1:", "Câu 2:", ...
        if re.match(r"Câu \d+:", text):
            if current_question and any(opt.strip() for opt in current_question["options"]):
                questions.append(current_question)
            current_question = {
                "question": re.sub(r"Câu \d+:\s*", "", text),
                "options": [],
                "answer_key": ""
            }

        # Đáp án A., B., C., D.
        elif re.match(r"[A-D]\.", text):
            raw_option = text[2:].strip()

            if not raw_option or all(c == '.' for c in raw_option):
                raw_option = f"Tùy chọn {len(current_question['options']) + 1}"

            # Kiểm tra underline trong bất kỳ đoạn nào
            if para.runs:
                for run in para.runs:
                    if run.underline:
                        current_question["answer_key"] = raw_option
                        break

            current_question["options"].append(raw_option)

    # Thêm câu cuối cùng
    if current_question and any(opt.strip() for opt in current_question["options"]):
        questions.append(current_question)

    return questions


def create_google_form(questions, form_title, share_email=None):
    credentials = get_credentials()
    service = build('forms', 'v1', credentials=credentials)

    form = {
        "info": {
            "title": form_title,
            "documentTitle": form_title
        }
    }
    result = service.forms().create(body=form).execute()
    form_id = result["formId"]

    requests = []

    for q in questions:
        cleaned = [opt.strip() for opt in q["options"] if opt.strip()]
        unique_options = list(dict.fromkeys(cleaned))

        if len(unique_options) < 2:
            st.warning(f"⚠️ Bỏ qua câu hỏi '{q['question']}' vì có ít hơn 2 lựa chọn hợp lệ.")
            continue

        labeled_options = []
        for opt in unique_options:
            if opt == q["answer_key"]:
                labeled_options.append(f"{opt} ⭐")
            else:
                labeled_options.append(opt)

        question_item = {
            "createItem": {
                "item": {
                    "title": q["question"],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": opt} for opt in labeled_options],
                                "shuffle": False
                            }
                        }
                    }
                },
                "location": {"index": 0}
            }
        }
        requests.append(question_item)

    if requests:
        service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

        if share_email:
            drive_service = build('drive', 'v3', credentials=credentials)
            drive_service.permissions().create(
                fileId=form_id,
                body={
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': share_email
                },
                sendNotificationEmail=True
            ).execute()

    return f"https://docs.google.com/forms/d/{form_id}/edit"
