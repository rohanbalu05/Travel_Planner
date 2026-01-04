# app_main.py
# Full Flask app — sanitize, remove markdown asterisks, align itinerary bullets for neat display,
# keep raw output in session, auto-finish truncated LLM responses, PDF download fallback.
import os
import re
import json
import math
import requests
from io import BytesIO
from flask import (
    Flask, render_template, request, jsonify, session,
    current_app, send_file
)

# Optional Groq SDK
try:
    from groq import Groq
except Exception:
    Groq = None

# Optional PDF library
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

app = Flask(__name__, template_folder="templates_main")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Groq client (if available + key present)
GROQ_KEY = os.environ.get("GROQ_API_KEY")
# --- ADDED DEBUG LINE ---
print(f"DEBUG: GROQ_API_KEY read by app: {'[KEY FOUND]' if GROQ_KEY else '[KEY NOT FOUND]'}")
# --- END DEBUG LINE ---
if Groq and GROQ_KEY:
    client = Groq(api_key=GROQ_KEY)
else:
    client = None

# -----------------------
# Config
# -----------------------
MAX_ITINERARY_CHARS = 100000   # raised limit to avoid early truncation
LLM_MAX_TOKENS = 4000         # larger token budget for initial generation
LLM_FINISH_TOKENS = 2000       # tokens for finish-retry when truncated

# -----------------------
# Helpers: sanitize, strip asterisks
# -----------------------
def strip_asterisks(text: str) -> str:
    if not text:
        return text
    return re.sub(r'\*+', '', text)

def sanitize_itinerary_text(text: str, max_chars=MAX_ITINERARY_CHARS) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("```", "` ` `").replace("<<ITINERARY_START>>", " ").replace("<<ITINERARY_END>>", " ")
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    if len(text) > max_chars:
        text = text[:max_chars]
    return text

def looks_truncated(text: str) -> bool:
    if not text:
        return True
    t = text.strip()
    if t.endswith("...") or "[...truncated...]" in t:
        return True
    last = t[-1]
    return last not in ".!?"

# -----------------------
# Align itinerary text for neat selection/display
# -----------------------
def align_itinerary_text(text: str) -> str:
    """
    Normalize indentation and bullets for neat display.
    - Removes leading indentation.
    - Converts '-', '*' bullets (and repeated bullets) to a single '• '.
    - Collapses excessive spaces.
    - Preserves paragraph breaks.
    """
    if not text:
        return text
    lines = text.splitlines()
    out_lines = []
    for line in lines:
        # preserve empty lines
        if not line.strip():
            out_lines.append('')
            continue

        # remove leading whitespace
        s = re.sub(r'^[ \t]+', '', line)

        # replace runs of bullet characters or leading hyphen/asterisk sequences with a single bullet "• "
        s = re.sub(r'^[\-\*\u2022\•\s]{1,6}', lambda m: '• ' if re.search(r'[\-\*\u2022\•]', m.group(0)) else '', s)

        # ensure single spaces between words
        s = re.sub(r'[ \t]{2,}', ' ', s)

        # trim trailing spaces
        s = s.rstrip()

        out_lines.append(s)

    # join and also collapse accidental multiple blank lines to max two
    joined = '\n'.join(out_lines)
    joined = re.sub(r'\n{3,}', '\n\n', joined)
    return joined

# -----------------------
# LLM wrapper with finish-retry (same as before)
# -----------------------
def generate_itinerary_via_groq(prompt_text: str) -> str:
    if not client:
        # Dev fallback
        return (
            "MOCK ITINERARY (no API key)\n\n"
            "Day 1: Arrival — Walk around the local market; Sunset at Baga Beach.\n"
            " - Breakfast at Fisherman's Cafe, Beach Shack.\n\n"
            "Day 2: Fort Aguada, Old Goa; visit Basilica.\n"
            " - Lunch at Cafe Chocolat, Local Diner.\n\n"
            "Tip: Carry water and sunscreen."
        )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a travel assistant."},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=LLM_MAX_TOKENS
        )
        raw = response.choices[0].message.content if hasattr(response.choices[0].message, 'content') else response.choices[0].text
        raw = raw if isinstance(raw, str) else str(raw)
        if looks_truncated(raw):
            try:
                followup_prompt = "The previous itinerary got cut off. Finish the final sentence or paragraph so the itinerary ends cleanly."
                follow = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role":"system","content":"You are a travel assistant."},
                        {"role":"user","content": followup_prompt},
                        {"role":"assistant","content": raw}
                    ],
                    max_tokens=LLM_FINISH_TOKENS
                )
                extra = follow.choices[0].message.content if hasattr(follow.choices[0].message,'content') else follow.choices[0].text
                extra = extra if isinstance(extra, str) else str(extra)
                if extra and len(extra.strip()) > 0:
                    raw = raw.rstrip() + "\n\n" + extra.strip()
            except Exception:
                current_app.logger.debug("LLM finish-retry failed; returning original raw.")
        return raw
    except Exception as e:
        current_app.logger.exception("Groq API error")
        return f"ERROR: calling Groq API failed: {str(e)}"

