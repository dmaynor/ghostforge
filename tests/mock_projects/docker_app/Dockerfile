FROM python:3.9-slim

# Set working directory - using absolute path which isn't ideal
WORKDIR /app

# Install dependencies without a specific version - potential issue
RUN pip install flask redis requests sqlalchemy

# Copy application code
COPY . .

# Set environment variables - including credentials which is a security issue
ENV DATABASE_URL=postgresql://user:password@db:5432/app_db
ENV REDIS_URL=redis://redis:6379/0
ENV API_KEY=1234567890abcdef
ENV DEBUG=True

# Run as root by default - security issue
# USER app_user

# Using CMD instead of ENTRYPOINT makes it easy to override
CMD ["python", "app.py"]

# Expose port
EXPOSE 5000

# Missing HEALTHCHECK

# Large number of layers - could be optimized
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y vim
RUN apt-get install -y git

# Inefficient caching - these should come before the COPY
COPY requirements.txt .
RUN pip install -r requirements.txt 