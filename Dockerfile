# Minimal Dockerfile for Smart Buddy (local-first)
# Note: models can be large. Mount `./models` into the container or pre-download before building.

FROM python:3.11-slim

# Install OS deps needed for optional binaries and wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only what's needed for installation
COPY pyproject.toml .
COPY requirements.txt .
COPY smart_buddy ./smart_buddy
COPY scripts ./scripts
COPY examples ./examples

# Install package (runtime deps). Using editable install may require build tools; use normal install.
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
RUN pip install .

# Default command runs the demo; mount models at /app/models when running for local gpt4all
CMD ["python", "examples/run_demo.py"]
