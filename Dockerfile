# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create upload directory
RUN mkdir -p static/uploads

# Expose port
EXPOSE 8080

# Set environment variable for Flask
ENV FLASK_APP=app.py

# Run the application with Python directly (uses socketio.run())
CMD ["python", "app.py"]
