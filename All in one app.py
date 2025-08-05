import streamlit as st
import os
import time
import uuid
import yaml
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from rembg.bg import remove, new_session

# --- Page Config ---
st.set_page_config(page_title="🖼️ Multi Feature Image Tool", layout="wide")

# --- Constants ---
SESSION_TIMEOUT = 180
CONFIG_FILE = "config.yaml"
SESSION_FILE = "session_data.yaml"

# --- Config Loader ---
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.error(f"Error loading config.yaml: {e}")
        st.stop()

# --- Session persistence functions ---
def load_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return yaml.safe_load(f)
    return {"active_users": {}}

def save_sessions(data):
    with open(SESSION_FILE, "w") as f:
        yaml.safe_dump(data, f)

def update_session(mobile, device_id):
    session_data["active_users"][mobile] = {
        "device_id": device_id,
        "timestamp": time.time()
    }
    save_sessions(session_data)

def is_session_valid(mobile, device_id):
    user = session_data["active_users"].get(mobile)
    return user and user["device_id"] == device_id and (time.time() - user["timestamp"] < SESSION_TIMEOUT)

def logout_user():
    mobile = st.session_state.get("mobile", "")
    if mobile in session_data["active_users"]:
        session_data["active_users"].pop(mobile)
        save_sessions(session_data)
    st.session_state.logged_in = False
    st.session_state.mobile = ""
    st.session_state.device_id = str(uuid.uuid4())

# --- Init login state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "mobile" not in st.session_state:
    st.session_state.mobile = ""
if "device_id" not in st.session_state:
    st.session_state.device_id = str(uuid.uuid4())

# --- Load credentials and sessions ---
config = load_config()
users = config["credentials"]["users"]
session_data = load_sessions()

# --- Login Page ---
if not st.session_state.logged_in:
    st.title("🔐 Login")
    mobile = st.text_input("📱 Mobile Number")
    password = st.text_input("🔑 Password", type="password")
    if st.button("Login"):
        if mobile in users and users[mobile]["password"] == password:
            existing = session_data["active_users"].get(mobile)
            if existing and time.time() - existing["timestamp"] < SESSION_TIMEOUT and existing["device_id"] != st.session_state.device_id:
                st.error("⚠️ Already logged in from another device.")
                st.stop()
            update_session(mobile, st.session_state.device_id)
            st.session_state.logged_in = True
            st.session_state.mobile = mobile
            st.success("✅ Login Successful!")
            st.rerun()
        else:
            st.error("❌ Invalid mobile number or password")
    st.stop()

# --- Validate Session ---
mobile = st.session_state.get("mobile", "")
if not is_session_valid(mobile, st.session_state.device_id):
    logout_user()
    st.warning("⚠️ Session expired. Please login again.")
    st.rerun()
update_session(mobile, st.session_state.device_id)

# --- Sidebar Logout Info ---
with st.sidebar:
    st.success(f"✅ Logged in as: {mobile}")
    remaining = SESSION_TIMEOUT - int(time.time() - session_data["active_users"][mobile]["timestamp"])
    st.info(f"⏳ Session time left: {remaining}s")
    if st.button("🚪 Logout"):
        logout_user()
        st.rerun()

# --- Feature Selection ---
st.title("🧰 Image Editing Tools")
feature = st.selectbox("Choose a feature:", [
    "Background Remover", 
    "Image Cropper", 
    "Image Resizer", 
    "Change Background Color", 
    "Add Name & Date (Exam Format)",
    "Resize Signature for Exams",
    "UPSC Photo Format Generator"
])

