import streamlit as st
from form_creator import parse_docx, create_google_form

st.set_page_config(page_title="Chuyển đề Word sang Google Form", layout="centered")
st.title("📝 Chuyển đề thi Word sang Google Form")

st.markdown("""
Ứng dụng này giúp bạn:
- ✅ Trích xuất câu hỏi từ file Word (.docx)
- ✅ Tự động tạo Google Form với các câu hỏi trắc nghiệm
- ✅ Chia sẻ quyền chỉnh sửa Form cho một địa chỉ Gmail
""")

# Upload file Word
uploaded_file = st.file_uploader("📤 Tải lên file Word đề thi (.docx)", type=["docx"])

# Nhập Gmail để chia sẻ
share_email = st.text_input("📧 Nhập Gmail để chia sẻ quyền chỉnh sửa Google Form")

# Xử lý khi có file tải lên
if uploaded_file:
    st.write("📥 File đã tải:", uploaded_file.name)

    # Parse Word
    questions = parse_docx(uploaded_file)
    st.write("📄 Kết quả phân tích:", questions)

    if not questions:
        st.warning("⚠️ Không có câu hỏi hợp lệ trong file Word.")
    else:
        form_title = uploaded_file.name.replace(".docx", "")
        st.write("🟢 Gọi hàm create_google_form()...")
        form_url = create_google_form(form_title, questions, share_email)
        st.write("📎 Kết quả trả về:", form_url)

        if form_url:
            st.success("✅ Google Form đã được tạo thành công!")
            st.markdown(f"[🔗 Mở Google Form]({form_url})", unsafe_allow_html=True)
        else:
            st.error("❌ Không thể tạo Google Form. Vui lòng kiểm tra dữ liệu đầu vào hoặc quyền chia sẻ.")
