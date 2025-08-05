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
    "UPSC Photo Format Generator",
    "Convert to Grayscale",
    "Rotate Image",
    "Flip Image",
    "Convert Image Format",
    "Draw Shape",
    "Add Custom Text",
    "AI Image Upscaler"
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
            name_width = draw.textlength(name.upper(), font=font_bold)
            date_width = draw.textlength(date, font=font_regular)
            draw.text(((354 - name_width) / 2, 418), name.upper(), fill="black", font=font_bold)
            draw.text(((354 - date_width) / 2, 445), date, fill="black", font=font_regular)
            st.image(canvas, caption="🪪 UPSC Format Image", use_column_width=False)
            buf = BytesIO()
            canvas.save(buf, format="JPEG")
            st.download_button("⬇️ Download UPSC Photo", buf.getvalue(), file_name="upsc_photo.jpg", mime="image/jpeg")


# Place this right below the last elif (UPSC Photo Format Generator):

    elif feature == "Convert to Grayscale":
        if st.button("🌑 Convert to Grayscale"):
            gray_img = image.convert("L")
            st.image(gray_img, caption="🌑 Grayscale Image", use_column_width=True)
            buf = BytesIO()
            gray_img.save(buf, format="PNG")
            st.download_button("⬇️ Download Grayscale", buf.getvalue(), file_name="grayscale.png")

    elif feature == "Rotate Image":
        angle = st.slider("🔄 Select Rotation Angle", 0, 360, 90)
        if st.button("🔃 Rotate"):
            rotated = image.rotate(angle, expand=True)
            st.image(rotated, caption=f"🔃 Rotated by {angle}°", use_column_width=True)
            buf = BytesIO()
            rotated.save(buf, format="PNG")
            st.download_button("⬇️ Download Rotated", buf.getvalue(), file_name="rotated.png")

    elif feature == "Flip Image":
        direction = st.radio("↔️ Flip Direction", ["Horizontal", "Vertical"])
        if st.button("↔️ Flip"):
            flipped = image.transpose(Image.FLIP_LEFT_RIGHT if direction == "Horizontal" else Image.FLIP_TOP_BOTTOM)
            st.image(flipped, caption=f"↔️ Flipped {direction}", use_column_width=True)
            buf = BytesIO()
            flipped.save(buf, format="PNG")
            st.download_button("⬇️ Download Flipped", buf.getvalue(), file_name="flipped.png")

    elif feature == "Convert Image Format":
        new_format = st.selectbox("📁 Convert to Format", ["PNG", "JPEG"])
        if st.button("🔁 Convert Format"):
            buf = BytesIO()
            image_rgb = image.convert("RGB")
            image_rgb.save(buf, format=new_format)
            ext = "jpg" if new_format == "JPEG" else "png"
            mime = "image/jpeg" if new_format == "JPEG" else "image/png"
            st.download_button(f"⬇️ Download as {new_format}", buf.getvalue(), file_name=f"converted.{ext}", mime=mime)

    elif feature == "Draw Shape":
        shape = st.selectbox("⬛ Choose Shape", ["Rectangle", "Circle"])
        x = st.number_input("Start X", 0, image.width, 10)
        y = st.number_input("Start Y", 0, image.height, 10)
        w = st.number_input("Width/Radius", 1, image.width, 100)
        h = st.number_input("Height (for Rectangle)", 1, image.height, 100)
        color = st.color_picker("🎨 Pick Shape Color", "#ff0000")
        if st.button("✏️ Draw"):
            draw_img = image.copy()
            draw = ImageDraw.Draw(draw_img)
            if shape == "Rectangle":
                draw.rectangle([x, y, x + w, y + h], outline=color, width=5)
            else:
                draw.ellipse([x, y, x + w, y + w], outline=color, width=5)
            st.image(draw_img, caption=f"✏️ {shape} Drawn", use_column_width=True)
            buf = BytesIO()
            draw_img.save(buf, format="PNG")
            st.download_button("⬇️ Download Drawn Image", buf.getvalue(), file_name="shape_drawn.png")

    elif feature == "Add Custom Text":
        text = st.text_input("🖊️ Enter Text")
        x = st.number_input("Text X Position", 0, image.width, 10)
        y = st.number_input("Text Y Position", 0, image.height, 10)
        color = st.color_picker("🎨 Pick Text Color", "#000000")
        size = st.slider("🔠 Font Size", 10, 100, 20)
        if st.button("📝 Add Text"):
            edited = image.copy()
            draw = ImageDraw.Draw(edited)
            try:
                font = ImageFont.truetype("arial.ttf", size)
            except:
                font = ImageFont.load_default()
            draw.text((x, y), text, fill=color, font=font)
            st.image(edited, caption="📝 Text Added", use_column_width=True)
            buf = BytesIO()
            edited.save(buf, format="PNG")
            st.download_button("⬇️ Download Text Image", buf.getvalue(), file_name="text_added.png")

elif feature == "AI Image Upscaler":
    scale = st.selectbox("Select Upscale Factor", ["2×", "4×"])
    if st.button("🔍 Upscale"):
        with st.spinner("Upscaling image..."):
            scale_factor = 2 if scale == "2×" else 4
            upscaled = image.resize((image.width * scale_factor, image.height * scale_factor), Image.LANCZOS)

        st.image(upscaled, caption=f"Upscaled {scale}", use_column_width=True)
        try:
            buf = BytesIO()
            upscaled.save(buf, format="PNG")
            st.download_button("⬇️ Download Upscaled", buf.getvalue(), file_name="upscaled.png", mime="image/png")
        except Exception as e:
            st.error(f"❌ Failed to generate download: {e}")






