# AI Rules for NovaTrip AI

This document outlines the core technologies and guidelines for library usage within the NovaTrip AI application.

## 🚀 Tech Stack

*   **Python 3.x**: The primary language for all backend logic and server-side operations.
*   **Flask**: A lightweight Python web framework used for handling HTTP requests, routing, and rendering templates.
*   **Groq LLaMA 3.1**: The AI model integrated for generating travel itineraries based on user input.
*   **Jinja2 Templating**: Used for server-side rendering of dynamic HTML content.
*   **Vanilla HTML/CSS**: The frontend is built using standard HTML and custom CSS for styling, ensuring a clean and responsive user interface.
*   **Leaflet.js**: A lightweight JavaScript library for interactive maps, used to display routes and locations.
*   **OpenStreetMap (Nominatim & OSRM)**: External services used for geocoding (converting addresses to coordinates) and routing (calculating travel paths).
*   **ReportLab**: An optional Python library for generating PDF versions of the itineraries.
*   **Requests**: A Python library for making HTTP requests to external APIs (e.g., geocoding, routing).

## 🛠️ Library Usage Rules

To maintain consistency and efficiency, please adhere to the following library usage guidelines:

*   **Backend (Python)**:
    *   **Web Framework**: Use `Flask` for all web server functionalities, routing, and handling requests/responses.
    *   **AI Integration**: Interact with Groq LLaMA models exclusively through the `groq` SDK (if available and configured).
    *   **External APIs**: Use the `requests` library for all external HTTP calls, such as to Nominatim for geocoding or OSRM for routing.
    *   **PDF Generation**: Utilize `reportlab` for generating PDF files. If `reportlab` is not available, ensure a fallback to plain text download is implemented.
    *   **General Utilities**: Standard Python libraries (`os`, `re`, `json`, `math`, `io`) are permitted for common utility tasks.

*   **Frontend (HTML/CSS/JavaScript)**:
    *   **Templating**: All dynamic HTML rendering must be done using Jinja2 templates on the server-side.
    *   **Styling**: All styling should be implemented using custom CSS directly within `index_page.html`. Avoid introducing external CSS frameworks unless explicitly requested.
    *   **Mapping**: Use `Leaflet.js` for all interactive map displays, including adding markers and drawing routes.
    *   **Client-Side Interactivity**: Implement client-side logic and interactivity using vanilla JavaScript. Avoid introducing large frontend frameworks (e.g., React, Vue, Angular) unless specifically requested.
    *   **Geocoding/Routing**: Frontend map interactions requiring geocoding or routing should communicate with the Flask backend endpoints (`/route`) rather than directly calling external services.