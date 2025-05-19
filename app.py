import streamlit as st
import tempfile
from form_creator import parse_docx, create_google_form

st.set_page_config(page_title="Chuyển Word sang Google Form", layout="centered")
st.title("📄 Chuyển đề thi Word sang Google Form")
st.markdown("Tải lên file Word (.docx) và nhập địa chỉ Gmail để chia sẻ form sau khi tạo.")

uploaded_file = st.file_uploader("📂 Tải lên file Word đề thi", type=["docx"])
user_email = st.text_input("📧 Nhập địa chỉ Gmail để chia sẻ quyền chỉnh sửa:")

if uploaded_file and user_email and "@" in user_email:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        tmp_file.write(uploaded_file.read())
        path = tmp_file.name

    st.success("✅ Đã tải lên file. Đang xử lý...")

    try:
        questions = parse_docx(path)

        st.subheader("📋 Nhật ký xử lý:")
        if not questions:
            st.error("❌ Không tìm thấy câu hỏi hợp lệ trong file Word!")
            st.stop()

        for i, q in enumerate(questions, 1):
            st.markdown(f"**Câu {i}:** {q['question']}")
            for opt in q["options"]:
                if opt == q["answer_key"]:
                    st.markdown(f"- ✅ {opt} (Đáp án đúng)")
                else:
                    st.markdown(f"- {opt}")
            st.markdown("---")

        form_link = create_google_form(questions, "Đề kiểm tra tự động", user_email)
        st.success("🎉 Đã tạo Google Form và chia sẻ thành công!")
        st.markdown(f"[📎 Mở Form tại đây]({form_link})", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Lỗi khi tạo form: {e}")

elif uploaded_file and not user_email:
    st.warning("📧 Vui lòng nhập địa chỉ Gmail trước khi tạo Form.")
