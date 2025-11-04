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
    Đọc file Word (.docx) và trích xuất danh sách câu hỏi từ nội dung Markdown chuyển sang Word.
    - Tự tách câu hỏi và đáp án dù cùng 1 paragraph
    - Hỗ trợ cả bảng (table)
    - Nhận dạng "Câu n:" ở giữa hoặc đầu dòng
    - Xử lý soft line breaks, tab, và xuống dòng mềm
    """
    doc = Document(file_path)
    questions = []
    current_question = None

    def extract_from_text_block(block_text):
        """Tách câu hỏi và đáp án trong 1 đoạn văn duy nhất"""
        nonlocal current_question, questions

        # Chuẩn hóa: bỏ ký tự thừa, thay xuống dòng mềm bằng dấu cách
        block_text = block_text.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()
        # Gom nhiều khoảng trắng liên tiếp thành 1
        block_text = re.sub(r"\s{2,}", " ", block_text)

        # Nếu có nhiều câu hỏi trong 1 block → tách riêng
        segments = re.split(r"(?=Câu\s*\d+\s*[:\.])", block_text)
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue

            # Nếu là câu hỏi
            if re.match(r"^Câu\s*\d+\s*[:\.]", seg):
                if current_question and current_question.get("options"):
                    questions.append(current_question)
                current_question = {
                    "question": "",
                    "options": [],
                    "answer_key": ""
                }

                # Lấy nội dung câu hỏi
                match_q = re.match(r"^Câu\s*\d+\s*[:\.]\s*(.+)", seg)
                if match_q:
                    current_question["question"] = match_q.group(1).strip()

            # Lấy các đáp án (A. B. C. D.)
            parts = re.split(r"(?=\b[A-D]\s*\.)", seg)
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
                    current_question["options"].append(raw_option)

    # Hàm xử lý toàn bộ đoạn và bảng
    def handle_paragraphs(paragraphs):
        for para in paragraphs:
            text = para.text.strip()
            if text:
                extract_from_text_block(text)

    # Duyệt toàn bộ đoạn văn chính
    handle_paragraphs(doc.paragraphs)

    # Duyệt cả bảng (nếu có)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                handle_paragraphs(cell.paragraphs)

    # Câu hỏi cuối cùng
    if current_question and current_question.get("options"):
        questions.append(current_question)

    if not questions:
        raise ValueError(
            "Không trích xuất được câu hỏi nào từ file Word! "
            "Kiểm tra lại nội dung: Mỗi câu hỏi phải chứa 'Câu n:' và ít nhất một đáp án A."
        )

    return questions


def create_google_form(questions, form_title, share_email=None):
    """Tạo Google Form từ danh sách câu hỏi"""
    credentials = get_credentials()
    service = build("forms", "v1", credentials=credentials)

    # Tạo form
    form = {"info": {"title": form_title, "documentTitle": form_title}}
    result = service.forms().create(body=form).execute()
    form_id = result["formId"]

    requests = []
    for q in questions:
        cleaned = [opt.strip().replace("\n", " ") for opt in q["options"] if opt.strip()]
        unique_options = list(dict.fromkeys(cleaned))

        if not unique_options:
            continue

        labeled_options = [opt for opt in unique_options]

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
                                "shuffle": False,
                            }
                        }
                    },
                },
                "location": {"index": 0},
            }
        }
        requests.append(question_item)

    # Gửi lên Form
    service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()

    # Chia sẻ quyền nếu có email
    if share_email:
        drive_service = build("drive", "v3", credentials=credentials)
        drive_service.permissions().create(
            fileId=form_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": share_email,
            },
            sendNotificationEmail=True,
        ).execute()

    return f"https://docs.google.com/forms/d/{form_id}/edit"