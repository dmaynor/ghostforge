"""
Author: David Maynor (dmaynor@gmail.com)
Project: BuildBot - An Interactive Troubleshooting Assistant

Overview:
BuildBot is a command-line assistant that integrates with TinyLlama to help troubleshoot and analyze
various project files (logs, Dockerfiles, YAML configurations, etc.). It provides an interactive
shell (REPL) for users to interact with, supports file indexing, and allows users to define and
store YAML-based prompts for structured queries.

Usage:
- Run the script to start the interactive shell: `python buildbot.py`
- Use `help` to list available commands.
- Use `index` to scan and store project files for quick lookup.
- YAML-based prompts can be stored in `./prompts/` for structured query use.

Requirements:
- Python 3.8+
- Dependencies (install via `pip install -r requirements.txt`):
  - cmd
  - subprocess
  - os
  - yaml
  - sqlite3
  - json
  - requests
  - sys
  - importlib
  - threading
  - shlex
  - datetime
  - jinja2
  - llama_cpp
"""

import cmd
import subprocess
import os
import yaml
import sqlite3
import json
import requests
import sys
import importlib.util
import threading
import shlex
import datetime
from jinja2 import Template
import fnmatch
from pathlib import Path

# Load environment variables with defaults
MODEL_URL = os.getenv("BUILDBOT_MODEL_URL", "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-GGUF/resolve/main/tinyllama-1.1b-chat.Q4_K_M.gguf")
MODEL_DIR = os.getenv("BUILDBOT_MODEL_DIR", os.path.expanduser("~/.buildbot/models"))
MODEL_PATH = os.path.join(MODEL_DIR, "tinyllama-1.1b-chat.Q4_K_M.gguf")
PROMPT_DIR = os.getenv("BUILDBOT_PROMPT_DIR", "./prompts")
CONFIG_DIR = os.getenv("BUILDBOT_CONFIG_DIR", os.path.expanduser("~/.buildbot"))

