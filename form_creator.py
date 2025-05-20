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

        # Nhận diện đáp án bắt đầu bằng A., B., ...
        elif re.match(r"[A-D]\.", text):
            option_label = text[:2]
            raw_option = text[2:].strip()

            # Nếu không có nội dung thì đặt là "Tùy chọn n"
            if not raw_option or raw_option.strip(".") == "":
                raw_option = f"Tùy chọn {len(current_question['options']) + 1}"

            # Kiểm tra xem có gạch chân không (dấu hiệu là đáp án đúng)
            is_underlined = any(run.underline for run in para.runs)
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

    # Tạo form Google
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

        if not unique_options:
            continue

        # Gắn dấu ⭐ vào đáp án đúng (nếu có)
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

    # Gửi tất cả câu hỏi lên Google Form
    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # Nếu có email chia sẻ, cấp quyền chỉnh sửa
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
