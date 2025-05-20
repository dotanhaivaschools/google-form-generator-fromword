import streamlit as st
import tempfile
from form_creator import parse_docx, create_google_form

# 🌐 Cấu hình hiển thị trình duyệt
st.set_page_config(
    page_title="Chuyển đề thi sang Google Form",
    page_icon="📝",
    layout="centered"
)

# 🎯 Giao diện chính
st.title("📝 Chuyển đề thi Word sang Google Form")

st.markdown("""
Ứng dụng này giúp bạn:
- ✅ Trích xuất câu hỏi từ file Word (.docx)
- ✅ Tự động tạo Google Form với các câu hỏi trắc nghiệm
- ✅ Chia sẻ quyền chỉnh sửa Form cho một địa chỉ Gmail
""")

# 📥 Tải file Word
uploaded_file = st.file_uploader("📂 Tải lên file Word đề thi", type=["docx"])

# 📧 Nhập Gmail để chia sẻ quyền
user_email = st.text_input("📧 Nhập địa chỉ Gmail để chia sẻ quyền chỉnh sửa Google Form:")

# 🔘 Nút xử lý tạo form
if st.button("🚀 Tạo Google Form"):
    if not uploaded_file:
        st.warning("⚠️ Vui lòng tải lên file Word (.docx)!")
    elif not user_email or "@" not in user_email:
        st.warning("⚠️ Vui lòng nhập địa chỉ Gmail hợp lệ!")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
            tmp_file.write(uploaded_file.read())
            path = tmp_file.name

        st.success("✅ Đã tải lên file, đang xử lý...")

        try:
            questions = parse_docx(path)
            if not questions:
                st.error("❌ Không trích xuất được câu hỏi nào từ file Word!")
            else:
                form_link = create_google_form(questions, "Đề kiểm tra tự động", user_email)
                st.success("🎉 Đã tạo Google Form thành công và chia sẻ quyền chỉnh sửa!")
                st.markdown(f"[📎 Nhấn vào đây để mở Google Form]({form_link})", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi: {e}")
