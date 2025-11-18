# app_main.py  — Full app (cleaned) with Groq-safe fallback, route, pinpoints, and strict structured chat modify
import os
import re
import json
import requests
from flask import Flask, render_template, request, jsonify, session, current_app

# Optional Groq SDK
try:
    from groq import Groq
except Exception:
    Groq = None

app = Flask(__name__, template_folder="templates_main")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Groq client (if available + key present)
GROQ_KEY = os.environ.get("GROQ_API_KEY")
if Groq and GROQ_KEY:
    client = Groq(api_key=GROQ_KEY)
else:
    client = None

def generate_itinerary_via_groq(prompt_text):
    """
    Call Groq (if available) or return a mock. Returns raw text.
    """
    if not client:
        # Basic mock - useful for dev and testing
        return (
            "MOCK ITINERARY (no API key)\n\n"
            "Day 1: Arrival — Walk around the local market; Sunset at Baga Beach.\n"
            "Food: Fisherman's Cafe, Beach Shack.\n\n"
            "Day 2: Fort Aguada, Old Goa; visit Basilica.\n"
            "Food: Cafe Chocolat, Local Diner.\n\n"
            "Tip: Carry water and sunscreen."
        )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a travel assistant."},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"ERROR: calling Groq API failed: {str(e)}"


# -----------------------
# Basic home / form
# -----------------------
@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    destination = ""
    if request.method == "POST":
        destination = request.form.get("destination", "").strip()
        budget = request.form.get("budget", "").strip()
        days = request.form.get("days", "").strip()
        trip_type = request.form.get("trip_type", "").strip()

        prompt = (
            "Create a concise day-by-day itinerary.\n"
            f"Destination: {destination}\n"
            f"Budget: {budget}\n"
            f"Duration: {days} days\n"
            f"Trip type: {trip_type}\n\n"
            "Include:\n"
            "- Daywise schedule with timings\n"
            "- 2 food suggestions per day\n"
            "- Rough cost estimate per day\n"
            "- One safety tip\n"
            "Be clear and user-friendly."
        )
        result = generate_itinerary_via_groq(prompt)

    return render_template("index_page.html", result=result, destination=destination)


