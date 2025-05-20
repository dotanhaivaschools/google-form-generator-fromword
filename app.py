import streamlit as st
from form_creator import parse_docx, create_google_form
import mimetypes

st.set_page_config(page_title="Chuyển đề Word sang Google Form", layout="centered")
st.title("📝 Chuyển đề thi Word sang Google Form")

st.markdown("""
Ứng dụng này giúp bạn:
- ✅ Trích xuất câu hỏi từ file Word (.docx)
- ✅ Tự động tạo Google Form với các câu hỏi trắc nghiệm
- ✅ Chia sẻ quyền chỉnh sửa Form cho một địa chỉ Gmail
""")

uploaded_file = st.file_uploader("📤 Tải lên file Word đề thi (.docx)", type=["docx"])
share_email = st.text_input("📧 Nhập Gmail để chia sẻ quyền chỉnh sửa Google Form")
submit_btn = st.button("🔄 Tạo Google Form")

# ✅ Kiểm tra file có thực sự được nhận
if uploaded_file:
    st.success("✅ Đã nhận file từ phía người dùng")
    st.write("📥 Tên file:", uploaded_file.name)
    st.write("📏 Dung lượng:", uploaded_file.size, "bytes")

    mime_type, _ = mimetypes.guess_type(uploaded_file.name)
    st.write("📎 MIME type:", mime_type)

if submit_btn:
    if not uploaded_file:
        st.error("❌ Không nhận được file từ file_uploader. Có thể do lỗi upload trên Cloud hoặc định dạng không hỗ trợ.")
    elif not share_email or "@" not in share_email:
        st.warning("⚠️ Vui lòng nhập địa chỉ Gmail hợp lệ.")
    else:
        st.write("📄 Đang phân tích câu hỏi từ file Word...")
        questions = parse_docx(uploaded_file)
        st.write("📄 Kết quả phân tích:", questions)

        if not questions:
            st.warning("⚠️ Không có câu hỏi hợp lệ trong file Word.")
        else:
            form_title = uploaded_file.name.replace(".docx", "")
            st.write("🟢 Gọi hàm create_google_form...")
            form_url = create_google_form(form_title, questions, share_email)
            st.write("📎 Kết quả trả về:", form_url)

            if form_url:
                st.success("✅ Google Form đã được tạo thành công!")
                st.markdown(f"[🔗 Mở Google Form]({form_url})", unsafe_allow_html=True)
            else:
                st.error("❌ Không thể tạo Google Form. Vui lòng kiểm tra dữ liệu đầu vào hoặc quyền chia sẻ.")