# --- File Upload ---
uploaded_file = st.file_uploader("📤 Upload Image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGBA")
    st.image(image, caption="📷 Original Image", use_column_width=True)

    if feature == "Background Remover":
        if st.button("✨ Remove Background"):
            with st.spinner("Processing with high-accuracy model..."):
                session = new_session("isnet-general-use")
                output = remove(
                    image,
                    session=session,
                    alpha_matting=True,
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=5
                )
                st.image(output, caption="✅ Transparent Background", use_column_width=True)
                buf = BytesIO()
                output.save(buf, format="PNG")
                st.download_button("⬇️ Download PNG", buf.getvalue(), file_name="transparent.png", mime="image/png")

    elif feature == "Image Cropper":
        x = st.number_input("Crop from Left", 0, image.width, 0)
        y = st.number_input("Crop from Top", 0, image.height, 0)
        w = st.number_input("Width", 1, image.width, image.width)
        h = st.number_input("Height", 1, image.height, image.height)
        if st.button("✂️ Crop"):
            cropped = image.crop((x, y, x + w, y + h))
            st.image(cropped, caption="✂️ Cropped Image", use_column_width=True)
            buf = BytesIO()
            cropped.save(buf, format="PNG")
            st.download_button("⬇️ Download Cropped", buf.getvalue(), file_name="cropped.png")

    elif feature == "Image Resizer":
        width = st.number_input("New Width", 1, 5000, image.width)
        height = st.number_input("New Height", 1, 5000, image.height)
        if st.button("📐 Resize"):
            resized = image.resize((width, height), Image.LANCZOS)
            st.image(resized, caption="📐 Resized Image", use_column_width=True)
            buf = BytesIO()
            resized.save(buf, format="PNG")
            st.download_button("⬇️ Download Resized", buf.getvalue(), file_name="resized.png")

    elif feature == "Change Background Color":
        color = st.color_picker("🎨 Choose Background Color", "#ffffff")
        if st.button("🧼 Apply Background"):
            bg = Image.new("RGBA", image.size, color)
            bg.paste(image, mask=image.split()[3])
            st.image(bg, caption="🎨 Background Color Changed", use_column_width=True)
            buf = BytesIO()
            bg.save(buf, format="PNG")
            st.download_button("⬇️ Download Colored", buf.getvalue(), file_name="bg_changed.png")

    elif feature == "Add Name & Date (Exam Format)":
        name = st.text_input("👤 Name")
        date = st.text_input("📅 Date")
        if st.button("📝 Generate Format"):
            formatted = image.copy()
            draw = ImageDraw.Draw(formatted)
            font = ImageFont.load_default()
            draw.text((10, image.height - 40), f"Name: {name}   Date: {date}", fill="black", font=font)
            st.image(formatted, caption="📝 Name and Date Added", use_column_width=True)
            buf = BytesIO()
            formatted.save(buf, format="PNG")
            st.download_button("⬇️ Download Exam Format", buf.getvalue(), file_name="exam_format.png")

    elif feature == "Resize Signature for Exams":
        width = st.number_input("Signature Width (px)", 50, 1000, 300)
        height = st.number_input("Signature Height (px)", 20, 500, 100)
        if st.button("✍️ Resize Signature"):
            resized = image.resize((width, height), Image.LANCZOS)
            st.image(resized, caption="✍️ Resized Signature", use_column_width=False)
            buf = BytesIO()
            resized.save(buf, format="PNG")
            st.download_button("⬇️ Download Signature", buf.getvalue(), file_name="signature_resized.png")

    elif feature == "UPSC Photo Format Generator":
        name = st.text_input("👤 Full Name (as per ID proof)")
        date = st.text_input("📅 Date (dd-mm-yyyy)")
        if st.button("📄 Generate UPSC Format"):
            upsc_img = image.convert("RGB").resize((354, 413))
            canvas = Image.new("RGB", (354, 470), "white")
            canvas.paste(upsc_img, (0, 0))
            draw = ImageDraw.Draw(canvas)
            try:
                font_bold = ImageFont.truetype("arialbd.ttf", 24)
                font_regular = ImageFont.truetype("arial.ttf", 20)
            except:
                font_bold = ImageFont.load_default()
                font_regular = ImageFont.load_default()
            draw.text((20, 418), name.upper(), fill="black", font=font_bold)
            draw.text((100, 445), date, fill="black", font=font_regular)
            st.image(canvas, caption="🪪 UPSC Format Image", use_column_width=False)
            buf = BytesIO()
            canvas.save(buf, format="JPEG")
            st.download_button("⬇️ Download UPSC Photo", buf.getvalue(), file_name="upsc_photo.jpg", mime="image/jpeg")