# -----------------------
# Geocoding & routing helpers
# -----------------------
def geocode_address(address):
    """Geocode an address -> (lat, lon, display_name) using Nominatim (server-side)."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    headers = {"User-Agent": "novatripai/1.0 (+https://example.com)"}
    r = requests.get(url, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", address)


@app.route("/route")
def get_route():
    """
    Query params:
      origin=lat,lng  OR origin_address=...
      dest=lat,lng    OR dest_address=...
    Returns GeoJSON Feature (LineString) with properties distance (m) and duration (s)
    """
    origin = request.args.get("origin")
    dest = request.args.get("dest")
    origin_addr = request.args.get("origin_address")
    dest_addr = request.args.get("dest_address")

    try:
        # resolve addresses if given
        if origin_addr and not origin:
            g = geocode_address(origin_addr)
            if not g:
                return jsonify({"error": "Could not geocode origin address"}), 400
            origin = f"{g[0]},{g[1]}"
        if dest_addr and not dest:
            g = geocode_address(dest_addr)
            if not g:
                return jsonify({"error": "Could not geocode destination address"}), 400
            dest = f"{g[0]},{g[1]}"

        if not origin or not dest:
            return jsonify({"error": "Provide origin and dest (lat,lng) or origin_address and dest_address"}), 400

        def parse_latlng(s):
            parts = s.split(",")
            if len(parts) != 2:
                raise ValueError("Invalid lat,lng format")
            return float(parts[0].strip()), float(parts[1].strip())

        o_lat, o_lng = parse_latlng(origin)
        d_lat, d_lng = parse_latlng(dest)

        # OSRM expects lon,lat and semi-colon separated pairs
        osrm_coords = f"{o_lng},{o_lat};{d_lng},{d_lat}"
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{osrm_coords}"
        params = {"overview": "full", "geometries": "geojson", "steps": "false"}
        r = requests.get(osrm_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if "routes" not in data or len(data["routes"]) == 0:
            return jsonify({"error": "No route found"}), 404

        route = data["routes"][0]
        geometry = route["geometry"]  # GeoJSON LineString
        distance = route.get("distance")  # meters
        duration = route.get("duration")  # seconds

        result = {
            "type": "Feature",
            "properties": {"distance": distance, "duration": duration},
            "geometry": geometry
        }
        return jsonify(result)

    except requests.exceptions.RequestException as re:
        return jsonify({"error": f"External service error: {str(re)}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------
# Pinpoints endpoint: accepts either "text" or "places" list
# -----------------------
def extract_place_candidates(itinerary_text, max_candidates=20):
    """
    Lightweight heuristic to extract place-name candidates from itinerary text.
    Finds sequences of 1-5 Titlecase words.
    """
    if not itinerary_text:
        return []

    text = itinerary_text.replace("—", " ").replace("–", " ").replace("/", " ")
    pattern = re.compile(r'\b([A-Z][a-zA-Z]{1,}(?:\s+[A-Z][a-zA-Z]{1,}){0,4})\b')
    matches = pattern.findall(text)

    blacklist = {"Day", "Days", "Tip", "Tips", "Include", "Duration", "Budget", "Cost", "Morning", "Evening", "Food", "Daywise"}
    seen = set()
    candidates = []
    for m in matches:
        m = m.strip()
        if len(m) < 2:
            continue
        if any(token.isdigit() for token in m.split()):
            continue
        if m in blacklist:
            continue
        key = m.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(m)
        if len(candidates) >= max_candidates:
            break
    return candidates


def geocode_place(place):
    """Geocode a place name -> (lat, lon, display_name) or None"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": place, "format": "json", "limit": 1}
        headers = {"User-Agent": "novatripai/1.0 (+https://example.com)"}
        r = requests.get(url, params=params, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        item = data[0]
        return float(item["lat"]), float(item["lon"]), item.get("display_name", place)
    except Exception:
        return None


@app.route("/pinpoints", methods=["POST"])
def pinpoints():
    """
    Accepts JSON:
      - { "text": "<itinerary text>", "limit": <int> }
      OR
      - { "places": ["Place 1", "Place 2"], "limit": <int> }
    Returns GeoJSON FeatureCollection of geocoded points.
    """
    payload = request.get_json(silent=True) or {}
    limit = int(payload.get("limit", 12) or 12)

    # if places array provided, geocode those directly
    places = payload.get("places")
    candidates = []
    if places and isinstance(places, list):
        candidates = [p for p in places if isinstance(p, str) and p.strip()]
    else:
        text = payload.get("text", "") or ""
        if not text.strip():
            return jsonify({"error": "No itinerary text or places provided"}), 400
        candidates = extract_place_candidates(text, max_candidates=limit*2)

    features = []
    count = 0
    for cand in candidates:
        if count >= limit:
            break
        g = geocode_place(cand)
        if not g:
            current_app.logger.debug(f"Geocode failed for: {cand}")
            continue
        lat, lon, display = g
        feat = {
            "type": "Feature",
            "properties": {"name": cand, "display_name": display},
            "geometry": {"type": "Point", "coordinates": [lon, lat]}
        }
        features.append(feat)
        count += 1

    result = {"type": "FeatureCollection", "features": features, "meta": {"candidates_examined": len(candidates)}}
    return jsonify(result)


# -----------------------
# Structured chat modify endpoint (STRICT JSON output)
# -----------------------
def extract_json_from_text(text):
    """
    Try to extract the first JSON object/array from a raw text (model output).
    """
    if not isinstance(text, str):
        return None
    # naive attempt: find first '{' or '[' and attempt json.loads progressively
    idx = text.find('{')
    idx2 = text.find('[')
    if idx == -1 and idx2 == -1:
        return None
    start = idx if (idx != -1) else idx2
    # try to find matching braces by scanning from the end backwards
    for end in range(len(text), start, -1):
        try:
            candidate = text[start:end]
            return json.loads(candidate)
        except Exception:
            continue
    return None


# defensive sanitizer for itinerary text before inserting into prompt
MAX_ITINERARY_CHARS = 6000


def sanitize_itinerary_text(text: str, max_chars=MAX_ITINERARY_CHARS) -> str:
    if not text:
        return ""
    # remove simple HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # replace problematic sequences
    text = text.replace("```", "` ` `").replace("<<ITINERARY_START>>", " ").replace("<<ITINERARY_END>>", " ")
    # strip control chars except newline/tab
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", " ", text)
    # collapse multiple spaces/newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    # truncate head+tail if too long
    if len(text) > max_chars:
        half = max_chars // 2
        head = text[:half]
        tail = text[-half:]
        text = head + "\n\n[...truncated...]\n\n" + tail
    return text


@app.route("/chat_modify_structured", methods=["POST"])
def chat_modify_structured():
    """
    Strict server implementation: always returns JSON:
      { "itinerary_text": "<full itinerary text (ALL DAYS)>", "places": [ ... ] }

    Accepts JSON: { "instruction": "<user text>", "current_itinerary": "<full itinerary text>" }
    """
    payload = request.get_json(silent=True) or {}
    instr = (payload.get("instruction") or "").strip()
    current = (payload.get("current_itinerary") or "").strip()

    if not instr:
        return jsonify({"error": "No instruction provided"}), 400
    if not current:
        return jsonify({"error": "No current itinerary provided"}), 400

    # sanitize but keep as much as possible so model has full context
    sanitized_current = sanitize_itinerary_text(current)

    # Strong explicit prompt: MUST return the full updated itinerary (all days).
    prompt = (
        "You are a travel itinerary assistant. You are given the user's current itinerary "
        "and a user instruction describing edits. **You MUST return only a single valid JSON object** "
        "with exactly two keys:\n"
        '1) "itinerary" : the full updated itinerary as plain human-readable text (MUST include every day from Day 1 to the final day; '
        "if the instruction only changes one day, keep all other days unchanged and include them in the output)\n"
        '2) "places" : an array of place names (strings) that appear in the updated itinerary and should be pinned on a map\n\n'
        "Important requirements:\n"
        "- Do not return only the modified day. Return the COMPLETE itinerary containing all days.\n"
        "- Preserve the original day numbering unless the user specifically asks to add/remove days.\n"
        "- Output must be JSON only (no extra explanation or commentary).\n\n"
        "CURRENT ITINERARY (between markers):\n"
        "<<ITINERARY_START>>\n"
        + sanitized_current
        + "\n<<ITINERARY_END>>\n\n"
        "USER INSTRUCTION:\n"
        + instr
        + "\n\n"
        "Return only valid JSON with keys 'itinerary' and 'places'. Ensure JSON is parseable."
    )

    raw = generate_itinerary_via_groq(prompt)

    parsed = None
    itinerary_text = None
    places = []

    try:
        if isinstance(raw, str):
            parsed = json.loads(raw)
        else:
            parsed = None
    except Exception:
        parsed = None

    if parsed is None:
        parsed = extract_json_from_text(raw)

    if isinstance(parsed, dict):
        itinerary_text = parsed.get("itinerary") or parsed.get("itinerary_text") or ""
        places_candidate = parsed.get("places") or []
        if isinstance(places_candidate, list):
            places = [str(p).strip() for p in places_candidate if str(p).strip()]
        else:
            places = []
    else:
        # Attempt one more unquote step if raw contains quoted JSON
        if isinstance(raw, str):
            trimmed = raw.strip()
            if (trimmed.startswith('"') and trimmed.endswith('"')) or (trimmed.startswith("'") and trimmed.endswith("'")):
                try:
                    candidate = json.loads(trimmed)
                    if isinstance(candidate, dict):
                        itinerary_text = candidate.get("itinerary") or candidate.get("itinerary_text") or ""
                        places_candidate = candidate.get("places") or []
                        if isinstance(places_candidate, list):
                            places = [str(p).strip() for p in places_candidate if str(p).strip()]
                except Exception:
                    pass

    # Final fallback: use raw as itinerary_text but still return strict JSON
    if not itinerary_text:
        if isinstance(raw, (dict, list)):
            itinerary_text = json.dumps(raw, indent=2)
        else:
            itinerary_text = str(raw)
        places = []

    itinerary_text = str(itinerary_text)
    places = [str(p) for p in (places or [])]

    try:
        hist = session.get("itinerary_history", [])
        hist.append({"instruction": instr, "result": itinerary_text})
        session["itinerary_history"] = hist[-10:]
    except Exception:
        current_app.logger.debug("Could not save itinerary history in session.")

    return jsonify({"itinerary_text": itinerary_text, "places": places})



if __name__ == "__main__":
    # Dev server only: bind to localhost
    app.run(host="127.0.0.1", port=5000, debug=True)
