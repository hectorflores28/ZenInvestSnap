# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Expose port 8000
EXPOSE 8000

# Run Django migrations before starting the app so the auth tables exist
# on first boot and after fresh container creation.
CMD ["/bin/sh", "-c", "python zen_invest_snap/manage.py migrate --noinput && exec python zen_invest_snap/manage.py runserver 0.0.0.0:8000"]
