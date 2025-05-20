import streamlit as st
from form_creator_logged import parse_docx, create_google_form  # đảm bảo bạn đã đổi tên file đúng

st.title("📄 Chuyển đề thi Word sang Google Form")

uploaded_file = st.file_uploader("📤 Tải lên file Word đề thi", type=["docx"])
share_email = st.text_input("📧 Nhập địa chỉ Gmail để chia sẻ quyền chỉnh sửa Google Form:")

if uploaded_file:
    st.write("📥 Đã tải file:", uploaded_file.name)

    questions = parse_docx(uploaded_file)
    st.write("📄 Kết quả phân tích:", questions)

    if questions:
        form_title = uploaded_file.name.replace(".docx", "")
        st.write("🟢 Gọi hàm create_google_form...")
        form_url = create_google_form(form_title, questions, share_email)
        st.write("📎 Kết quả trả về:", form_url)

        if form_url:
            st.success("✅ Google Form đã được tạo thành công!")
            st.markdown(f"[🔗 Mở Google Form]({form_url})", unsafe_allow_html=True)
        else:
            st.error("❌ Không thể tạo Google Form. Vui lòng kiểm tra log.")
    else:
        st.warning("⚠️ Không có câu hỏi hợp lệ trong file Word.")
