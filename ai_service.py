# ai_service.py
import os
import re
from flask import current_app
# Optional Groq SDK
try:
    from groq import Groq
except Exception:
    Groq = None

# Groq client (if available + key present)
GROQ_KEY = os.environ.get("GROQ_API_KEY")
if Groq and GROQ_KEY:
    client = Groq(api_key=GROQ_KEY)
else:
    client = None

# Config for LLM interaction
LLM_MAX_TOKENS = 4000
LLM_FINISH_TOKENS = 2000

def looks_truncated(text: str) -> bool:
    """
    Checks if the AI-generated text appears to be truncated.
    """
    if not text:
        return True
    t = text.strip()
    if t.endswith("...") or "[...truncated...]" in t:
        return True
    last = t[-1]
    return last not in ".!?"

def generate_itinerary_via_groq(prompt_text: str) -> str:
    """
    Generates an itinerary using the Groq LLM.
    Includes a fallback mock itinerary if the API key is missing or an error occurs.
    Attempts to complete truncated responses.
    """
    if not client:
        # Dev fallback: return a mock itinerary if Groq client is not available
        return (
            "MOCK ITINERARY (no API key)\n\n"
            "Day 1: Arrival — Walk around the local market; Sunset at Baga Beach.\n"
            " - Breakfast at Fisherman's Cafe (approx 500 INR), Beach Shack.\n"
            " - Cost: 2000 INR. Places: Baga Beach, Local Market.\n\n"
            "Day 2: Fort Aguada, Old Goa; visit Basilica.\n"
            " - Lunch at Cafe Chocolat (approx 700 INR), Local Diner.\n"
            " - Cost: 3000 INR. Places: Fort Aguada, Old Goa, Basilica.\n\n"
            "Tip: Carry water and sunscreen."
        )

    try:
        # Call the Groq API to generate the itinerary
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": (
                    "You are a travel assistant. Provide a detailed day-by-day itinerary including activities, "
                    "food suggestions with approximate costs, a daily total cost estimate, and a list of places to visit for each day. "
                    "Format the output clearly. "
                    "**Crucially, aim to utilize at least 70% of the provided budget, scaling the quality of experiences "
                    "and comfort level (e.g., accommodation, transport, activities) to match the budget.** "
                    "For higher budgets, suggest premium experiences. Do not exceed the total budget."
                    "**IMPORTANT: For each day, explicitly include a line starting with 'Places: ' followed by a comma-separated list of locations.**" # FIX: Added explicit instruction for 'Places:'
                )},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=LLM_MAX_TOKENS
        )
        raw = response.choices[0].message.content if hasattr(response.choices[0].message, 'content') else response.choices[0].text
        raw = raw if isinstance(raw, str) else str(raw)

        # Attempt to finish truncated responses by making a follow-up call
        if looks_truncated(raw):
            try:
                followup_prompt = "The previous itinerary got cut off. Finish the final sentence or paragraph so the itinerary ends cleanly. Ensure all daily costs and places are included."
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
            except Exception as e:
                current_app.logger.debug(f"LLM finish-retry failed: {e}; returning original raw.")
        return raw
    except Exception as e:
        # Log the exception and return an error message if API call fails
        current_app.logger.exception("Groq API error during itinerary generation")
        return f"ERROR: calling Groq API failed: {str(e)}"