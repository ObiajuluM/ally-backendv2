# ============================================================================
# Stage 1 - Builder
# ============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install only packages needed to build Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip

RUN pip install --prefix=/install -r requirements.txt


# ============================================================================
# Stage 2 - Runtime
# ============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1

# Install only runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gdal-bin \
    libgdal32 \
    libgeos-c1v5 \
    libproj25 \
    binutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages
COPY --from=builder /install /usr/local

# Copy project
COPY . .

# Create directories used by Django
RUN mkdir -p \
    static \
    staticfiles \
    media

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]