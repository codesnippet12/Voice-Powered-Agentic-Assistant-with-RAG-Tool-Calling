FROM python:3.11-slim

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/hf_cache

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker caching
COPY requirements.txt .

# Install Python packages
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories used by the application
RUN mkdir -p uploads hf_cache data

# Streamlit port
EXPOSE 8501

# Run Streamlit app
CMD ["streamlit", "run", "app_rag.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]