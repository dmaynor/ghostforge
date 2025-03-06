#!/usr/bin/env python3
"""
GhostForge Model Auto-Downloader

This script automatically downloads the TinyLlama model needed for GhostForge
and sets up the configuration directories.
"""

import os
import sys
import requests
import yaml
from pathlib import Path
import shutil

# Configuration
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.ghostforge")
MODELS_DIR = os.path.join(DEFAULT_CONFIG_DIR, "models")
DEFAULT_MODEL_URL = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
DEFAULT_MODEL_FILENAME = "tinyllama-1.1b-chat.Q4_K_M.gguf"
DEFAULT_MODEL_PATH = os.path.join(MODELS_DIR, DEFAULT_MODEL_FILENAME)


def is_venv_active():
    """Check if a virtual environment is active."""
    return (hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


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
        # Check if required packages are installed
        required_packages = ["requests", "pyyaml"]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            venv_active = is_venv_active()
            pip_flags = []
            
            print("The following required packages are missing:")
            for package in missing_packages:
                print(f"  - {package}")
            
            if not venv_active:
                print("\n⚠️ No virtual environment detected!")
                print("Installing packages system-wide can lead to conflicts.")
                print("Options:")
                print("  1. Create and activate a virtual environment first (recommended)")
                print("  2. Use the --break-system-packages flag (not recommended)")
                print("  3. Skip package installation\n")
                choice = input("Choose an option (1-3): ").strip()
                
                if choice == "1":
                    print("\nPlease run these commands to set up a virtual environment:")
                    print("  python -m venv .venv")
                    print("  source .venv/bin/activate  # On Unix/Mac")
                    print("  .venv\\Scripts\\activate   # On Windows")
                    print("\nThen run this script again.")
                    sys.exit(0)
                elif choice == "2":
                    print("\n⚠️ Using --break-system-packages flag")
                    pip_flags.append("--break-system-packages")
                else:
                    print("\nSkipping package installation.")
                    print("You'll need to install the required packages manually:")
                    print(f"  pip install {' '.join(missing_packages)}")
                    sys.exit(1)
            else:
                print("\n✓ Virtual environment detected")
                install = input("Would you like to install the missing packages now? [Y/n]: ").lower().strip()
                if not (install == "" or install in ('y', 'yes')):
                    print("\nSkipping package installation.")
                    sys.exit(1)
            
            # Install packages
            try:
                import subprocess
                cmd = [sys.executable, "-m", "pip", "install"] + pip_flags + missing_packages
                print(f"\nRunning: {' '.join(cmd)}")
                subprocess.check_call(cmd)
                print("✓ Packages installed successfully")
                
                # Re-import the packages
                for package in missing_packages:
                    __import__(package)
            except Exception as e:
                print(f"✗ Package installation failed: {e}")
                print("\nYou can try installing the packages manually:")
                flags_str = " ".join(pip_flags) + " " if pip_flags else ""
                print(f"  pip install {flags_str}{' '.join(missing_packages)}")
                sys.exit(1)
        
        # Run main function
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1) 