#!/usr/bin/env python3
"""
GhostForge Model Auto-Downloader (Simple Version)

This script automatically downloads the TinyLlama model needed for GhostForge
and sets up the configuration directories.
"""

import os
import sys
import requests
from pathlib import Path
import yaml

# Configuration
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.ghostforge")
MODELS_DIR = os.path.join(DEFAULT_CONFIG_DIR, "models")
DEFAULT_MODEL_URL = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
DEFAULT_MODEL_FILENAME = "tinyllama-1.1b-chat.Q4_K_M.gguf"
DEFAULT_MODEL_PATH = os.path.join(MODELS_DIR, DEFAULT_MODEL_FILENAME)


def ensure_directory(path):
    """Ensure a directory exists."""
    os.makedirs(path, exist_ok=True)
    print(f"✓ Directory created/confirmed: {path}")


def download_file(url, destination):
    """
    Download a file with progress indication.
    
    Args:
        url: URL to download from
        destination: Path to save the file to
    """
    print(f"\nDownloading: {url}")
    print(f"To: {destination}")
    
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Start download
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for bad responses
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        print(f"File size: {total_size / (1024 * 1024):.1f} MB")
        print("Progress: ", end="", flush=True)
        
        with open(destination, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)
                    percent = int(50 * downloaded / total_size) if total_size else 0
                    sys.stdout.write(f"\rProgress: [{'#' * percent}{' ' * (50 - percent)}] {downloaded / (1024 * 1024):.1f}/{total_size / (1024 * 1024):.1f} MB")
                    sys.stdout.flush()
        
        print("\n✓ Download complete!")
        return True
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        return False


def create_default_config():
    """Create a default configuration file."""
    config_file = os.path.join(DEFAULT_CONFIG_DIR, "config.yaml")
    
    # Only create if it doesn't exist
    if os.path.exists(config_file):
        print(f"✓ Config file already exists: {config_file}")
        return
    
    config = {
        "model": {
            "path": DEFAULT_MODEL_PATH,
            "context_size": 2048,
            "gpu_layers": 0,
            "threads": 4,
            "f16_kv": True
        },
        "prompts_directory": os.path.join(DEFAULT_CONFIG_DIR, "prompts"),
        "database_path": os.path.join(DEFAULT_CONFIG_DIR, "ghostforge.db"),
        "exclude_patterns": [
            "*.pyc",
            "__pycache__/*",
            ".git/*",
            "*.log"
        ]
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"✓ Created default config: {config_file}")


def main():
    """Main function to set up GhostForge."""
    print("\n=== GhostForge Auto Setup ===\n")
    
    # Create config directory
    ensure_directory(DEFAULT_CONFIG_DIR)
    
    # Create models directory
    ensure_directory(MODELS_DIR)
    
    # Create default config file
    create_default_config()
    
    # Check if model exists
    if os.path.exists(DEFAULT_MODEL_PATH):
        print(f"✓ Model already exists: {DEFAULT_MODEL_PATH}")
        print("\nGhostForge is ready to use!")
        print("\nRun the shell with:")
        print("  python -m ghostforge.shell")
        return 0
    
    # Download model
    print(f"\nModel not found at: {DEFAULT_MODEL_PATH}")
    download = input("Would you like to download the model now? (~125MB) [Y/n]: ").lower().strip()
    
    if download in ('', 'y', 'yes'):
        success = download_file(DEFAULT_MODEL_URL, DEFAULT_MODEL_PATH)
        if success:
            print("\n✓ GhostForge setup complete!")
            print("\nRun the shell with:")
            print("  python -m ghostforge.shell")
            return 0
        else:
            print("\n✗ Model download failed.")
            print("You can try manually downloading the model later with:")
            print(f"  curl -L {DEFAULT_MODEL_URL} -o {DEFAULT_MODEL_PATH}")
            return 1
    else:
        print("\nModel download skipped.")
        print("You'll need to provide a model before using GhostForge's LLM features.")
        print("You can run GhostForge with limited functionality or download the model later.")
        return 0


if __name__ == "__main__":
    try:
        # Run main function
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1) 