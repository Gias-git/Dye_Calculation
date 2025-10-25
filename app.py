from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- OpenRouter client configuration ---
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found. Please set it in your .env file.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

extra_headers = {
    "HTTP-Referer": os.getenv("YOUR_SITE_URL"),
    "X-Title": os.getenv("YOUR_SITE_NAME"),
}

# --- Flask setup ---
app = Flask(__name__)

@app.route("/")
def index():
    """Render the main input form."""
    return render_template("index.html")

@app.route("/calculate_recipe", methods=["POST"])
def calculate_recipe():
    """
    Receives fabric details, asks the AI for multiple dye recipes,
    and returns structured JSON data.
    """
    try:
        data = request.get_json()
        target_color = data.get("target_color")
        fabric_type = data.get("fabric_type")
        dyeing_system = data.get("dyeing_system")

        if not all([target_color, fabric_type, dyeing_system]):
            return jsonify({"error": "All fields are required."}), 400

        # Construct AI prompt
        prompt = f"""
        You are a master dye chemist.
        Given the following details, return a JSON array containing multiple dye recipes.
        Each recipe must include:
        - fabric_type
        - target_color
        - dyeing_system
        - dye_percentage (in %)
        - chemicals (name and dosage)
        - temperature (°C)
        - time (minutes)
        - step_by_step_instructions

        Return ONLY valid JSON (no markdown, no explanations).

        Example JSON format:
        [
          {{
            "fabric_type": "Cotton",
            "target_color": "Sky Blue",
            "dyeing_system": "Reactive",
            "dye_percentage": "2%",
            "chemicals": [
              {{"name": "Salt", "dosage": "40 g/L"}},
              {{"name": "Soda Ash", "dosage": "10 g/L"}}
            ],
            "temperature": "60°C",
            "time": "40 min",
            "step_by_step_instructions": [
              "Dissolve dye in warm water",
              "Add salt gradually",
              "Raise temperature to 60°C",
              "Add soda ash and continue dyeing for 40 minutes"
            ]
          }}
        ]

        Now generate recipes for the given data:
        Target Color: {target_color}
        Fabric Type: {fabric_type}
        Dyeing System: {dyeing_system}
        """

        # Call OpenRouter API
        completion = client.chat.completions.create(
            extra_headers=extra_headers,
            model="deepseek/deepseek-chat-v3.1:free",
            messages=[
                {"role": "system", "content": "You return only JSON, no explanations."},
                {"role": "user", "content": prompt},
            ],
        )

        raw_response = completion.choices[0].message.content.strip()

        # Try to parse as JSON safely
        try:
            recipes = json.loads(raw_response)
        except json.JSONDecodeError:
            recipes = {"raw_text": raw_response, "warning": "Response not valid JSON"}

        return jsonify({"recipes": recipes})

    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
