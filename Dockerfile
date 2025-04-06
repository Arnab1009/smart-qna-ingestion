# Use an official Python image as base
FROM python:3.12-slim

# Set working directory in container
WORKDIR /app

# Copy project files into container
COPY . .

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to not use virtual environments
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-root

# Command to run the app
CMD ["python", "app/trigger_ingestion.py"]