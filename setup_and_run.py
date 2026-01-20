"""
Complete Setup and Run Script
Automates the entire project setup and execution
"""

import subprocess
import sys
import os
from pathlib import Path

# --------------------------------------------------
# FORCE UTF-8 (Fix UnicodeEncodeError on Windows)
# --------------------------------------------------
os.environ["PYTHONUTF8"] = "1"

# --------------------------------------------------
# Project Root
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent


# --------------------------------------------------
# Utility Functions
# --------------------------------------------------

def print_header(text):
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70 + "\n")


def run_command(cmd, description):
    """Run a command safely (NO shell=True, Windows-safe)"""
    print(f"📦 {description}...")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True,
            cwd=PROJECT_ROOT
        )
        print(f"✅ {description} - SUCCESS")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print("\nSTDOUT:\n", e.stdout)
        print("\nSTDERR:\n", e.stderr)
        return False


# --------------------------------------------------
# Environment File Check
# --------------------------------------------------

def check_env_file():
    env_file = PROJECT_ROOT / ".env"

    if not env_file.exists():
        print("❌ .env file not found!")

        template = """# Air Pollution Monitoring System - Environment Variables

WAQI_API_TOKEN=your_waqi_token_here
OPENAQ_API_KEY=your_openaq_key_here
MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here
"""
        env_file.write_text(template)
        print(f"✅ Created .env template at {env_file}")
        print("⚠️  Please fill API keys and re-run.")
        return False

    print("✅ .env file found")
    return True


# --------------------------------------------------
# Dependency Installation
# --------------------------------------------------

def install_dependencies():
    print_header("INSTALLING DEPENDENCIES")

    requirements_file = PROJECT_ROOT / "requirements.txt"

    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False

    return run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements_file)
        ],
        "Installing Python packages"
    )


# --------------------------------------------------
# Data Collection (RUN AS MODULES — FIXES src IMPORTS)
# --------------------------------------------------

def collect_data():
    print_header("COLLECTING REAL DATA")

    modules = [
        ("src.data_collection.fetch_openaq_sdk", "OpenAQ data"),
        ("src.data_collection.fetch_waqi", "WAQI data"),
        ("src.data_collection.fetch_era5_weather", "ERA5 weather data"),
    ]

    for module, desc in modules:
        run_command(
            [sys.executable, "-m", module],
            f"Fetching {desc}"
        )

    return run_command(
        [sys.executable, "-m", "src.data_collection.fetch_all_gases"],
        "Running master data orchestrator"
    )


# --------------------------------------------------
# Model Training
# --------------------------------------------------

def train_models():
    print_header("TRAINING ML MODELS")

    module = "src.models.hotspot_detection"

    return run_command(
        [sys.executable, "-m", module],
        "Training ML models"
    )


# --------------------------------------------------
# Backend Server
# --------------------------------------------------

def start_backend():
    print_header("STARTING BACKEND SERVER")

    print("🚀 Starting backend server...")
    print("📍 API: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("\n⚠️  Press CTRL+C to stop\n")

    subprocess.run(
        [sys.executable, "-m", "api.main"],
        cwd=PROJECT_ROOT
    )

    return True


# --------------------------------------------------
# Dashboard Instructions
# --------------------------------------------------

def show_dashboard_instructions():
    print_header("DASHBOARD ACCESS")

    dashboard_dir = PROJECT_ROOT / "dashboard"
    dashboard_file = dashboard_dir / "index.html"

    print("Option 1 (recommended):")
    print(f'  cd "{dashboard_dir}"')
    print("  python -m http.server 8080")
    print("  Open http://localhost:8080\n")

    print("Option 2:")
    print(f"  Open directly: {dashboard_file}")


# --------------------------------------------------
# Main Flow
# --------------------------------------------------

def main():
    print_header("AIR POLLUTION MONITORING SYSTEM")

    input("Press ENTER to continue...")

    if not check_env_file():
        return

    if not install_dependencies():
        print("\n❌ Failed to install dependencies")
        return

    if input("\nCollect real data now? (y/n): ").lower() == "y":
        collect_data()

    if input("\nTrain ML models? (y/n): ").lower() == "y":
        train_models()

    show_dashboard_instructions()

    if input("\nStart backend server now? (y/n): ").lower() == "y":
        start_backend()

    print_header("SETUP COMPLETE")
    print("Your air pollution monitoring system is ready.")


if __name__ == "__main__":
    main()
