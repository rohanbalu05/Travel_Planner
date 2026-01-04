import re

def parse_daily_cost(day_description: str) -> int:
    """
    Parses a daily cost from the day's description using regex.
    Looks for "Cost: X INR" or similar patterns and extracts the numeric value.
    Returns 0 if no cost is found or cannot be parsed.
    """
    match = re.search(r'Cost:\s*(\d+)\s*(?:INR|USD|EUR)?', day_description, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0

def parse_places_per_day(day_description: str) -> list:
    """
    Parses a list of places from the day's description.
    Looks for "Places: Place A, Place B, Place C." and extracts individual place names.
    Returns an empty list if no places are found.
    """
    match = re.search(r'Places:\s*(.+?)(?:\.|\n|$)', day_description, re.IGNORECASE)
    if match:
        places_str = match.group(1)
        return [p.strip() for p in places_str.split(',') if p.strip()]
    return []

def validate_itinerary(itinerary_text: str, user_budget: str, max_places_per_day: int = 5) -> (bool, str, list):
    """
    Validates the generated itinerary against predefined rules:
    1. Total estimated cost does not exceed the user's budget.
    2. Number of places per day does not exceed `max_places_per_day`.
    3. Each day has a reasonable amount of descriptive content.

    Args:
        itinerary_text (str): The full AI-generated itinerary text.
        user_budget (str): The user's specified budget (e.g., "20000 INR").
        max_places_per_day (int): The maximum allowed places per day.

    Returns:
        tuple: (is_valid: bool, message: str, parsed_days_data: list)
               `parsed_days_data` is a list of dicts, each containing:
               {'day_number': int, 'description': str, 'cost': int, 'places': list}
    """
    lines = itinerary_text.splitlines()
    parsed_days_data = []
    current_day_description = []
    current_day_number = 0
    total_estimated_cost = 0

    # Try to parse user budget (e.g., "20000 INR" -> 20000)
    user_budget_value = 0
    budget_match = re.search(r'(\d+)', user_budget)
    if budget_match:
        user_budget_value = int(budget_match.group(1))

    # Iterate through lines to parse each day's itinerary
    for line in lines:
        day_match = re.match(r'Day\s*(\d+):', line)
        if day_match:
            if current_day_number > 0:
                # Process the description collected for the previous day
                day_desc_str = "\n".join(current_day_description).strip()
                day_cost = parse_daily_cost(day_desc_str)
                day_places = parse_places_per_day(day_desc_str)
                parsed_days_data.append({
                    'day_number': current_day_number,
                    'description': day_desc_str,
                    'cost': day_cost,
                    'places': day_places
                })
                total_estimated_cost += day_cost
            
            current_day_number = int(day_match.group(1))
            current_day_description = [line] # Start new day's description with the "Day X:" line
        elif current_day_number > 0:
            current_day_description.append(line)
    
    # Process the last day after the loop finishes
    if current_day_number > 0:
        day_desc_str = "\n".join(current_day_description).strip()
        day_cost = parse_daily_cost(day_desc_str)
        day_places = parse_places_per_day(day_desc_str)
        parsed_days_data.append({
            'day_number': current_day_number,
            'description': day_desc_str,
            'cost': day_cost,
            'places': day_places
        })
        total_estimated_cost += day_cost

    # If no days were parsed, the itinerary structure is invalid
    if not parsed_days_data:
        return False, "Itinerary structure not recognized. Please ensure it starts with 'Day 1:', 'Day 2:', etc.", []

    # Rule 1: Validate total itinerary does not exceed budget
    if user_budget_value > 0 and total_estimated_cost > user_budget_value:
        return False, f"Total estimated cost ({total_estimated_cost} INR) exceeds your budget ({user_budget_value} INR). Please adjust your budget or regenerate.", []

    # Rule 2: Limit number of places per day
    for day_data in parsed_days_data:
        if len(day_data['places']) > max_places_per_day:
            return False, f"Day {day_data['day_number']} has too many places ({len(day_data['places'])}). Please limit to {max_places_per_day} places per day.", []

    # Rule 3: Enforce reasonable daily schedules (simple check: each day must have some descriptive content)
    for day_data in parsed_days_data:
        # An arbitrary length check to ensure some content exists for the day
        if not day_data['description'] or len(day_data['description'].strip()) < 50:
            return False, f"Day {day_data['day_number']} seems to have an incomplete schedule. Please ensure each day has activities.", []

    return True, "Itinerary validated successfully.", parsed_days_data