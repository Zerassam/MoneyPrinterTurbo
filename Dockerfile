# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /MoneyPrinterTurbo

# 设置/MoneyPrinterTurbo目录权限为777
RUN chmod 777 /MoneyPrinterTurbo

ENV PYTHONPATH="/MoneyPrinterTurbo"

# Install system dependencies from the official Debian repositories and clean
# the apt cache so the Railway image stays small.
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements.txt first to leverage Docker cache
COPY requirements.txt ./

# Install Python dependencies from the official PyPI index without retaining
# a pip cache in the image.
RUN pip install --no-cache-dir --retries 3 --timeout 60 -r requirements.txt

# Now copy the rest of the codebase into the image
COPY . .

# Expose the port the app runs on
RUN chmod +x entrypoint.sh

EXPOSE 8501

# Use entrypoint.sh so $PORT is read at runtime (Railway sets it dynamically).
# Falls back to 8501 when PORT is not set (local docker, compose, etc.).
CMD ["sh", "./entrypoint.sh"]

# 1. Build the Docker image using the following command
# docker build -t moneyprinterturbo .

# 2. Run the Docker container using the following command
## For Linux or MacOS:
# docker run -v $(pwd)/config.toml:/MoneyPrinterTurbo/config.toml -v $(pwd)/storage:/MoneyPrinterTurbo/storage -p 127.0.0.1:7860:7860 moneyprinterturbo
## For Windows:
# docker run -v ${PWD}/config.toml:/MoneyPrinterTurbo/config.toml -v ${PWD}/storage:/MoneyPrinterTurbo/storage -p 127.0.0.1:7860:7860 moneyprinterturbo
