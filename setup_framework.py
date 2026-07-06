#!/usr/bin/env python3
"""Quick setup script for the AI Automation Framework."""

import subprocess
import sys
from pathlib import Path


def main():
    framework_dir = Path(__file__).parent.resolve()
    print(f"📦 Setting up AI Automation Framework in: {framework_dir}")

    # 1. Create virtual environment
    venv_dir = framework_dir / ".venv"
    if not venv_dir.exists():
        print("🔨 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    else:
        print("✅ Virtual environment already exists")

    # 2. Determine pip path
    if sys.platform == "win32":
        pip = str(venv_dir / "Scripts" / "pip")
        python = str(venv_dir / "Scripts" / "python")
    else:
        pip = str(venv_dir / "bin" / "pip")
        python = str(venv_dir / "bin" / "python")

    # 3. Install dependencies
    print("📥 Installing dependencies...")
    subprocess.run([pip, "install", "--upgrade", "pip"], check=True)
    subprocess.run([pip, "install", "-r", str(framework_dir / "requirements.txt")], check=True)

    # 4. Install Playwright browsers (web only)
    print("🌐 Installing Playwright browsers...")
    try:
        subprocess.run([python, "-m", "playwright", "install", "chromium"], check=True)
    except subprocess.CalledProcessError:
        print("⚠️  Playwright browser install skipped (not needed for mobile-only projects)")

    # 5. Create default directories
    for d in ["reports/screenshots", "reports/sources", "reports/healing", "logs"]:
        (framework_dir / d).mkdir(parents=True, exist_ok=True)

    print()
    print("✅ Setup complete!")
    print()
    print(f"   Activate:  source {venv_dir}/bin/activate")
    print(f"   Run tests: pytest tests/web/ --platform web -v")
    print()


if __name__ == "__main__":
    main()
