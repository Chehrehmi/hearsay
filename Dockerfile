# Lightweight Python 3.11 base image
FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Install curl (for healthchecks) and basic build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU first to keep image lightweight (avoids 3GB+ CUDA wheels)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download required spaCy NLP model for sentence decomposition
RUN python -m spacy download en_core_web_sm

# Copy project source code
COPY . .

# Install hearsay in editable mode so imports resolve cleanly
# RUN pip install --no-cache-dir -e .

# Expose Gateway (8000) and Dashboard (8501)
EXPOSE 8000 8501

# Default command: FastAPI Gateway
CMD ["uvicorn", "hearsay.proxy.gateway:app", "--host", "0.0.0.0", "--port", "8000"]
