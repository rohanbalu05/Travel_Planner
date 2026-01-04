# app_main.py
import os
import re
import json
import math
import requests
from io import BytesIO
from flask import (
    Flask, render_template, request, jsonify, session,
    current_app, send_file, redirect, url_for, flash
)

# Import modular components
from database import db, User, Trip, ItineraryDay, init_db
from auth import register_user, login_user, logout_user, login_required, get_current_user
from ai_service import generate_itinerary_via_groq
from validation import validate_itinerary, parse_daily_cost, parse_places_per_day

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

# Initialize database with the Flask app
init_db(app)

# -----------------------
# Config
# -----------------------
MAX_ITINERARY_CHARS = 100000
LLM_MAX_TOKENS = 4000
LLM_FINISH_TOKENS = 2000

# -----------------------
# Helpers: sanitize, strip asterisks (moved here for general use)
# -----------------------
def strip_asterisks(text: str) -> str:
    """Removes all asterisk characters from a string."""
    if not text:
        return text
    return re.sub(r'\*+', '', text)

def sanitize_itinerary_text(text: str, max_chars=MAX_ITINERARY_CHARS) -> str:
    """
    Sanitizes the itinerary text by removing HTML tags, specific markers,
    non-printable characters, excessive whitespace, and truncating if too long.
    """
    if not text:
        return ""
    text = re.sub(r"&lt;[^&gt;]+&gt;", " ", text) # Remove HTML-like tags
    text = text.replace("```", "` ` `").replace("&lt;&lt;ITINERARY_START&gt;&gt;", " ").replace("&lt;&lt;ITINERARY_END&gt;&gt;", " ")
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", " ", text) # Remove non-printable chars
    text = re.sub(r"[ \t]+", " ", text) # Collapse multiple spaces/tabs
    text = re.sub(r"\n\s*\n+", "\n\n", text) # Collapse multiple blank lines
    if len(text) > max_chars:
        text = text[:max_chars]
    return text

