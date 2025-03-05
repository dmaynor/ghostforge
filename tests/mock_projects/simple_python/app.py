"""
Simple Python application for testing GhostForge indexing and analysis.
This file contains intentional issues for GhostForge to detect.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global variable - potential issue for review
DEBUG = True
PASSWORD = "hardcoded_password"  # Security issue to be detected

class ConfigManager:
    """Configuration manager for the application."""
    
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
            else:
                logger.warning(f"Configuration file {self.config_path} not found. Using defaults.")
                self.config = {"debug": True, "timeout": 30}
        except json.JSONDecodeError:
            # Error handling issue - using empty config instead of raising
            logger.error(f"Invalid JSON in {self.config_path}")
            self.config = {}
    
    def get(self, key, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Configuration saved to {self.config_path}")

# Memory leak example - keeps growing without bounds
request_history = []

def process_request(request_data):
    """Process a request and store it in history."""
    timestamp = datetime.now().isoformat()
    request_with_time = {"timestamp": timestamp, "data": request_data}
    
    # Memory leak - continuously appends without any cleanup
    request_history.append(request_with_time)
    
    # Unnecessary nested conditions - code smell
    if "action" in request_data:
        action = request_data["action"]
        if action == "query":
            if "query_string" in request_data:
                query_string = request_data["query_string"]
                return execute_query(query_string)
            else:
                return {"error": "missing_query_string"}
        elif action == "update":
            return update_data(request_data)
        else:
            return {"error": "unknown_action"}
    else:
        return {"error": "missing_action"}

def execute_query(query_string):
    """Execute a database query."""
    # SQL Injection vulnerability for GhostForge to detect
    # This function directly uses the query string without sanitization
    logger.info(f"Executing query: {query_string}")
    
    # Simulate database query
    return {"result": f"Query executed: {query_string}", "status": "success"}

def update_data(data):
    """Update data in the database."""
    logger.info(f"Updating data: {data}")
    
    # Unnecessary resource usage - creates a new connection for each update
    # conn = create_db_connection()
    # update_result = conn.update(data)
    # conn.close()
    
    return {"status": "updated", "timestamp": datetime.now().isoformat()}

def main():
    """Main function to run the application."""
    logger.info("Application started")
    
    # Potential crash without try/except
    config = ConfigManager()
    
    # Infinite loop without clear exit condition
    while DEBUG:
        try:
            command = input("Enter command: ")
            if command == "exit":
                break
            
            result = process_request({"action": command})
            print(json.dumps(result, indent=2))
            
        except KeyboardInterrupt:
            logger.info("Application terminated by user")
            break
        except Exception as e:
            # Overly broad exception handling
            logger.error(f"Error: {e}")
    
    logger.info("Application stopped")

if __name__ == "__main__":
    main() 