# ─── Multi-Stage Dockerfile ──────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Generate data and seed DB at build time
RUN python scripts/generate_data.py && python scripts/seed_db.py

# Expose ports for API and Dashboard
EXPOSE 8000 8501

# Default: start both services (use docker-compose for separate containers)
CMD bash -c "uvicorn app.main:app --host 0.0.0.0 --port 8000 & streamlit run streamlit_app/dashboard.py --server.port 8501 --server.address 0.0.0.0"