# -----------------------
# PDF generation helper (reportlab)
# -----------------------
def pdf_from_text_reportlab(text: str, title: str = "Itinerary") -> BytesIO:
    buffer = BytesIO()
    page_width, page_height = A4
    c = rl_canvas.Canvas(buffer, pagesize=A4)
    left_margin = 40
    top_margin = page_height - 40
    max_width = page_width - 2 * left_margin
    line_height = 14
    y = top_margin

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, title)
    y -= (line_height * 1.5)
    c.setFont("Helvetica", 11)

    lines = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split()
        current = ""
        for w in words:
            test = (current + " " + w).strip() if current else w
            width = stringWidth(test, "Helvetica", 11)
            if width <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

    for line in lines:
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = top_margin
        c.drawString(left_margin, y, line)
        y -= line_height

    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# Routes
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
        raw = generate_itinerary_via_groq(prompt)
        try:
            session['last_raw_itinerary'] = raw
        except Exception:
            current_app.logger.debug("Unable to store itinerary in session.")
        sanitized = sanitize_itinerary_text(raw)
        cleaned = strip_asterisks(sanitized)
        aligned = align_itinerary_text(cleaned)
        result = aligned

    return render_template("index_page.html", result=result, destination=destination)

# route & download endpoints (same as previous version)
def geocode_place_simple(place):
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

@app.route("/route")
def get_route():
    origin = request.args.get("origin")
    dest = request.args.get("dest")
    origin_addr = request.args.get("origin_address")
    dest_addr = request.args.get("dest_address")

    try:
        if origin_addr and not origin:
            g = geocode_place_simple(origin_addr)
            if not g:
                return jsonify({"error": "Could not geocode origin address"}), 400
            origin = f"{g[0]},{g[1]}"
        if dest_addr and not dest:
            g = geocode_place_simple(dest_addr)
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

        osrm_coords = f"{o_lng},{o_lat};{d_lng},{d_lat}"
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{osrm_coords}"
        params = {"overview": "full", "geometries": "geojson", "steps": "false"}
        r = requests.get(osrm_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if "routes" not in data or len(data["routes"]) == 0:
            return jsonify({"error": "No route found"}), 404

        route = data["routes"][0]
        geometry = route["geometry"]
        distance = route.get("distance")
        duration = route.get("duration")

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

@app.route("/download_itinerary", methods=["POST"])
def download_itinerary():
    payload = request.get_json(silent=True) or {}
    posted = payload.get("itinerary_text") or ""
    filename = payload.get("filename") or "itinerary"
    source = posted or session.get("last_raw_itinerary") or ""
    if posted and looks_truncated(posted):
        raw = session.get("last_raw_itinerary")
        if raw and len(raw) > len(posted):
            source = raw
    if not source:
        return jsonify({"error": "No itinerary available for download"}), 400
    filename = re.sub(r'[^A-Za-z0-9_\-\. ]+', '_', filename).strip()
    if not filename:
        filename = "itinerary"
    final_text = str(source)
    if REPORTLAB_AVAILABLE:
        try:
            pdf_buf = pdf_from_text_reportlab(final_text, title=filename)
            return send_file(pdf_buf, as_attachment=True, download_name=f"{filename}.pdf", mimetype="application/pdf")
        except Exception:
            current_app.logger.exception("ReportLab PDF generation failed; falling back to TXT.")
    txt_bytes = BytesIO()
    txt_bytes.write(final_text.encode("utf-8"))
    txt_bytes.seek(0)
    return send_file(txt_bytes, as_attachment=True, download_name=f"{filename}.txt", mimetype="text/plain; charset=utf-8")

# Chat modify structured (keeps prior behaviour)
def extract_json_from_text(text):
    if not isinstance(text, str):
        return None
    idx = text.find('{')
    idx2 = text.find('[')
    if idx == -1 and idx2 == -1:
        return None
    start = idx if (idx != -1) else idx2
    for end in range(len(text), start, -1):
        try:
            candidate = text[start:end]
            return json.loads(candidate)
        except Exception:
            continue
    return None

@app.route("/chat_modify_structured", methods=["POST"])
def chat_modify_structured():
    payload = request.get_json(silent=True) or {}
    instr = (payload.get("instruction") or "").strip()
    current_it = (payload.get("current_itinerary") or "").strip()
    if not instr:
        return jsonify({"error": "No instruction provided"}), 400
    if not current_it:
        return jsonify({"error": "No current itinerary provided"}), 400
    sanitized_current = sanitize_itinerary_text(current_it)
    sanitized_current = strip_asterisks(sanitized_current)
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
    if not itinerary_text:
        if isinstance(raw, (dict, list)):
            itinerary_text = json.dumps(raw, indent=2)
        else:
            itinerary_text = str(raw)
        places = []
    itinerary_text = str(itinerary_text)
    itinerary_text = strip_asterisks(itinerary_text)
    itinerary_text = align_itinerary_text(itinerary_text)
    places = [str(p) for p in (places or [])]
    try:
        hist = session.get("itinerary_history", [])
        hist.append({"instruction": instr, "result": itinerary_text})
        session["itinerary_history"] = hist[-10:]
    except Exception:
        current_app.logger.debug("Could not save itinerary history in session.")
    return jsonify({"itinerary_text": itinerary_text, "places": places})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)