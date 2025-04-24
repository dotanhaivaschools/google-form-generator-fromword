import re
import json
from docx import Document
from googleapiclient.discovery import build
from google.oauth2 import service_account
import streamlit as st


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

        # Nhận diện câu hỏi bắt đầu bằng "Câu 1:", "Câu 2:", ...
        if re.match(r"Câu \d+:", text):
            if current_question and any(opt.strip() for opt in current_question["options"]):
                questions.append(current_question)
            current_question = {
                "question": re.sub(r"Câu \d+:\s*", "", text),
                "options": [],
                "answer_key": ""
            }

        # Nhận diện đáp án bắt đầu bằng A., B., C., D.
        elif re.match(r"[A-D]\.", text):
            raw_option = text[2:].strip()
            is_underlined = False

            # Duyệt qua từng run để phát hiện run có gạch chân
            for run in para.runs:
                if run.underline and re.match(r"[A-D]\.", run.text.strip()):
                    # Gạch chân nằm trong label, không dùng
                    continue
                if run.underline:
                    is_underlined = True
                    break

            if not raw_option or raw_option.strip(".") == "":
                raw_option = f"Tùy chọn {len(current_question['options']) + 1}"

            # Gán làm đáp án đúng nếu gạch chân
            if is_underlined:
                current_question["answer_key"] = raw_option

            current_question["options"].append(raw_option)

    # Câu cuối cùng
    if current_question and any(opt.strip() for opt in current_question["options"]):
        questions.append(current_question)

    return questions


def create_google_form(questions, form_title, share_email=None):
    credentials = get_credentials()
    service = build('forms', 'v1', credentials=credentials)

    # Tạo biểu mẫu
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
        unique_options = list(dict.fromkeys(cleaned))  # loại trùng

        # Thêm dấu ⭐ vào đáp án đúng nếu có
        labeled_options = []
        for opt in unique_options:
            if opt == q["answer_key"]:
                labeled_options.append(f"{opt} ⭐")
            else:
                labeled_options.append(opt)

        if not labeled_options:
            continue

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

    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # Nếu có email chia sẻ
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
