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
    current_question = None

    for para in doc.paragraphs:
        text = para.text.strip()

        # Nếu là dòng bắt đầu bằng "Câu 1:", "Câu 2:", ...
        if re.match(r"Câu \d+:", text):
            if current_question and current_question.get("options"):
                questions.append(current_question)
            current_question = {
                "question": re.sub(r"Câu \d+:\s*", "", text),
                "options": [],
                "answer_key": ""
            }

        # Nếu là dòng chứa A., B., C., D.
        elif current_question and any(label in text for label in ["A.", "B.", "C.", "D."]):
            # Tách từng đáp án nếu chúng nằm cùng dòng
            parts = re.split(r"(?=\b[A-D]\.)", text)
            for part in parts:
                part = part.strip()
                if re.match(r"[A-D]\.", part):
                    label = part[:2]
                    raw_option = part[2:].strip()

                    if not raw_option:
                        raw_option = f"Tùy chọn {len(current_question['options']) + 1}"

                    # Kiểm tra có gạch chân không (đáp án đúng)
                    is_underlined = any(run.underline for run in para.runs if run.text.startswith(label))
                    if is_underlined:
                        current_question["answer_key"] = raw_option

                    current_question["options"].append(raw_option)

    # Thêm câu cuối cùng nếu hợp lệ
    if current_question and current_question.get("options"):
        questions.append(current_question)

    return questions

def create_google_form(questions, form_title, share_email=None):
    credentials = get_credentials()
    service = build('forms', 'v1', credentials=credentials)

    # Tạo biểu mẫu Google Form
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
        # Làm sạch dữ liệu: loại bỏ xuống dòng
        cleaned = [opt.strip().replace("\n", " ") for opt in q["options"] if opt.strip()]
        unique_options = list(dict.fromkeys(cleaned))  # loại trùng

        if not unique_options:
            continue

        labeled_options = []
        for opt in unique_options:
            if opt == q["answer_key"].replace("\n", " ").strip():
                labeled_options.append(f"{opt} ⭐")
            else:
                labeled_options.append(opt)

        if not labeled_options:
            continue

        question_title = q["question"].replace("\n", " ").strip()

        question_item = {
            "createItem": {
                "item": {
                    "title": question_title,
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

    # Gửi tất cả câu hỏi lên biểu mẫu
    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # Chia sẻ quyền chỉnh sửa nếu có email
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