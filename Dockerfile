# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install git and other dependencies
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/Xoconoch/spotizerr-auth.git

# Set the working directory
WORKDIR /spotizerr-auth

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the default command to run the application
CMD ["python", "spotizerr-auth.py"]
