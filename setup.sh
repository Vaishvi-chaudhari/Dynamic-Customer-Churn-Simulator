#!/usr/bin/env bash
# ─── One-Command Setup ───────────────────────────────────────────────────────
# Run from the project root: bash setup.sh

set -e

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "📊 Generating synthetic dataset..."
python scripts/generate_data.py

echo ""
echo "🗃️ Seeding database..."
python scripts/seed_db.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the dashboard:"
echo "  streamlit run streamlit_app/dashboard.py"
echo ""
echo "To start the API:"
echo "  uvicorn app.main:app --reload"
