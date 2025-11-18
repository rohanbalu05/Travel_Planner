# app.py   <-- place at project root
import os
# import the Flask app object from your existing module
# adjust the module name if your file is named differently
from app_main import app

# Vercel expects the variable to be named `app` (or `application`) at module level.
# We already imported it as `app`, so nothing else is needed.
# But keep a runnable guard so you can run locally with `python app.py`.
if __name__ == "__main__":
    # Use PORT env (Vercel sets it for runtime) or default 5000 locally
    port = int(os.environ.get("PORT", 5000))
    # bind to 0.0.0.0 for container hosting
    app.run(host="0.0.0.0", port=port, debug=True)
