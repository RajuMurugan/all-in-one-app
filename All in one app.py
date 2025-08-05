import streamlit as st
import os
import time
import uuid
import yaml
from PIL import Image
from io import BytesIO
from rembg.bg import remove, new_session

# --- Page Config ---
st.set_page_config(page_title="🖼️ Transparent BG Remover", layout="wide")

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

# --- Image Background Removal UI ---
st.title("🖼️ Transparent Background Remover")

uploaded_file = st.file_uploader("📤 Upload Image (JPG/PNG)", type=["png", "jpg", "jpeg"])
if uploaded_file:
    image = Image.open(uploaded_file).convert("RGBA")
    st.image(image, caption="📷 Original Image", use_column_width=True)

    if st.button("✨ Remove Background"):
        with st.spinner("Processing high-accuracy model..."):
            # create session once per run
            session = new_session("isnet-general-use")
            output = remove(
                image,
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=5
            )

            st.image(output, caption="✅ Clean Transparent Output", use_column_width=True)
            buf = BytesIO()
            output.save(buf, format="PNG")
            byte_im = buf.getvalue()
            st.download_button("⬇️ Download PNG", byte_im, file_name="output.png", mime="image/png")
