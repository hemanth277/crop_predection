import os
import gradio as gr
from dotenv import load_dotenv
from PIL import Image
import base64
import io
import hashlib
import traceback
import google.generativeai as genai

load_dotenv()

# ===============================
# GEMINI CONFIG
# ===============================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ===============================
# IMAGE CACHE ONLY
# ===============================
crop_cache = {}


def get_hash(image_bytes):
    return hashlib.md5(image_bytes).hexdigest()


# ===============================
# IDENTIFY CROP
# ===============================
def identify_crop(image_file, crop_state):

    if image_file is None:
        return "❌ Please upload a crop image.", crop_state

    try:
        img = Image.open(image_file)

        if img.width > 1000 or img.height > 1000:
            img.thumbnail((1000, 1000))

        if img.mode != "RGB":
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)

        image_bytes = buffer.getvalue()
        image_hash = get_hash(image_bytes)

        # ✅ cache
        if image_hash in crop_cache:
            result = crop_cache[image_hash]
            return f"🌾 Cached Crop Result:\n\n{result}", result

        model = genai.GenerativeModel(
            "gemini-pro-vision",
            system_instruction="You are an expert agricultural scientist."
        )

        response = model.generate_content(
            ["Identify this crop briefly.", img],
            generation_config=genai.GenerationConfig(max_output_tokens=300)
        )

        result = response.text
        crop_cache[image_hash] = result

        # ✅ SAVE ONLY IN SESSION
        return f"🌾 Crop Identification:\n\n{result}", result

    except Exception:
        return traceback.format_exc(), crop_state


# ===============================
# CHATBOT
# ===============================
def ask_chatbot(message, crop_state):

    if not crop_state:
        return "⚠️ Please upload and identify a crop image first."

    context = f"\nCrop Info:\n{crop_state}\n"

    model = genai.GenerativeModel(
        "gemini-pro",
        system_instruction="You are a farming advisor. Give direct practical answers."
    )

    response = model.generate_content(
        context + message,
        generation_config=genai.GenerationConfig(max_output_tokens=400)
    )

    return response.text


# ===============================
# CHAT UI
# ===============================
def chat_ui(message, history, crop_state):

    if history is None:
        history = []

    if not message:
        return history, "", crop_state

    reply = ask_chatbot(message, crop_state)

    history.append([message, reply])

    return history, "", crop_state


# ===============================
# UI
# ===============================
with gr.Blocks(title="Crop Prediction") as demo:

    gr.Markdown(
        "# 🌾 Smart Crop Identification & Farming Assistant"
    )

    # ✅ SESSION MEMORY
    crop_state = gr.State(None)

    with gr.Row():

        with gr.Column():
            image_input = gr.Image(
                type="filepath",
                label="Upload Crop Image"
            )

            identify_btn = gr.Button("🔍 Identify Crop")

            image_output = gr.Textbox(
                lines=10,
                label="Result"
            )

        with gr.Column():
            chatbot = gr.Chatbot(height=400)
            msg = gr.Textbox(
                placeholder="Ask about soil, disease..."
            )
            send = gr.Button("Send")

    identify_btn.click(
        identify_crop,
        [image_input, crop_state],
        [image_output, crop_state]
    )

    send.click(
        chat_ui,
        [msg, chatbot, crop_state],
        [chatbot, msg, crop_state]
    )

    msg.submit(
        chat_ui,
        [msg, chatbot, crop_state],
        [chatbot, msg, crop_state]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        pwa=True,
        favicon_path="favicon.ico"
    )
