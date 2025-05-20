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

# Xử lý khi đã tải file
if uploaded_file:
    st.write("📥 File đã tải:", uploaded_file.name)

    # 1. Parse file Word
    questions = parse_docx(uploaded_file)
    st.write("📄 Câu hỏi đã phân tích:", questions)

    # 2. Nếu có câu hỏi, tạo form
    if questions:
        form_title = uploaded_file.name.replace(".docx", "")
        st.write("🟢 Đang tạo Google Form...")
        
        form_url = create_google_form(form_title, questions, share_email)

        st.write("📎 Kết quả trả về từ API:", form_url)

        if form_url:
            st.success("✅ Google Form đã được tạo thành công!")
            st.markdown(f"[🔗 Mở Google Form]({form_url})", unsafe_allow_html=True)
        else:
            st.error("❌ Không thể tạo Google Form. Vui lòng kiểm tra log hoặc file đầu vào.")
    else:
        st.warning("⚠️ Không có câu hỏi hợp lệ trong file Word.")
