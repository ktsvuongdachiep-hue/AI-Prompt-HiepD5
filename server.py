from flask import Flask, request, jsonify
from google import genai
from google.genai import types
import os

app = Flask(__name__)

# Lấy API từ biến môi trường Render
API_KEY = os.getenv("AI_KEY")

client = genai.Client(api_key=API_KEY)

@app.route("/")
def home():
    return "AI Prompt Server Running"


@app.route("/generate", methods=["POST"])
def generate():

    try:

        base_file = request.files["base"]
        ref_file = request.files["ref"]

        base_bytes = base_file.read()
        ref_bytes = ref_file.read()

        prompt = """
You are an architectural visualization prompt engineer.

Image1 = building model.
Image2 = render reference.

Return:

PROMPT:
<english>

VIETNAMESE:
<vietnamese>
"""

        res = client.models.generate_content(

            model="gemini-2.5-flash",

            contents=[

                prompt,

                types.Part.from_bytes(
                    data=base_bytes,
                    mime_type="image/jpeg"
                ),

                types.Part.from_bytes(
                    data=ref_bytes,
                    mime_type="image/jpeg"
                )
            ]
        )

        return jsonify({
            "text": res.text
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
