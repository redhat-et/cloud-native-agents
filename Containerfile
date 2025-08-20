FROM python:3.11-slim

# Set the final WORKDIR for your application
WORKDIR /cloud-native-agent/kafka

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy requirements.txt into the WORKDIR and install
# The source path 'kafka/requirements.txt' is relative to the build context (your project root)
COPY kafka/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set the home directory for streamlit to a writable location
ENV STREAMLIT_HOME=/cloud-native-agent/kafka/.streamlit

# Copy the rest of your kafka application code into the WORKDIR
COPY kafka/ .

# Copy the backend code to a directory OUTSIDE the WORKDIR
# The destination path is absolute
COPY backend/core/ /cloud-native-agent/backend/core/