def align_itinerary_text(text: str) -> str:
    """
    Normalizes indentation and bullets for neat display.
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
# PDF generation helper (reportlab) - kept here as it's a specific app feature
# -----------------------
def pdf_from_text_reportlab(text: str, title: str = "Itinerary") -> BytesIO:
    """
    Generates a PDF from plain text using ReportLab.
    """
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
    # Word-wrap text for PDF
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

    # Draw lines onto the PDF, handling page breaks
    for line in lines:
        if y < 60: # Check if close to bottom margin
            c.showPage() # Start new page
            c.setFont("Helvetica", 11)
            y = top_margin
        c.drawString(left_margin, y, line)
        y -= line_height

    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# Authentication Routes
# -----------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handles user registration."""
    if 'user_id' in session: # If already logged in, redirect to home
        return redirect(url_for('home'))
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Basic input validation
        if not username or not email or not password:
            flash("All fields are required for registration.", "error")
            return render_template("index_page.html", active_tab="register")

        success, message = register_user(username, email, password)
        if success:
            flash(message, "success")
            return redirect(url_for('login')) # Redirect to login after successful registration
        else:
            flash(message, "error")
    return render_template("index_page.html", active_tab="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handles user login."""
    if 'user_id' in session: # If already logged in, redirect to home
        return redirect(url_for('home'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Basic input validation
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("index_page.html", active_tab="login")

        success, message = login_user(username, password)
        if success:
            flash(message, "success")
            return redirect(url_for('home')) # Redirect to home after successful login
        else:
            flash(message, "error")
    return render_template("index_page.html", active_tab="login")

@app.route("/logout")
def logout():
    """Handles user logout."""
    logout_user()
    return redirect(url_for('home'))

# -----------------------
# Main Application Routes
# -----------------------

@app.route("/", methods=["GET", "POST"])
@login_required # Only logged-in users can access the home page
def home():
    """
    Handles itinerary generation, display of user's trips, and form submission.
    """
    user = get_current_user()
    if not user: # This check is mostly for type hinting, @login_required should prevent this
        flash("User not found, please log in again.", "error")
        return redirect(url_for('login'))

    # Fetch all trips for the current user to display in the sidebar
    user_trips = Trip.query.filter_by(user_id=user.id).order_by(Trip.created_at.desc()).all()
    
    result_itinerary_text = None
    current_trip_id = request.args.get('trip_id', type=int) # Get trip_id from URL for viewing a specific trip
    current_trip = None

    # If a trip_id is provided in the URL, load that trip's itinerary
    if current_trip_id:
        current_trip = Trip.query.filter_by(id=current_trip_id, user_id=user.id).first()
        if current_trip:
            # Reconstruct itinerary text from DB for display
            itinerary_parts = [day.description for day in current_trip.itinerary_days]
            result_itinerary_text = "\n\n".join(itinerary_parts)
            # Store in session for PDF download and chat modify functionality
            session['last_raw_itinerary'] = result_itinerary_text
            session['current_trip_id'] = current_trip.id # Store current trip ID for chat modify
        else:
            flash("Trip not found or you don't have access.", "error")
            return redirect(url_for('home'))

    if request.method == "POST":
        destination = request.form.get("destination", "").strip()
        budget = request.form.get("budget", "").strip()
        days = request.form.get("days", type=int) # Expect integer
        trip_type = request.form.get("trip_type", "").strip()

        # Input validation for itinerary generation form
        if not destination or not days or days <= 0:
            flash("Destination and number of days (must be positive) are required.", "error")
            return render_template("index_page.html", 
                                   user=user, 
                                   user_trips=user_trips, 
                                   result=result_itinerary_text, 
                                   current_trip=current_trip,
                                   destination=destination,
                                   budget=budget,
                                   days=days,
                                   trip_type=trip_type)

        # Construct prompt for the AI service
        prompt = (
            "Create a concise day-by-day itinerary.\n"
            f"Destination: {destination}\n"
            f"Budget: {budget}\n"
            f"Duration: {days} days\n"
            f"Trip type: {trip_type}\n\n"
            "Include:\n"
            "- Daywise schedule with timings\n"
            "- 2 food suggestions per day with approximate costs (e.g., 'approx 500 INR')\n"
            "- Rough total cost estimate per day (e.g., 'Cost: 2000 INR')\n"
            "- A list of places to visit for each day (e.g., 'Places: Baga Beach, Local Market')\n"
            "- One safety tip\n"
            "Be clear and user-friendly."
        )
        
        raw_ai_response = generate_itinerary_via_groq(prompt)

        # Handle AI API failure
        if raw_ai_response.startswith("ERROR:"):
            flash(f"AI generation failed: {raw_ai_response}", "error")
            return render_template("index_page.html", 
                                   user=user, 
                                   user_trips=user_trips, 
                                   result=result_itinerary_text, 
                                   current_trip=current_trip,
                                   destination=destination,
                                   budget=budget,
                                   days=days,
                                   trip_type=trip_type)

        # Sanitize and clean AI response for validation and display
        sanitized = sanitize_itinerary_text(raw_ai_response)
        cleaned = strip_asterisks(sanitized)
        aligned = align_itinerary_text(cleaned)
        
        # --- Validation Layer ---
        is_valid, validation_message, parsed_days_data = validate_itinerary(aligned, budget, max_places_per_day=5)

        if not is_valid:
            flash(f"Itinerary validation failed: {validation_message}", "error")
            # Display the unvalidated itinerary for user to see what AI generated
            result_itinerary_text = aligned
            session['last_raw_itinerary'] = raw_ai_response # Store raw for potential debug
        else:
            # If valid, save the new trip and its itinerary days to the database
            new_trip = Trip(
                user_id=user.id,
                destination=destination,
                budget=budget,
                days=days,
                trip_type=trip_type
            )
            db.session.add(new_trip)
            db.session.flush() # Get new_trip.id before committing

            for day_data in parsed_days_data:
                itinerary_day = ItineraryDay(
                    trip_id=new_trip.id,
                    day_number=day_data['day_number'],
                    description=day_data['description']
                )
                db.session.add(itinerary_day)
            
            db.session.commit()
            flash("Itinerary generated and saved successfully!", "success")
            # Redirect to view the newly created trip
            return redirect(url_for('home', trip_id=new_trip.id))

    # Render the home page with current user info, trips, and any generated/loaded itinerary
    return render_template("index_page.html", 
                           user=user, 
                           user_trips=user_trips, 
                           result=result_itinerary_text, 
                           current_trip=current_trip,
                           destination=request.form.get("destination", ""), # Pre-fill form if POST failed
                           budget=request.form.get("budget", ""),
                           days=request.form.get("days", 3),
                           trip_type=request.form.get("trip_type", ""))

@app.route("/view_trip/<int:trip_id>")
@login_required
def view_trip(trip_id):
    """
    Displays a specific saved trip's itinerary.
    """
    user = get_current_user()
    # Fetch the trip, ensuring it belongs to the current user
    trip = Trip.query.filter_by(id=trip_id, user_id=user.id).first_or_404()
    
    # Reconstruct itinerary text from DB for display
    itinerary_parts = [day.description for day in trip.itinerary_days]
    result_itinerary_text = "\n\n".join(itinerary_parts)

    # Store in session for PDF download and chat modify
    session['last_raw_itinerary'] = result_itinerary_text
    session['current_trip_id'] = trip.id # Keep track of current trip for chat modify

    # Render the home page with the selected trip's details
    return render_template("index_page.html", 
                           user=user, 
                           user_trips=Trip.query.filter_by(user_id=user.id).order_by(Trip.created_at.desc()).all(),
                           result=result_itinerary_text, 
                           current_trip=trip,
                           destination=trip.destination,
                           budget=trip.budget,
                           days=trip.days,
                           trip_type=trip.trip_type)

@app.route("/delete_trip/<int:trip_id>", methods=["POST"])
@login_required
def delete_trip(trip_id):
    """
    Deletes a specific trip and its associated itinerary days.
    """
    user = get_current_user()
    # Fetch the trip, ensuring it belongs to the current user
    trip = Trip.query.filter_by(id=trip_id, user_id=user.id).first_or_404()

    # Delete associated itinerary days first to maintain referential integrity
    ItineraryDay.query.filter_by(trip_id=trip.id).delete()
    db.session.delete(trip)
    db.session.commit()
    flash(f"Trip to {trip.destination} deleted successfully.", "info")
    return redirect(url_for('home'))


# -----------------------
# External API Routes (Geocoding, Routing)
# -----------------------

def geocode_place_simple(place):
    """
    Geocodes a place name into latitude and longitude using OpenStreetMap Nominatim.
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": place, "format": "json", "limit": 1}
        headers = {"User-Agent": "novatripai/1.0 (+https://example.com)"} # Required User-Agent
        r = requests.get(url, params=params, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        item = data[0]
        return float(item["lat"]), float(item["lon"]), item.get("display_name", place)
    except Exception:
        current_app.logger.exception(f"Geocoding failed for place: {place}")
        return None

@app.route("/route")
def get_route():
    """
    Calculates a driving route between two points using OSRM.
    Accepts lat/lng or addresses for origin and destination.
    """
    origin = request.args.get("origin")
    dest = request.args.get("dest")
    origin_addr = request.args.get("origin_address")
    dest_addr = request.args.get("dest_address")

    try:
        # Geocode addresses if provided instead of lat/lng
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

        # Construct OSRM API URL
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
        current_app.logger.exception("External service error during routing")
        return jsonify({"error": f"External service error: {str(re)}"}), 502
    except Exception as e:
        current_app.logger.exception("Error during routing")
        return jsonify({"error": str(e)}), 500

@app.route("/download_itinerary", methods=["POST"])
@login_required
def download_itinerary():
    """
    Allows downloading the current itinerary as PDF or plain text.
    """
    payload = request.get_json(silent=True) or {}
    posted = payload.get("itinerary_text") or ""
    filename = payload.get("filename") or "itinerary"
    
    # Prefer itinerary from session (which would be the currently displayed/modified one)
    source = session.get("last_raw_itinerary") or posted

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
    
    # Fallback to plain text download if ReportLab is not available or fails
    txt_bytes = BytesIO()
    txt_bytes.write(final_text.encode("utf-8"))
    txt_bytes.seek(0)
    return send_file(txt_bytes, as_attachment=True, download_name=f"{filename}.txt", mimetype="text/plain; charset=utf-8")

# -----------------------
# Chat Modify Itinerary
# -----------------------

def extract_json_from_text(text):
    """
    Attempts to extract a JSON object from a string that might contain extra text.
    """
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
@login_required
def chat_modify_structured():
    """
    Allows users to modify an existing itinerary using natural language instructions
    and updates the database.
    """
    user = get_current_user()
    if not user: # Redundant with @login_required, but good for safety
        return jsonify({"error": "User not logged in."}), 401

    payload = request.get_json(silent=True) or {}
    instr = (payload.get("instruction") or "").strip()
    current_it = (payload.get("current_itinerary") or "").strip()
    
    current_trip_id = session.get('current_trip_id')
    if not current_trip_id:
        return jsonify({"error": "No trip selected for modification. Please view a trip first."}), 400
    
    current_trip = Trip.query.filter_by(id=current_trip_id, user_id=user.id).first()
    if not current_trip:
        return jsonify({"error": "Selected trip not found or unauthorized."}), 403

    if not instr:
        return jsonify({"error": "No instruction provided"}), 400
    if not current_it:
        return jsonify({"error": "No current itinerary provided"}), 400
    
    sanitized_current = sanitize_itinerary_text(current_it)
    sanitized_current = strip_asterisks(sanitized_current)
    
    # Prompt the LLM to modify the itinerary based on user instruction
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
        "- Output must be JSON only (no extra explanation or commentary).\n"
        "- Ensure daily cost estimates and places lists are updated/maintained for each day.\n\n"
        "CURRENT ITINERARY (between markers):\n"
        "&lt;&lt;ITINERARY_START&gt;&gt;\n"
        + sanitized_current
        + "\n&lt;&lt;ITINERARY_END&gt;&gt;\n\n"
        "USER INSTRUCTION:\n"
        + instr
        + "\n\n"
        "Return only valid JSON with keys 'itinerary' and 'places'. Ensure JSON is parseable."
    )
    
    raw_ai_response = generate_itinerary_via_groq(prompt)

    if raw_ai_response.startswith("ERROR:"):
        return jsonify({"error": f"AI modification failed: {raw_ai_response}"}), 500

    parsed = None
    itinerary_text = None
    places = []
    
    # Attempt to parse JSON from AI response
    try:
        if isinstance(raw_ai_response, str):
            parsed = json.loads(raw_ai_response)
        else:
            parsed = None
    except json.JSONDecodeError:
        parsed = extract_json_from_text(raw_ai_response) # Fallback to extract JSON if direct parse fails

    if isinstance(parsed, dict):
        itinerary_text = parsed.get("itinerary") or parsed.get("itinerary_text") or ""
        places_candidate = parsed.get("places") or []
        if isinstance(places_candidate, list):
            places = [str(p).strip() for p in places_candidate if str(p).strip()]
        else:
            places = []
    else:
        # If AI didn't return valid JSON, treat the whole response as itinerary text
        itinerary_text = str(raw_ai_response)
        places = [] # Cannot extract places reliably without JSON

    if not itinerary_text:
        return jsonify({"error": "AI did not return a valid itinerary after modification."}), 500

    itinerary_text = strip_asterisks(itinerary_text)
    itinerary_text = align_itinerary_text(itinerary_text)
    
    # --- Validation Layer for modified itinerary ---
    # Re-validate the modified itinerary against the trip's original budget
    is_valid, validation_message, parsed_days_data = validate_itinerary(itinerary_text, current_trip.budget, max_places_per_day=5)

    if not is_valid:
        # If modified itinerary fails validation, reject it and inform user
        return jsonify({"error": f"Modified itinerary failed validation: {validation_message}"}), 400
    
    # If valid, update the database with the new itinerary
    # Delete old itinerary days associated with this trip
    ItineraryDay.query.filter_by(trip_id=current_trip.id).delete()
    db.session.flush() # Ensure deletions are processed before adding new ones

    # Add new itinerary days based on the validated, modified itinerary
    for day_data in parsed_days_data:
        itinerary_day = ItineraryDay(
            trip_id=current_trip.id,
            day_number=day_data['day_number'],
            description=day_data['description']
        )
        db.session.add(itinerary_day)
    
    db.session.commit()
    
    # Update session with the new itinerary for subsequent downloads/modifications
    session['last_raw_itinerary'] = itinerary_text

    return jsonify({"itinerary_text": itinerary_text, "places": places})

if __name__ == "__main__":
    # Ensure the database is created when running locally
    with app.app_context():
        db.create_all() # Create database tables if they don't exist
    app.run(host="127.0.0.1", port=5000, debug=True)