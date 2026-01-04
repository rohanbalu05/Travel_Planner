"""
Test script to verify NovaTrip AI setup
This simulates what happens after running setup.bat on Windows
"""

import sys
import os

print("=" * 60)
print("NovaTrip AI - Setup Verification")
print("=" * 60)
print()

# Check Python version
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print()

# Check if app_main.py exists
if os.path.exists("app_main.py"):
    print("✓ app_main.py found")
else:
    print("✗ app_main.py not found")
    sys.exit(1)

# Check if requirements.txt exists
if os.path.exists("requirements.txt"):
    print("✓ requirements.txt found")
    with open("requirements.txt", "r") as f:
        print(f"  Dependencies: {len(f.readlines())} packages")
else:
    print("✗ requirements.txt not found")
    sys.exit(1)

# Check if templates exist
if os.path.exists("templates_main/auth.html"):
    print("✓ auth.html template found")
else:
    print("✗ auth.html template not found")

if os.path.exists("templates_main/home.html"):
    print("✓ home.html template found")
else:
    print("✗ home.html template not found")

# Check Python modules
print()
print("Checking required Python modules:")
modules = ['flask', 'groq', 'requests', 'flask_sqlalchemy', 'werkzeug', 'reportlab']
all_installed = True

for module in modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError:
        print(f"  ✗ {module} (will be installed by setup.bat)")
        all_installed = False

print()
print("=" * 60)

if not all_installed:
    print("NOTE: Some modules not installed yet")
    print("This is normal before running: pip install -r requirements.txt")
    print()
    print("After installation, all modules will be available")
else:
    print("✓ All modules installed!")
    print()
    print("Testing application import...")
    try:
        from app_main import app
        print("✓ Application imports successfully!")
        print("✓ Ready to run: python app_main.py")
    except Exception as e:
        print(f"✗ Error importing app: {e}")

print("=" * 60)
