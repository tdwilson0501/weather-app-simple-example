from flask import Flask, render_template, request, jsonify
import requests
import subprocess
import json

app = Flask(__name__)

def get_location_name(lat, lon):
    """
    converts lat/lon to a location name using Nominatim.
    """
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        address = data.get("address", {})
        return (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or data.get("display_name", f"{lat},{lon}")
        )
    except Exception:
        return f"{lat},{lon}"

def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    r = requests.get(url)
    if r.status_code == 200:
        weather = r.json().get("current_weather", {})
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 51: "Light drizzle", 61: "Light rain", 63: "Moderate rain",
            65: "Heavy rain", 71: "Light snow", 73: "Moderate snow", 75: "Heavy snow",
        }
        weather["description"] = weather_codes.get(weather.get("weathercode"), "Unknown")
        return weather
    return {}

def generate_recommendations(weather_data, location):
    """
    Calls a local LLM (through ollama) to get recommendations based on weather + location.
    """
    desc = (
        f"temperature {weather_data.get('temperature', 'unknown')}°C, "
        f"windspeed {weather_data.get('windspeed', 'unknown')} km/h, "
        f"{weather_data.get('description', 'unknown weather')}"
    )
    prompt = (
        f"The current weather in {location} is {desc}. "
        "Recommend three outdoor or indoor activities that someone can enjoy."
    )
    try:
        result = subprocess.run(
            ["ollama", "run", "llama2:7b"],
            capture_output=True, text=True, check=True, encoding='utf-8',
            input=prompt
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error generating recommendations: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_info", methods=["POST"])
def get_info():
    """
    POST with JSON: { "lat": X, "lon": Y }
    1) Reverse geocode lat/lon -> location
    2) Get weather from Open-Meteo
    3) Generate some recommended activities from LLM
    Returns JSON with { weather, recommendations, location }
    """
    data = request.json
    lat = data.get("lat")
    lon = data.get("lon")

    location = get_location_name(lat, lon)

    weather = get_weather(lat, lon)

    recommendations = generate_recommendations(weather, location)

    return jsonify({
        "weather": weather,
        "recommendations": recommendations,
        "location": location
    })

if __name__ == "__main__":
    app.run(debug=True)
