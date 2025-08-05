import streamlit as st
import os
import time
import uuid
import yaml
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from rembg.bg import remove, new_session

# --- Page Config ---
st.set_page_config(page_title="🖼️ Transparent BG Remover & Editor", layout="wide")

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

# --- Features UI ---
st.title("🛠️ Transparent Background Remover & Editor")

uploaded_file = st.file_uploader("📤 Upload Image (JPG/PNG)", type=["png", "jpg", "jpeg"])
if uploaded_file:
    image = Image.open(uploaded_file).convert("RGBA")
    st.image(image, caption="📷 Original Image", use_column_width=True)

    if st.button("✨ Remove Background"):
        with st.spinner("Processing high-accuracy model..."):
            session = new_session("isnet-general-use")
            image = remove(
                image,
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=5
            )
        st.image(image, caption="✅ Clean Transparent Output", use_column_width=True)

    st.subheader("✂️ Crop Image")
    x1 = st.number_input("Left", 0, image.width, 0)
    y1 = st.number_input("Top", 0, image.height, 0)
    x2 = st.number_input("Right", 0, image.width, image.width)
    y2 = st.number_input("Bottom", 0, image.height, image.height)
    if st.button("Apply Crop"):
        image = image.crop((x1, y1, x2, y2))
        st.image(image, caption="Cropped Image")

    st.subheader("📐 Resize Image")
    new_width = st.number_input("Width", 1, 5000, image.width)
    new_height = st.number_input("Height", 1, 5000, image.height)
    if st.button("Apply Resize"):
        image = image.resize((new_width, new_height), Image.LANCZOS)
        st.image(image, caption="Resized Image")

    st.subheader("🎨 Change Background Color")
    bg_color = st.color_picker("Pick Color", "#FFFFFF")
    if st.button("Apply BG Color"):
        rgb = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))
        bg = Image.new("RGBA", image.size, rgb + (255,))
        image = Image.alpha_composite(bg, image)
        st.image(image, caption="New Background")

    st.subheader("📝 Add Name and Date")
    name = st.text_input("Enter Name")
    date = st.text_input("Enter Date")
    if st.button("Apply Name/Date"):
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        text = f"{name} | {date}"
        w, h = draw.textsize(text, font=font)
        x = (image.width - w) // 2
        y = image.height - h - 10
        draw.rectangle([x-5, y-5, x+w+5, y+h+5], fill=(255,255,255,180))
        draw.text((x, y), text, font=font, fill=(0,0,0))
        st.image(image, caption="Image with Name & Date")

    signature = st.file_uploader("Upload Signature", type=["png","jpg","jpeg"])
    if signature:
        sig = Image.open(signature).convert("RGBA")
        sig_resized = sig.resize((image.width//3, image.height//10), Image.LANCZOS)
        image.paste(sig_resized, (10, image.height - sig_resized.height - 10), sig_resized)
        st.image(image, caption="With Signature")

    buf = BytesIO()
    image.save(buf, format="PNG")
    st.download_button("⬇️ Download Final Image", buf.getvalue(), file_name="final_image.png", mime="image/png")
