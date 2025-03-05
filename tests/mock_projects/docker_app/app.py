"""Simple Flask application for Docker testing."""

import os
import json
import time
import redis
import logging
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection - credentials in code is a security issue
DB_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@db:5432/app_db")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
API_KEY = os.environ.get("API_KEY", "default_key")
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Global database connection - not ideal for Flask
try:
    db_engine = create_engine(DB_URL)
    redis_client = redis.from_url(REDIS_URL)
    logger.info("Database and Redis connections established")
except Exception as e:
    logger.error(f"Error connecting to database or Redis: {e}")
    # No fallback mechanism - app will be broken

@app.route("/")
def index():
    """Root endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Docker test app is running"
    })

@app.route("/api/data", methods=["GET"])
def get_data():
    """Get data endpoint."""
    # No authentication check
    
    # Simulating slow response
    time.sleep(2)
    
    try:
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM data LIMIT 100"))
            data = [dict(row) for row in result]
        return jsonify({"data": data})
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/data", methods=["POST"])
def create_data():
    """Create data endpoint."""
    # Basic auth - not ideal for production
    auth_key = request.headers.get("X-API-Key")
    if auth_key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # SQL injection vulnerability - using string formatting
        query = f"INSERT INTO data (name, value) VALUES ('{data['name']}', '{data['value']}')"
        with db_engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        
        # Caching issue - not invalidating cache after write
        redis_client.set(f"data:{data['name']}", json.dumps(data))
        
        return jsonify({"status": "created", "data": data})
    except Exception as e:
        logger.error(f"Error writing to database: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats")
def get_stats():
    """Get application statistics."""
    stats = {
        "database_connections": db_engine.pool.size(),
        "redis_connections": redis_client.info("clients")["connected_clients"],
        "api_requests": redis_client.incr("stats:api_requests"),
        "uptime": time.time() - app.start_time
    }
    return jsonify(stats)

# Memory leak - start time never gets reset
app.start_time = time.time()

if __name__ == "__main__":
    # Running in debug mode in production - security issue
    app.run(host="0.0.0.0", port=5000, debug=DEBUG) 