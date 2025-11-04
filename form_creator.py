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
    """
    Đọc file Word (.docx) và trích xuất danh sách câu hỏi.
    Hỗ trợ:
    - Câu hỏi bắt đầu bằng 'Câu n:'
    - Các đáp án A.,B.,C.,D. (dù liền hay có khoảng trắng)
    - Nội dung trong bảng (table)
    - Đáp án đúng: ký tự A./B./C./D. được gạch chân
    """
    doc = Document(file_path)
    questions = []
    current_question = None

    def handle_paragraphs(paragraphs):
        nonlocal current_question, questions

        for para in paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 🟩 Nhận diện câu hỏi
            if re.match(r"^Câu\s*\d+\s*[:\.]", text):
                if current_question and current_question.get("options"):
                    questions.append(current_question)
                current_question = {
                    "question": re.sub(r"^Câu\s*\d+\s*[:\.]\s*", "", text),
                    "options": [],
                    "answer_key": ""
                }

            # 🟨 Nhận diện các đáp án A. B. C. D.
            elif current_question and re.search(r"\b[A-D]\s*\.", text):
                # Tách từng đáp án trong 1 dòng
                parts = re.split(r"(?=\b[A-D]\s*\.)", text)
                for part in parts:
                    part = part.strip()
                    if re.match(r"^[A-D]\s*\.", part):
                        label_match = re.match(r"^([A-D])\s*\.", part)
                        if not label_match:
                            continue
                        label = label_match.group(1)
                        raw_option = re.sub(r"^[A-D]\s*\.\s*", "", part).strip()

                        if not raw_option:
                            raw_option = f"Tùy chọn {len(current_question['options']) + 1}"

                        # 🟢 Kiểm tra gạch chân trong đoạn run
                        is_underlined = any(
                            run.underline and label in run.text for run in para.runs
                        )
                        if is_underlined:
                            current_question["answer_key"] = raw_option

                        current_question["options"].append(raw_option)

    # 🧩 Duyệt qua tất cả các đoạn văn chính
    handle_paragraphs(doc.paragraphs)

    # 🧩 Duyệt cả các đoạn trong bảng (nếu có)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                handle_paragraphs(cell.paragraphs)

    # 🟦 Thêm câu cuối cùng
    if current_question and current_question.get("options"):
        questions.append(current_question)

    # ⚠️ Nếu không có câu hỏi nào được nhận dạng
    if not questions:
        raise ValueError("Không trích xuất được câu hỏi nào từ file Word! "
                         "Vui lòng kiểm tra lại định dạng: "
                         "Mỗi câu hỏi phải bắt đầu bằng 'Câu n:' và có ít nhất một đáp án A.")

    return questions


def create_google_form(questions, form_title, share_email=None):
    """Tạo Google Form từ danh sách câu hỏi"""
    credentials = get_credentials()
    service = build('forms', 'v1', credentials=credentials)

    # 🧾 Tạo biểu mẫu Google Form
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
        # Loại bỏ ký tự xuống dòng
        cleaned = [opt.strip().replace("\n", " ") for opt in q["options"] if opt.strip()]
        unique_options = list(dict.fromkeys(cleaned))

        if not unique_options:
            continue

        # Gắn dấu ⭐ vào đáp án đúng
        labeled_options = []
        for opt in unique_options:
            if opt == q["answer_key"].replace("\n", " ").strip():
                labeled_options.append(f"{opt} ⭐")
            else:
                labeled_options.append(opt)

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

    # 📨 Gửi tất cả câu hỏi lên Google Form
    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # ✉️ Chia sẻ quyền chỉnh sửa (nếu có email)
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