# Ensure the directories exist
os.makedirs(PROMPT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# Load configuration
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

exclude_patterns = config.get('indexing', {}).get('exclude_patterns', [])

def should_exclude(filepath):
    path = Path(filepath)
    return any(path.match(pattern) for pattern in exclude_patterns)

# Check for missing dependencies
def check_dependency(module_name):
    print(f"[BuildBot]: Checking for missing dependency: {module_name}")
    print(f"[DEBUG]: Checking dependency {module_name}")
    if importlib.util.find_spec(module_name) is None:
        raise ImportError(f"[BuildBot]: Missing dependency '{module_name}'. Please install it using: pip install {module_name}")

check_dependency("llama_cpp")
from llama_cpp import Llama

def download_model():
    """Downloads the TinyLlama model if it doesn't exist, with error handling and retries."""
    if not os.path.exists(MODEL_PATH):
        print(f"[BuildBot]: Model not found. Downloading from {MODEL_URL}...")
        os.makedirs(MODEL_DIR, exist_ok=True)
        try:
            response = requests.get(MODEL_URL, stream=True, timeout=10)
            response.raise_for_status()
            with open(MODEL_PATH, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print("[BuildBot]: Model downloaded successfully.")
        except requests.exceptions.RequestException as e:
            print(f"[BuildBot]: Error downloading model: {e}")
            sys.exit(1)
    else:
        print("[DEBUG]: Model already exists.")

download_model()

def load_prompt(prompt_name, context={}):
    """Loads and renders a YAML prompt file from the prompts directory using Jinja templates.
    Validates YAML structure before rendering to avoid runtime errors."""
    prompt_path = os.path.join(PROMPT_DIR, f"{prompt_name}.yaml")
    if os.path.exists(prompt_path):
        try:
            with open(prompt_path, "r") as f:
                prompt_data = yaml.safe_load(f)
            if not isinstance(prompt_data, dict):
                print(f"[BuildBot]: Invalid YAML structure in '{prompt_name}.yaml'. Expected a dictionary.")
                return None
            template = Template(yaml.dump(prompt_data))
            return template.render(context)
        except yaml.YAMLError as e:
            print(f"[BuildBot]: Error parsing YAML in '{prompt_name}.yaml': {e}")
            return None
    else:
        print(f"[BuildBot]: Prompt file '{prompt_name}.yaml' not found.")
        return None

class BuildBotShell(cmd.Cmd):
    """Interactive REPL for BuildBot."""
    intro = "BuildBot REPL v1.0\nType 'help' for commands, or 'exit' to quit."
    prompt = "> "
    history = []  # Stores past commands
    watch_threads = {}  # Stores active watch threads

    def __init__(self):
        print("[DEBUG]: Initializing BuildBotShell")
        super().__init__()
        self.config = self.load_config()
        self.model = self.load_model()
        self.db_conn = self.init_database()

    def preloop(self):
        """Setup before the command loop starts."""
        super().preloop()
        # Load history from file if it exists
        try:
            with open(os.path.join(CONFIG_DIR, "history.json"), "r") as f:
                self.history = json.load(f)
        except FileNotFoundError:
            self.history = []

    def precmd(self, line):
        """Pre-command hook to store history."""
        if line.strip() and not line.startswith(("history", "exit")):
            timestamp = datetime.datetime.now().isoformat()
            self.history.append({"timestamp": timestamp, "command": line.strip()})
            # Keep only last 1000 commands
            self.history = self.history[-1000:]
            # Save history to file
            try:
                with open(os.path.join(CONFIG_DIR, "history.json"), "w") as f:
                    json.dump(self.history, f)
            except Exception as e:
                print(f"[BuildBot]: Error saving history: {e}")
        return line

    def postcmd(self, stop, line):
        """Post-command hook."""
        return stop

    def do_exit(self, arg):
        """Exit the shell."""
        print("Goodbye!")
        return True  # Signals to exit

    def do_index(self, arg):
        """Index project files for troubleshooting."""
        print("[DEBUG]: Starting file indexing")
        print("[BuildBot]: Indexing logs, Dockerfiles, and configurations...")
        cursor = self.db_conn.cursor()
        for root, _, files in os.walk("."):
            for file in files:
                filepath = os.path.join(root, file)
                if should_exclude(filepath):
                    continue  # Skip excluded files
                if file.endswith((".log", ".yaml", ".yml", ".json", ".py", ".sh", "Dockerfile")):
                    last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                    try:
                        # First try to open the file to check if it's readable
                        with open(filepath, "rb") as f:
                            # Try to read a small portion to verify it's accessible
                            f.read(1)
                        
                        # If readable, now try to read as text
                        with open(filepath, "r", errors="ignore") as f:
                            content = f.read()
                        cursor.execute("INSERT OR REPLACE INTO files (path, content, last_modified) VALUES (?, ?, ?)", (filepath, content, last_modified))
                    except Exception as e:
                        # More graceful error handling
                        print(f"[BuildBot]: {filepath} will not be indexed.")
        self.db_conn.commit()
        print("[BuildBot]: Indexing complete!")

    def do_search(self, arg):
        """Search indexed files using keywords or patterns.
        Usage: search <keywords> [--type=<file_type>] [--path=<path_pattern>]
        Example: search error --type=log --path=*/server/*"""
        if not arg:
            print("[BuildBot]: Please provide search keywords.")
            return

        args = shlex.split(arg)
        keywords = []
        file_type = None
        path_pattern = None

        # Parse arguments
        for a in args:
            if a.startswith("--type="):
                file_type = a.split("=")[1]
            elif a.startswith("--path="):
                path_pattern = a.split("=")[1]
            else:
                keywords.append(a)

        query = " ".join(keywords)
        sql = "SELECT path, content FROM files WHERE content LIKE ?"
        params = [f"%{query}%"]

        if file_type:
            sql += " AND path LIKE ?"
            params.append(f"%.{file_type}")
        if path_pattern:
            sql += " AND path LIKE ?"
            params.append(f"%{path_pattern}%")

        cursor = self.db_conn.cursor()
        results = cursor.execute(sql, params).fetchall()

        if not results:
            print("[BuildBot]: No matches found.")
            return

        print(f"[BuildBot]: Found {len(results)} matches:")
        for path, content in results:
            print(f"\nFile: {path}")
            # Show context around the match
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    print("..." if start > 0 else "")
                    for j in range(start, end):
                        prefix = ">>> " if j == i else "    "
                        print(f"{prefix}{lines[j]}")
                    print("..." if end < len(lines) else "")
                    break

    def do_analyze(self, arg):
        """Analyze a file or content using TinyLlama.
        Usage: analyze <file_path> [--prompt=<prompt_name>]
        Example: analyze logs/error.log --prompt=error_analysis"""
        if not arg:
            print("[BuildBot]: Please provide a file path to analyze.")
            return

        args = shlex.split(arg)
        file_path = args[0]
        prompt_name = None

        # Parse arguments
        for a in args[1:]:
            if a.startswith("--prompt="):
                prompt_name = a.split("=")[1]

        try:
            with open(file_path, "r", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"[BuildBot]: Error reading file: {e}")
            return

        # Prepare the prompt
        if prompt_name:
            prompt_template = load_prompt(prompt_name, {"content": content})
            if not prompt_template:
                return
        else:
            prompt_template = f"""Analyze the following content and provide insights:
Content:
{content}

Please provide:
1. Summary of the content
2. Key findings or issues
3. Recommendations (if applicable)
"""

        # Generate response using TinyLlama
        try:
            response = self.model.create_completion(
                prompt_template,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.95,
                stop=["<end>"]
            )
            print("\n[BuildBot]: Analysis Results:")
            print(response["choices"][0]["text"].strip())
        except Exception as e:
            print(f"[BuildBot]: Error during analysis: {e}")

    def do_prompt(self, arg):
        """List, view, or create YAML prompts.
        Usage: prompt [list|view|create] [prompt_name]
        Example: prompt list
                prompt view error_analysis
                prompt create custom_analysis"""
        if not arg:
            print("[BuildBot]: Please specify an action (list|view|create).")
            return

        args = shlex.split(arg)
        action = args[0]

        if action == "list":
            prompts = [f for f in os.listdir(PROMPT_DIR) if f.endswith(".yaml")]
            if not prompts:
                print("[BuildBot]: No prompts found.")
                return
            print("[BuildBot]: Available prompts:")
            for prompt in prompts:
                print(f"  - {prompt[:-5]}")

        elif action == "view" and len(args) > 1:
            prompt_name = args[1]
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_name}.yaml")
            try:
                with open(prompt_path, "r") as f:
                    print(f.read())
            except FileNotFoundError:
                print(f"[BuildBot]: Prompt '{prompt_name}' not found.")

        elif action == "create" and len(args) > 1:
            prompt_name = args[1]
            prompt_path = os.path.join(PROMPT_DIR, f"{prompt_name}.yaml")
            if os.path.exists(prompt_path):
                print(f"[BuildBot]: Prompt '{prompt_name}' already exists.")
                return

            template = """# {prompt_name} prompt template
description: Add description here
template: |
  Instructions for analysis:
  {{{{ content }}}}  # This will be replaced with the file content
  
  Please provide:
  1. Point 1
  2. Point 2
  3. Point 3
""".format(prompt_name=prompt_name)

            try:
                with open(prompt_path, "w") as f:
                    f.write(template)
                print(f"[BuildBot]: Created prompt template '{prompt_name}'.")
            except Exception as e:
                print(f"[BuildBot]: Error creating prompt: {e}")

    def do_config(self, arg):
        """View or modify BuildBot configuration.
        Usage: config [view|set|unset] [key] [value]
        Example: config view
                config set model.temperature 0.8"""
        if not arg:
            print("[BuildBot]: Please specify an action (view|set|unset).")
            return

        args = shlex.split(arg)
        action = args[0]

        if action == "view":
            print("[BuildBot]: Current configuration:")
            print(yaml.dump(self.config, default_flow_style=False))

        elif action == "set" and len(args) >= 3:
            key = args[1]
            value = args[2]
            
            # Convert string value to appropriate type
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # Keep as string if not valid JSON

            # Update nested dictionary
            current = self.config
            key_parts = key.split(".")
            for part in key_parts[:-1]:
                current = current.setdefault(part, {})
            current[key_parts[-1]] = value

            # Save configuration
            try:
                with open(CONFIG_PATH, "w") as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                print(f"[BuildBot]: Updated configuration: {key} = {value}")
            except Exception as e:
                print(f"[BuildBot]: Error saving configuration: {e}")

        elif action == "unset" and len(args) >= 2:
            key = args[1]
            current = self.config
            key_parts = key.split(".")
            
            try:
                # Navigate to the parent of the key to unset
                for part in key_parts[:-1]:
                    current = current[part]
                # Remove the key
                del current[key_parts[-1]]
                
                # Save configuration
                with open(CONFIG_PATH, "w") as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                print(f"[BuildBot]: Removed configuration key: {key}")
            except KeyError:
                print(f"[BuildBot]: Configuration key '{key}' not found.")
            except Exception as e:
                print(f"[BuildBot]: Error updating configuration: {e}")

    def do_docker(self, arg):
        """Docker-specific analysis and troubleshooting.
        Usage: docker [analyze|inspect|check] [path]
        Examples:
          docker analyze Dockerfile
          docker inspect docker-compose.yaml
          docker check container_name"""
        if not arg:
            print("[BuildBot]: Please specify an action and target.")
            return

        args = shlex.split(arg)
        if len(args) < 2:
            print("[BuildBot]: Please provide both action and target.")
            return

        action, target = args[0], args[1]

        if action == "analyze":
            # Analyze Dockerfile or docker-compose
            try:
                with open(target, "r") as f:
                    content = f.read()
                
                prompt_template = f"""Analyze this Docker configuration and provide insights:

{content}

Please provide:
1. Configuration Summary
2. Security Concerns (if any)
3. Performance Optimization Suggestions
4. Best Practices Compliance
5. Resource Management Analysis
"""
                response = self.model.create_completion(
                    prompt_template,
                    max_tokens=1000,
                    temperature=0.7,
                    stop=["<end>"]
                )
                print("\n[BuildBot]: Docker Analysis Results:")
                print(response["choices"][0]["text"].strip())

            except Exception as e:
                print(f"[BuildBot]: Error analyzing Docker file: {e}")

        elif action == "inspect":
            # Inspect running container or compose setup
            try:
                result = subprocess.run(["docker", "inspect", target], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    prompt_template = f"""Analyze this Docker inspection output and highlight important details:

{result.stdout}

Focus on:
1. Container Health
2. Network Configuration
3. Volume Mounts
4. Environment Variables
5. Resource Limits
"""
                    response = self.model.create_completion(
                        prompt_template,
                        max_tokens=1000,
                        temperature=0.7,
                        stop=["<end>"]
                    )
                    print("\n[BuildBot]: Docker Inspection Analysis:")
                    print(response["choices"][0]["text"].strip())
                else:
                    print(f"[BuildBot]: Docker inspection failed: {result.stderr}")

            except Exception as e:
                print(f"[BuildBot]: Error during Docker inspection: {e}")

        elif action == "check":
            # Check container health and logs
            try:
                # Get container status
                status = subprocess.run(["docker", "ps", "-a", "--filter", f"name={target}"],
                                     capture_output=True, text=True)
                
                # Get container logs
                logs = subprocess.run(["docker", "logs", "--tail", "100", target],
                                   capture_output=True, text=True)

                prompt_template = f"""Analyze this Docker container's status and recent logs:

Status:
{status.stdout}

Recent Logs:
{logs.stdout}

Please provide:
1. Container Status Summary
2. Log Analysis
3. Potential Issues
4. Health Assessment
"""
                response = self.model.create_completion(
                    prompt_template,
                    max_tokens=1000,
                    temperature=0.7,
                    stop=["<end>"]
                )
                print("\n[BuildBot]: Container Health Analysis:")
                print(response["choices"][0]["text"].strip())

            except Exception as e:
                print(f"[BuildBot]: Error checking container: {e}")

    def do_history(self, arg):
        """View or search command history.
        Usage: history [search_term] [--last=N]
        Examples:
          history
          history docker
          history --last=10"""
        args = shlex.split(arg) if arg else []
        last_n = None
        search_term = None

        # Parse arguments
        for a in args:
            if a.startswith("--last="):
                try:
                    last_n = int(a.split("=")[1])
                except ValueError:
                    print("[BuildBot]: Invalid number for --last")
                    return
            else:
                search_term = a

        # Filter history
        filtered_history = self.history
        if search_term:
            filtered_history = [h for h in filtered_history 
                              if search_term.lower() in h["command"].lower()]
        if last_n:
            filtered_history = filtered_history[-last_n:]

        # Display history
        if not filtered_history:
            print("[BuildBot]: No matching commands in history.")
            return

        print("\n[BuildBot]: Command History:")
        for i, entry in enumerate(filtered_history, 1):
            timestamp = datetime.datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            print(f"{i:3d}. [{timestamp}] {entry['command']}")

    def do_watch(self, arg):
        """Watch a file or command output in real-time.
        Usage: watch [file|command] <target> [--interval=N]
        Examples:
          watch file /var/log/app.log
          watch command "docker ps" --interval=5"""
        if not arg:
            print("[BuildBot]: Please specify what to watch (file or command).")
            return

        args = shlex.split(arg)
        if len(args) < 2:
            print("[BuildBot]: Please provide both watch type and target.")
            return

        watch_type = args[0]
        target = args[1]
        interval = 5  # default interval in seconds

        # Parse interval if provided
        for a in args[2:]:
            if a.startswith("--interval="):
                try:
                    interval = int(a.split("=")[1])
                except ValueError:
                    print("[BuildBot]: Invalid interval value")
                    return

        # Stop existing watch if any
        if target in self.watch_threads:
            self.watch_threads[target].stop()
            del self.watch_threads[target]
            print(f"[BuildBot]: Stopped watching {target}")

        # Create new watch thread
        watch_thread = WatchThread(
            watch_type=watch_type,
            target=target,
            interval=interval,
            model=self.model
        )
        self.watch_threads[target] = watch_thread
        watch_thread.start()
        print(f"[BuildBot]: Started watching {target} (interval: {interval}s)")

    def do_unwatch(self, arg):
        """Stop watching a file or command.
        Usage: unwatch [target|all]
        Examples:
          unwatch /var/log/app.log
          unwatch all"""
        if not arg:
            print("[BuildBot]: Please specify target to unwatch or 'all'.")
            return

        if arg == "all":
            for thread in self.watch_threads.values():
                thread.stop()
            self.watch_threads.clear()
            print("[BuildBot]: Stopped all watches")
        elif arg in self.watch_threads:
            self.watch_threads[arg].stop()
            del self.watch_threads[arg]
            print(f"[BuildBot]: Stopped watching {arg}")
        else:
            print(f"[BuildBot]: No active watch for {arg}")

    def do_watches(self, arg):
        """List active watches.
        Usage: watches"""
        if not self.watch_threads:
            print("[BuildBot]: No active watches")
            return

        print("\n[BuildBot]: Active Watches:")
        for target, thread in self.watch_threads.items():
            status = "Running" if thread.is_alive() else "Stopped"
            print(f"  - {target} ({status}, interval: {thread.interval}s)")

    def do_help(self, arg):
        """List available commands with their usage."""
        if arg:
            super().do_help(arg)
        else:
            print("\nAvailable commands:")
            print("  index   - Index project files for troubleshooting")
            print("  search  - Search indexed files using keywords")
            print("  analyze - Analyze files using TinyLlama")
            print("  prompt  - Manage YAML prompt templates")
            print("  config  - View or modify BuildBot configuration")
            print("  docker  - Docker-specific analysis and troubleshooting")
            print("  history - View or search command history")
            print("  watch   - Watch files or command output in real-time")
            print("  unwatch - Stop watching a target")
            print("  watches - List active watches")
            print("  exit    - Exit the shell")
            print("\nUse 'help <command>' for detailed usage of each command.")

    def load_model(self):
        """Load the LLM model based on configuration."""
        print("[DEBUG]: Loading model")
        model_config = self.config.get("model", {})
        model_path = model_config.get("path", MODEL_PATH)
        
        # Model parameters
        params = {
            "n_ctx": model_config.get("context_size", 2048),
            "n_threads": model_config.get("threads", None),
            "n_gpu_layers": model_config.get("gpu_layers", 0),
            "seed": model_config.get("seed", -1),
            "f16_kv": model_config.get("f16_kv", True)
        }
        
        return Llama(model_path=model_path, **params)

    def do_model(self, arg):
        """Manage LLM models and configurations.
        Usage: model [list|download|switch|info] [model_name_or_url]
        Examples:
          model list
          model download mistral-7b-instruct
          model switch mistral-7b-instruct
          model info"""
        if not arg:
            print("[BuildBot]: Please specify an action.")
            return

        args = shlex.split(arg)
        action = args[0]

        if action == "list":
            print("\n[BuildBot]: Available Models:")
            models = [f for f in os.listdir(MODEL_DIR) if f.endswith(".gguf")]
            if not models:
                print("  No models found in models directory.")
            else:
                current = self.config.get("model", {}).get("path", MODEL_PATH)
                for model in models:
                    path = os.path.join(MODEL_DIR, model)
                    size = os.path.getsize(path) / (1024 * 1024)  # Size in MB
                    current_marker = "*" if path == current else " "
                    print(f"  [{current_marker}] {model} ({size:.1f} MB)")

        elif action == "download":
            if len(args) < 2:
                print("[BuildBot]: Please provide a model name or URL.")
                return

            model_url = args[1]
            if not model_url.startswith("http"):
                # Convert model name to Hugging Face URL
                model_url = f"https://huggingface.co/TheBloke/{model_url}-GGUF/resolve/main/{model_url}.Q4_K_M.gguf"

            try:
                print(f"[BuildBot]: Downloading model from {model_url}...")
                response = requests.get(model_url, stream=True)
                response.raise_for_status()
                
                filename = os.path.basename(model_url)
                filepath = os.path.join(MODEL_DIR, filename)
                
                total_size = int(response.headers.get("content-length", 0))
                block_size = 1024 * 1024  # 1MB chunks
                progress = 0
                
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            progress += len(chunk)
                            if total_size:
                                percent = (progress * 100) / total_size
                                print(f"\rProgress: {percent:.1f}% ({progress/(1024*1024):.1f} MB)", end="")
                
                print("\n[BuildBot]: Model downloaded successfully!")
                
            except Exception as e:
                print(f"[BuildBot]: Error downloading model: {e}")

        elif action == "switch":
            if len(args) < 2:
                print("[BuildBot]: Please provide a model name.")
                return

            model_name = args[1]
            if not model_name.endswith(".gguf"):
                model_name += ".Q4_K_M.gguf"

            model_path = os.path.join(MODEL_DIR, model_name)
            if not os.path.exists(model_path):
                print(f"[BuildBot]: Model '{model_name}' not found.")
                return

            try:
                # Update configuration
                if "model" not in self.config:
                    self.config["model"] = {}
                self.config["model"]["path"] = model_path

                # Save configuration
                with open(CONFIG_PATH, "w") as f:
                    yaml.dump(self.config, f, default_flow_style=False)

                # Reload model
                print("[BuildBot]: Reloading model...")
                self.model = self.load_model()
                print(f"[BuildBot]: Switched to model: {model_name}")

            except Exception as e:
                print(f"[BuildBot]: Error switching model: {e}")

        elif action == "info":
            model_config = self.config.get("model", {})
            current_model = model_config.get("path", MODEL_PATH)
            
            print("\n[BuildBot]: Current Model Configuration:")
            print(f"  Model Path: {current_model}")
            print(f"  Context Size: {model_config.get('context_size', 2048)}")
            print(f"  GPU Layers: {model_config.get('gpu_layers', 0)}")
            print(f"  Threads: {model_config.get('threads', 'auto')}")
            print(f"  F16 KV: {model_config.get('f16_kv', True)}")
            
            if os.path.exists(current_model):
                size = os.path.getsize(current_model) / (1024 * 1024)  # Size in MB
                print(f"  Model Size: {size:.1f} MB")
            else:
                print("  Warning: Model file not found!")

    def do_prompts(self, arg):
        """Alias for prompt command."""
        self.do_prompt(arg)

# Add WatchThread class at the top level
class WatchThread(threading.Thread):
    """Thread class for watching files or command output."""
    
    def __init__(self, watch_type, target, interval, model):
        super().__init__()
        self.watch_type = watch_type
        self.target = target
        self.interval = interval
        self.model = model
        self.stop_event = threading.Event()
        self.last_content = None
        self.daemon = True  # Thread will be terminated when main program exits

    def stop(self):
        """Signal the thread to stop."""
        self.stop_event.set()

    def run(self):
        """Main thread loop."""
        while not self.stop_event.is_set():
            try:
                if self.watch_type == "file":
                    self._watch_file()
                elif self.watch_type == "command":
                    self._watch_command()
            except Exception as e:
                print(f"[BuildBot]: Watch error ({self.target}): {e}")
                break
            
            # Wait for interval or until stopped
            self.stop_event.wait(self.interval)

    def _watch_file(self):
        """Watch a file for changes."""
        try:
            with open(self.target, "r") as f:
                content = f.read()
            
            if content != self.last_content:
                if self.last_content is not None:  # Skip first run
                    self._analyze_changes(content)
                self.last_content = content

        except FileNotFoundError:
            print(f"[BuildBot]: File not found: {self.target}")
            self.stop()
        except Exception as e:
            print(f"[BuildBot]: Error reading file: {e}")

    def _watch_command(self):
        """Watch command output for changes."""
        try:
            result = subprocess.run(shlex.split(self.target), 
                                  capture_output=True, text=True)
            content = result.stdout

            if content != self.last_content:
                if self.last_content is not None:  # Skip first run
                    self._analyze_changes(content)
                self.last_content = content

        except Exception as e:
            print(f"[BuildBot]: Error running command: {e}")

    def _analyze_changes(self, new_content):
        """Analyze changes using TinyLlama."""
        prompt = f"""Analyze the following changes and provide insights:

Previous Content Length: {len(self.last_content) if self.last_content else 0}
New Content Length: {len(new_content)}

New or Changed Content:
{new_content}

Please provide:
1. Summary of changes
2. Important events or patterns
3. Potential issues or warnings
4. Recommended actions (if any)
"""
        try:
            response = self.model.create_completion(
                prompt,
                max_tokens=500,
                temperature=0.7,
                stop=["<end>"]
            )
            print(f"\n[BuildBot]: Change Analysis for {self.target}:")
            print(response["choices"][0]["text"].strip())
        except Exception as e:
            print(f"[BuildBot]: Error analyzing changes: {e}")

if __name__ == "__main__":
    print("[DEBUG]: Starting BuildBotShell")
    BuildBotShell().cmdloop()
