# Environment setup using the latest Python image
FROM python:latest

# Set working directory inside the container
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    vim \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Pixi
RUN curl -fsSL https://pixi.sh/install.sh | bash

# Add Pixi to the PATH
ENV PATH="/root/.pixi/bin:${PATH}"

# Verify Pixi installation
RUN pixi --version