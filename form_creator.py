import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from docx import Document

# Hàm lấy credentials từ secrets
def get_credentials():
    try:
        info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        return service_account.Credentials.from_service_account_info(info, scopes=[
            'https://www.googleapis.com/auth/forms.body',
            'https://www.googleapis.com/auth/forms.responses.readonly',
            'https://www.googleapis.com/auth/drive'
        ])
    except Exception as e:
        st.error(f"❌ Lỗi khi tải thông tin xác thực: {e}")
        return None

# Hàm phân tích file .docx thành danh sách câu hỏi
def parse_docx(docx_file):
    try:
        document = Document(docx_file)
        questions = []
        current_question = None

        for para in document.paragraphs:
            text = para.text.strip()

            if text.lower().startswith("câu"):
                if current_question:
                    questions.append(current_question)
                current_question = {
                    "question": text,
                    "options": [],
                    "answer_index": -1
                }
            elif text[:2] in ["A.", "B.", "C.", "D."] and current_question:
                option_text = text[2:].strip()

                # Kiểm tra định dạng gạch chân
                if any(run.underline for run in para.runs):
                    current_question["answer_index"] = len(current_question["options"])
                    option_text += " ⭐"

                current_question["options"].append(option_text)

        if current_question:
            questions.append(current_question)

        return questions
    except Exception as e:
        st.error(f"❌ Lỗi khi đọc file Word: {e}")
        return []

# Hàm tạo Google Form và chia sẻ
def create_google_form(title, questions, share_email):
    try:
        creds = get_credentials()
        if not creds:
            return None

        forms_service = build('forms', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # 1. Tạo biểu mẫu
        NEW_FORM = {"info": {"title": title}}
        form = forms_service.forms().create(body=NEW_FORM).execute()
        form_id = form["formId"]

        # 2. Tạo danh sách câu hỏi
        requests_list = []
        for q in questions:
            item = {
                "createItem": {
                    "item": {
                        "title": q["question"],
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [{"value": opt} for opt in q["options"]],
                                    "shuffle": False
                                }
                            }
                        }
                    },
                    "location": {"index": 0}
                }
            }
            requests_list.append(item)

        # 3. Gửi câu hỏi vào biểu mẫu
        forms_service.forms().batchUpdate(formId=form_id, body={"requests": requests_list}).execute()

        # 4. Đưa vào thư mục Drive để cho phép chia sẻ
        try:
            drive_service.files().update(
                fileId=form_id,
                addParents='root'
            ).execute()
        except Exception as e:
            st.warning(f"⚠️ Không thể lưu form vào Google Drive: {e}")

        # 5. Chia sẻ nếu có email
        if share_email and "@" in share_email:
            try:
                drive_service.permissions().create(
                    fileId=form_id,
                    body={
                        'type': 'user',
                        'role': 'writer',
                        'emailAddress': share_email
                    },
                    sendNotificationEmail=True
                ).execute()
            except Exception as e:
                st.warning(f"⚠️ Không thể chia sẻ form với {share_email}: {e}")
        else:
            st.warning("⚠️ Bạn chưa nhập địa chỉ Gmail hợp lệ để chia sẻ Google Form.")

        # 6. Trả lại liên kết chỉnh sửa form
        form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        return form_url

    except Exception as e:
        st.error(f"❌ Đã xảy ra lỗi khi tạo Google Form: {e}")
        return None
