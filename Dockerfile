# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install git and other dependencies
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /spotizerr-auth

RUN pip install spotizerr-auth==1.1.1

# Set the default command to run the application
CMD ["spotizerr-auth"]
