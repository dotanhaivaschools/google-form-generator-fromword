import streamlit as st
import tempfile
from form_creator import parse_docx, create_google_form

st.set_page_config(page_title="Chuyển đề thi Word sang Google Form", layout="centered")

st.title("📄 Chuyển đề thi Word sang Google Form")
st.markdown("Tải lên file Word (.docx) và nhập địa chỉ email để chia sẻ Form sau khi tạo.")

uploaded_file = st.file_uploader("📂 Tải lên file Word đề thi", type=["docx"])
user_email = st.text_input("📧 Nhập địa chỉ Gmail để chia sẻ quyền chỉnh sửa Google Form:")

if uploaded_file and user_email and "@" in user_email:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        tmp_file.write(uploaded_file.read())
        path = tmp_file.name

    st.success("✅ Đã tải lên file, đang phân tích câu hỏi...")

    try:
        questions = parse_docx(path)

        # ✅ LOG DEBUG: Hiển thị nội dung đã parse
        st.subheader("📋 Nhật ký kiểm tra đầu vào:")
        if not questions:
            st.error("❌ Không tìm thấy câu hỏi hợp lệ trong file Word!")
        else:
            for i, q in enumerate(questions, 1):
                st.markdown(f"**Câu {i}:** {q['question']}")
                for opt in q['options']:
                    if opt == q['answer_key']:
                        st.markdown(f"- ✅ {opt} (Đáp án đúng)")
                    else:
                        st.markdown(f"- {opt}")
                st.markdown("---")

        # Nếu có câu hỏi → tạo Google Form
        if questions:
            form_link = create_google_form(questions, "Đề kiểm tra tự động", user_email)
            st.success("🎉 Đã tạo Google Form thành công và chia sẻ với bạn!")
            st.markdown(f"[📎 Mở Google Form tại đây]({form_link})", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Đã xảy ra lỗi khi tạo Google Form: `{e}`")

elif uploaded_file and not user_email:
    st.warning("📧 Vui lòng nhập địa chỉ Gmail để chia sẻ Google Form trước khi tạo.")
