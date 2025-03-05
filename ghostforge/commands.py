"""GhostForge shell commands."""

import os
import sys
import time
import json
import yaml
import shlex
import threading
import subprocess
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
import fnmatch
from jinja2 import Template
from .utils import load_prompt

# Load environment variables with defaults
PROMPT_DIR = os.getenv("GHOSTFORGE_PROMPT_DIR", os.path.expanduser("~/.ghostforge/prompts"))
CONFIG_DIR = os.getenv("GHOSTFORGE_CONFIG_DIR", os.path.expanduser("~/.ghostforge"))

def do_exit(self, arg):
    """Exit the GhostForge shell."""
    print("Goodbye!")
    return True

def do_index(self, arg):
    """Index files in the current directory for searching.
    Usage: index [path]
    """
    path = arg.strip() if arg else "."
    if not os.path.exists(path):
        print(f"[GhostForge]: Path '{path}' does not exist.")
        return

    cursor = self.db_conn.cursor()
    for root, _, files in os.walk(path):
        for file in files:
            if file.startswith(".") or any(file.endswith(ext) for ext in [".pyc", ".git"]):
                continue
            
            file_path = os.path.join(root, file)
            try:
                # First try to open the file to check if it's readable
                with open(file_path, "rb") as f:
                    # Try to read a small portion to verify it's accessible
                    f.read(1)
                
                # If readable, now try to read as text with UTF-8 encoding
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                last_modified = os.path.getmtime(file_path)
                
                cursor.execute(
                    "INSERT OR REPLACE INTO files (path, content, last_modified) VALUES (?, ?, ?)",
                    (file_path, content, last_modified)
                )
            except Exception as e:
                # More graceful error handling
                print(f"[GhostForge]: {file_path} will not be indexed.")
    
    self.db_conn.commit()
    print("[GhostForge]: Indexing complete.")

def do_search(self, arg):
    """Search indexed files.
    Usage: search <query>
    """
    if not arg:
        print("[GhostForge]: Please provide a search query.")
        return

    cursor = self.db_conn.cursor()
    cursor.execute(
        "SELECT path, content FROM files WHERE content LIKE ?",
        (f"%{arg}%",)
    )
    results = cursor.fetchall()

    if not results:
        print("[GhostForge]: No matches found.")
        return

    print(f"[GhostForge]: Found {len(results)} matches:")
    for path, content in results:
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if arg in line:
                print(f"\n{path}:{i}")
                print(f"    {line.strip()}")

def do_analyze(self, arg):
    """Analyze a file or directory using the LLM.
    Usage: analyze <path> [prompt_name]
    """
    args = shlex.split(arg)
    if not args:
        print("[GhostForge]: Please provide a path to analyze.")
        return

    path = args[0]
    prompt_name = args[1] if len(args) > 1 else "default_analysis"

    if not os.path.exists(path):
        print(f"[GhostForge]: Path '{path}' does not exist.")
        return

    # Load the analysis prompt
    prompt_text = load_prompt(prompt_name, {"path": path})
    if not prompt_text:
        return

    # Get file content
    try:
        if os.path.isfile(path):
            with open(path, "r") as f:
                content = f.read()
        else:
            content = subprocess.check_output(["tree", path]).decode()
    except Exception as e:
        print(f"[GhostForge]: Error reading '{path}': {e}")
        return

    # Generate analysis
    try:
        response = self.model.create_completion(
            f"{prompt_text}\n\nContent:\n{content}",
            max_tokens=1000,
            temperature=0.7,
            stop=["<end>"]
        )
        print("\n[GhostForge Analysis]:")
        print(response.choices[0].text.strip())
    except Exception as e:
        print(f"[GhostForge]: Error generating analysis: {e}")

def do_prompt(self, arg):
    """Create or edit a prompt template.
    Usage: prompt <name>
    """
    if not arg:
        print("[GhostForge]: Please provide a prompt name.")
        return

    prompt_path = os.path.join(self.config.get("prompt_dir", "prompts"), f"{arg}.yaml")
    
    if not os.path.exists(prompt_path):
        default_prompt = {
            "system": "You are an AI assistant analyzing code or system output.",
            "user": "Please analyze the following content and provide insights:\n{{content}}"
        }
        with open(prompt_path, "w") as f:
            yaml.dump(default_prompt, f)
        print(f"[GhostForge]: Created new prompt template '{arg}.yaml'")
    
    # Open the prompt file in the default editor
    editor = os.getenv("EDITOR", "vim")
    subprocess.run([editor, prompt_path])

def do_config(self, arg):
    """View or edit GhostForge configuration.
    Usage: config [edit]
    """
    config_path = os.path.join(CONFIG_DIR, "config.yaml")
    
    if arg == "edit":
        if not os.path.exists(config_path):
            default_config = {
                "model": {
                    "path": os.path.expanduser("~/.ghostforge/models/model.gguf"),
                    "context_size": 2048,
                    "gpu_layers": 0
                },
                "prompt_dir": os.path.expanduser("~/.ghostforge/prompts"),
                "history_size": 1000
            }
            with open(config_path, "w") as f:
                yaml.dump(default_config, f)
        
        editor = os.getenv("EDITOR", "vim")
        subprocess.run([editor, config_path])
    else:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                print(yaml.dump(yaml.safe_load(f)))
        else:
            print("[GhostForge]: No configuration file found. Use 'config edit' to create one.")

def do_docker(self, arg):
    """Analyze Docker containers and images.
    Usage: docker [container|image] [id/name]
    """
    args = shlex.split(arg)
    if not args:
        print("[GhostForge]: Please specify 'container' or 'image'.")
        return

    command = args[0]
    target = args[1] if len(args) > 1 else None

    try:
        if command == "container":
            if target:
                output = subprocess.check_output(["docker", "inspect", target]).decode()
                logs = subprocess.check_output(["docker", "logs", target]).decode()
                content = f"Container Inspection:\n{output}\n\nContainer Logs:\n{logs}"
            else:
                content = subprocess.check_output(["docker", "ps", "-a"]).decode()
        elif command == "image":
            if target:
                content = subprocess.check_output(["docker", "image", "inspect", target]).decode()
            else:
                content = subprocess.check_output(["docker", "images"]).decode()
        else:
            print("[GhostForge]: Invalid command. Use 'container' or 'image'.")
            return

        prompt_text = load_prompt("docker_analysis", {"type": command, "target": target})
        if prompt_text:
            response = self.model.create_completion(
                f"{prompt_text}\n\nContent:\n{content}",
                max_tokens=1000,
                temperature=0.7,
                stop=["<end>"]
            )
            print("\n[GhostForge Analysis]:")
            print(response.choices[0].text.strip())
    except subprocess.CalledProcessError as e:
        print(f"[GhostForge]: Docker command failed: {e}")
    except Exception as e:
        print(f"[GhostForge]: Error: {e}")

def do_history(self, arg):
    """View command history.
    Usage: history [export]
    """
    if arg == "export":
        export_path = os.path.join(CONFIG_DIR, f"history_export_{int(time.time())}.json")
        with open(export_path, "w") as f:
            json.dump(self.history, f, indent=2)
        print(f"[GhostForge]: History exported to {export_path}")
    else:
        for i, entry in enumerate(self.history, 1):
            print(f"{i:4d}  {entry['timestamp']}  {entry['command']}")

def do_watch(self, arg):
    """Watch a file or command for changes.
    Usage: watch <file|command> <target>
    """
    args = shlex.split(arg)
    if len(args) < 2:
        print("[GhostForge]: Please specify what to watch and the target.")
        return

    watch_type = args[0]
    target = " ".join(args[1:])
    watch_id = f"{watch_type}:{target}"

    if watch_id in self.watch_threads:
        print(f"[GhostForge]: Already watching {watch_type} '{target}'")
        return

    def watch_file(path):
        last_modified = os.path.getmtime(path)
        while True:
            time.sleep(1)
            try:
                current_modified = os.path.getmtime(path)
                if current_modified != last_modified:
                    print(f"\n[GhostForge]: File '{path}' changed.")
                    with open(path, "r") as f:
                        content = f.read()
                    prompt_text = load_prompt("file_change", {"path": path})
                    if prompt_text:
                        response = self.model.create_completion(
                            f"{prompt_text}\n\nContent:\n{content}",
                            max_tokens=500,
                            temperature=0.7
                        )
                        print(response.choices[0].text.strip())
                    last_modified = current_modified
            except Exception as e:
                print(f"[GhostForge]: Error watching file: {e}")
                break

    def watch_command(cmd):
        while True:
            try:
                output = subprocess.check_output(shlex.split(cmd)).decode()
                prompt_text = load_prompt("command_output", {"command": cmd})
                if prompt_text:
                    response = self.model.create_completion(
                        f"{prompt_text}\n\nOutput:\n{output}",
                        max_tokens=500,
                        temperature=0.7
                    )
                    print(f"\n[GhostForge]: Command '{cmd}' output analysis:")
                    print(response.choices[0].text.strip())
                time.sleep(5)
            except Exception as e:
                print(f"[GhostForge]: Error watching command: {e}")
                break

    if watch_type == "file":
        if not os.path.exists(target):
            print(f"[GhostForge]: File '{target}' does not exist.")
            return
        thread = threading.Thread(target=watch_file, args=(target,), daemon=True)
    elif watch_type == "command":
        thread = threading.Thread(target=watch_command, args=(target,), daemon=True)
    else:
        print("[GhostForge]: Invalid watch type. Use 'file' or 'command'.")
        return

    thread.start()
    self.watch_threads[watch_id] = thread
    print(f"[GhostForge]: Started watching {watch_type} '{target}'")

def do_unwatch(self, arg):
    """Stop watching a file or command.
    Usage: unwatch <file|command> <target>
    """
    if not arg:
        print("[GhostForge]: Please specify what to unwatch.")
        return

    args = shlex.split(arg)
    watch_type = args[0]
    target = " ".join(args[1:])
    watch_id = f"{watch_type}:{target}"

    if watch_id in self.watch_threads:
        # Thread will terminate on next iteration
        del self.watch_threads[watch_id]
        print(f"[GhostForge]: Stopped watching {watch_type} '{target}'")
    else:
        print(f"[GhostForge]: Not watching {watch_type} '{target}'")

def do_watches(self, _):
    """List active watches."""
    if not self.watch_threads:
        print("[GhostForge]: No active watches.")
        return

    print("[GhostForge]: Active watches:")
    for watch_id in self.watch_threads:
        watch_type, target = watch_id.split(":", 1)
        print(f"  {watch_type}: {target}")

def get_command_categories(self):
    """Get all commands organized by category."""
    # Return a dictionary of command categories
    return {
        "Core Commands": ["help", "exit"],
        "File Operations": ["index", "search", "analyze"],
        "Configuration": ["config", "prompt", "model", "prompts"],
        "Monitoring": ["watch", "unwatch", "watches"],
        "Analysis": ["docker", "analyze", "detect"],
        "History": ["history"]
    }

def do_help(self, arg):
    """Show help about commands.
    Usage: help [command]
    
    Without arguments, shows a general overview and lists all commands by category.
    With a command name, shows detailed help for that specific command.
    """
    if arg:
        # Show help about specific command
        try:
            func = getattr(self, 'do_' + arg)
            print(f"\n[GhostForge]: Help for command '{arg}':")
            print(f"\n{func.__doc__}")
        except AttributeError:
            print(f"[GhostForge]: No such command: {arg}")
        return

    # Show general overview
    print("""
[GhostForge] - AI-powered DevOps Troubleshooting Assistant
=====================================================

GhostForge helps you analyze and troubleshoot your development environment, providing
AI-powered insights for various aspects of your project.

Getting Started:
---------------
1. Initialize your environment:
   > index                    # Index your project files
   > model download <url>     # Download a model (if not already present)

2. Basic Analysis:
   > analyze <file>          # Analyze a specific file
   > detect                  # Detect project characteristics
   > docker container <name> # Analyze a Docker container

3. Monitoring:
   > watch file <path>      # Monitor a file for changes
   > watch command <cmd>    # Monitor command output
   > watches               # List active watches

4. Configuration:
   > config                # View current configuration
   > config edit          # Edit configuration
   > prompts list         # List available prompt templates

Available Commands by Category:
---------------------------""")

    # Show commands by category
    categories = self.get_command_categories()
    for category, commands in categories.items():
        print(f"\n{category}:")
        for cmd in commands:
            func = getattr(self, f'do_{cmd}')
            doc = func.__doc__.split('\n')[0] if func.__doc__ else 'No description available'
            print(f"  {cmd:<15} {doc}")

    print("""
Additional Help:
--------------
- Use 'help <command>' for detailed information about a specific command
- Press TAB for command completion
- Commands support various options; use help on specific commands to learn more

Examples:
--------
> analyze logs/error.log              # Analyze an error log
> docker container web-server         # Analyze a Docker container
> watch file config/app.yaml          # Monitor configuration changes
> detect                             # Analyze project structure
> prompts list                       # List available analysis templates

Environment:
-----------
- Config Directory: ~/.ghostforge/
- Models Directory: ~/.ghostforge/models/
- Prompts Directory: ~/.ghostforge/prompts/
- Database: ~/.ghostforge/index.db

For more information, visit: https://github.com/dmaynor/ghostforge
""")

def do_model(self, arg):
    """Manage LLM models.
    Usage: model [list|download|switch|info]
    """
    if not arg:
        print("[GhostForge]: Please specify a subcommand: list, download, switch, or info")
        return

    args = shlex.split(arg)
    command = args[0]

    if command == "list":
        model_dir = os.path.expanduser("~/.ghostforge/models")
        if not os.path.exists(model_dir):
            print("[GhostForge]: No models found.")
            return
        print("[GhostForge]: Available models:")
        for model in os.listdir(model_dir):
            if model.endswith(".gguf"):
                size = os.path.getsize(os.path.join(model_dir, model)) / (1024 * 1024)
                print(f"  {model} ({size:.1f} MB)")

    elif command == "download":
        if len(args) < 2:
            print("[GhostForge]: Please provide a model URL")
            return
        url = args[1]
        model_dir = os.path.expanduser("~/.ghostforge/models")
        os.makedirs(model_dir, exist_ok=True)
        model_name = url.split("/")[-1]
        model_path = os.path.join(model_dir, model_name)

        print(f"[GhostForge]: Downloading model from {url}")
        try:
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            block_size = 1024
            with open(model_path, "wb") as f:
                for data in response.iter_content(block_size):
                    f.write(data)
            print(f"[GhostForge]: Model downloaded to {model_path}")
        except Exception as e:
            print(f"[GhostForge]: Error downloading model: {e}")

    elif command == "switch":
        if len(args) < 2:
            print("[GhostForge]: Please provide a model name")
            return
        model_name = args[1]
        model_dir = os.path.expanduser("~/.ghostforge/models")
        model_path = os.path.join(model_dir, model_name)

        if not os.path.exists(model_path):
            print(f"[GhostForge]: Model '{model_name}' not found")
            return

        config_path = os.path.join(CONFIG_DIR, "config.yaml")
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            config.setdefault("model", {})["path"] = model_path
            with open(config_path, "w") as f:
                yaml.dump(config, f)
            print(f"[GhostForge]: Switched to model '{model_name}'")
            print("[GhostForge]: Please restart the shell to apply changes")
        except Exception as e:
            print(f"[GhostForge]: Error switching model: {e}")

    elif command == "info":
        model_config = self.config.get("model", {})
        current_model = model_config.get("path", "Not set")
        print("\n[GhostForge]: Current model configuration:")
        print(f"  Path: {current_model}")
        print(f"  Context size: {model_config.get('context_size', 2048)}")
        print(f"  GPU layers: {model_config.get('gpu_layers', 0)}")
        print(f"  Threads: {model_config.get('threads', 'Auto')}")
        print(f"  F16 KV: {model_config.get('f16_kv', True)}")

    else:
        print("[GhostForge]: Invalid subcommand. Use list, download, switch, or info")

def do_prompts(self, arg):
    """List or view available prompt templates.
    Usage: prompts [list|view <name>|info <name>]
    Examples:
      prompts list          - List all available prompts with descriptions
      prompts view docker   - View the docker analysis prompt template
      prompts info api      - Show detailed information about the API analysis prompt
    """
    args = shlex.split(arg) if arg else ["list"]
    action = args[0]

    if action == "list":
        if not os.path.exists(PROMPT_DIR):
            print("[GhostForge]: No prompts directory found.")
            return

        prompts = [f[:-5] for f in os.listdir(PROMPT_DIR) if f.endswith('.yaml')]
        if not prompts:
            print("[GhostForge]: No prompt templates found.")
            return

        # Dynamically discover categories based on prompt names and content
        categories = {}
        for prompt in prompts:
            try:
                with open(os.path.join(PROMPT_DIR, f"{prompt}.yaml"), 'r') as f:
                    content = yaml.safe_load(f)
                    desc = content.get('description', '')
                    
                    # Determine category based on filename patterns and content
                    category = None
                    if prompt.endswith('_analysis'):
                        if prompt.startswith('security_'):
                            category = "Security Analysis"
                        elif prompt.startswith('performance_'):
                            category = "Performance Analysis"
                        else:
                            category = "General Analysis"
                    elif prompt.startswith('security_'):
                        category = "Security"
                    elif prompt in ['file_change', 'command_output']:
                        category = "Monitoring"
                    elif 'test' in prompt:
                        category = "Testing"
                    elif 'docker' in prompt or 'kubernetes' in prompt:
                        category = "Infrastructure"
                    elif 'api' in prompt:
                        category = "API"
                    elif 'database' in prompt or 'db' in prompt:
                        category = "Database"
                    elif 'log' in prompt:
                        category = "Logging"
                    else:
                        category = "Other"

                    # Store prompt info in the category
                    if category not in categories:
                        categories[category] = []
                    categories[category].append({
                        'name': prompt,
                        'description': desc
                    })
            except Exception as e:
                print(f"  {prompt:<20} [Error reading template: {str(e)}]")

        # Display prompts by category
        print("\n[GhostForge]: Available Prompt Templates:")
        for category in sorted(categories.keys()):
            print(f"\n{category}:")
            for prompt in sorted(categories[category], key=lambda x: x['name']):
                desc = prompt['description']
                if desc:
                    # Format the description to wrap at 60 characters
                    wrapped_desc = [desc[i:i+60] for i in range(0, len(desc), 60)]
                    print(f"  {prompt['name']:<20} {wrapped_desc[0]}")
                    for line in wrapped_desc[1:]:
                        print(f"  {' '*20} {line}")
                else:
                    print(f"  {prompt['name']:<20} [No description available]")

    elif action == "view" and len(args) > 1:
        template_name = args[1]
        template_path = os.path.join(PROMPT_DIR, f"{template_name}.yaml")
        
        if not os.path.exists(template_path):
            print(f"[GhostForge]: Prompt template '{template_name}' not found.")
            return

        try:
            with open(template_path, 'r') as f:
                content = yaml.safe_load(f)
                desc = content.get('description', '[No description available]')
                print(f"\n[GhostForge]: {template_name} - {desc}")
                print("\nTemplate Content:")
                print(yaml.dump(content))
        except Exception as e:
            print(f"[GhostForge]: Error reading template: {e}")

    elif action == "info" and len(args) > 1:
        template_name = args[1]
        template_path = os.path.join(PROMPT_DIR, f"{template_name}.yaml")
        
        if not os.path.exists(template_path):
            print(f"[GhostForge]: Prompt template '{template_name}' not found.")
            return

        try:
            with open(template_path, 'r') as f:
                content = yaml.safe_load(f)
            
            print(f"\n[GhostForge]: {template_name}")
            print("\nDescription:")
            desc = content.get('description', '[No description available]')
            # Format the description to wrap at 80 characters
            for i in range(0, len(desc), 80):
                print(desc[i:i+80])
            
            print("\nStructure:")
            for key in content.keys():
                if key != 'description':
                    print(f"- {key}")
            
            # Show available variables
            variables = []
            template_str = yaml.dump(content)
            for match in Template.pattern.findall(template_str):
                var = match[2].strip()
                if var not in variables:
                    variables.append(var)
            
            if variables:
                print("\nAvailable Variables:")
                for var in variables:
                    print(f"- {var}")
            
        except Exception as e:
            print(f"[GhostForge]: Error reading template: {e}")

    else:
        print("[GhostForge]: Invalid action. Use 'list', 'view <name>', or 'info <name>'")

def load_recipes():
    """Load all recipe files for project detection."""
    recipe_dir = os.path.join(os.path.dirname(__file__), "recipes")
    recipes = {}
    
    recipe_files = [
        "languages.yaml",
        "build_tools.yaml",
        "environments.yaml",
        "testing.yaml",
        "ci_cd.yaml",
        "documentation.yaml",
        "config.yaml"
    ]
    
    for recipe_file in recipe_files:
        try:
            with open(os.path.join(recipe_dir, recipe_file), 'r') as f:
                recipes[recipe_file[:-5]] = yaml.safe_load(f)
        except Exception as e:
            print(f"[GhostForge]: Warning - Could not load recipe file {recipe_file}: {e}")
    
    return recipes

def do_detect(self, arg):
    """Detect and analyze project characteristics.
    Usage: detect [path]
    Example: detect .
    
    Analyzes the project directory to identify:
    - Programming languages used
    - Build tools and package managers
    - Virtual environments
    - Dependencies and requirements
    - Configuration files
    - Testing frameworks
    - CI/CD configurations
    - Documentation formats
    """
    path = arg.strip() if arg else "."
    if not os.path.exists(path):
        print(f"[GhostForge]: Path '{path}' does not exist.")
        return

    print(f"\n[GhostForge]: Analyzing project in {os.path.abspath(path)}...")

    # Load recipes
    recipes = load_recipes()

    # Initialize findings with categories from recipes
    findings = {
        "languages": {},  # Will store language -> {count, category}
        "build_tools": set(),
        "environments": set(),
        "dependencies": set(),
        "testing": set(),
        "ci_cd": set(),
        "documentation": {},  # Will store doc_type -> {count, category}
        "config": set(),
        "containers": {"docker": False, "kubernetes": False}
    }

    # Walk through the project directory
    for root, dirs, files in os.walk(path):
        # Skip common directories to ignore
        if any(ignore in root for ignore in [".git", "__pycache__", "node_modules", ".pytest_cache"]):
            continue

        rel_path = os.path.relpath(root, path)

        # Check directories for each recipe type
        for recipe_name, recipe in recipes.items():
            for pattern, info in recipe["patterns"].items():
                if info.get("type") == "directory":
                    if pattern.rstrip("/") in dirs:
                        category_name = recipe_name.replace("_", " ").title()
                        findings[recipe_name].add(f"{info['name']} ({info['category']})")

        # Check files
        for file in files:
            file_path = os.path.join(root, file)
            
            # Check each recipe type
            for recipe_name, recipe in recipes.items():
                for pattern, info in recipe["patterns"].items():
                    matched = False
                    if info.get("type") == "file" and file == pattern:
                        matched = True
                    elif info.get("type") == "glob" and fnmatch.fnmatch(file, pattern):
                        matched = True
                    
                    if matched:
                        if recipe_name == "languages":
                            if info["name"] not in findings["languages"]:
                                findings["languages"][info["name"]] = {"count": 0, "category": info["category"]}
                            findings["languages"][info["name"]]["count"] += 1
                        elif recipe_name == "documentation" and pattern.endswith((".md", ".rst")):
                            if info["name"] not in findings["documentation"]:
                                findings["documentation"][info["name"]] = {"count": 0, "category": info["category"]}
                            findings["documentation"][info["name"]]["count"] += 1
                        else:
                            findings[recipe_name].add(f"{info['name']} ({info['category']})")
                        
                        # Parse dependencies if supported
                        if info.get("can_parse_deps"):
                            try:
                                if pattern == "requirements.txt":
                                    with open(file_path, "r") as f:
                                        for line in f:
                                            line = line.strip()
                                            if line and not line.startswith("#"):
                                                findings["dependencies"].add(f"Python: {line.split('==')[0]}")
                                elif pattern == "package.json":
                                    with open(file_path, "r") as f:
                                        data = json.load(f)
                                        for field in info.get("dep_fields", ["dependencies"]):
                                            for dep in data.get(field, {}):
                                                findings["dependencies"].add(f"Node.js: {dep}")
                            except Exception as e:
                                print(f"[GhostForge]: Warning - Could not parse dependencies in {file_path}: {e}")

            # Special checks for Docker and Kubernetes
            if file == "Dockerfile" or file.endswith(".dockerfile"):
                findings["containers"]["docker"] = True
            elif file.endswith((".yaml", ".yml")):
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                        if "kind: Deployment" in content or "kind: Pod" in content:
                            findings["containers"]["kubernetes"] = True
                except Exception:
                    pass

    # Print findings
    print("\n[GhostForge]: Project Analysis Results")
    
    # Languages by category
    if findings["languages"]:
        print("\nLanguages by Category:")
        categories = {}
        for lang, info in findings["languages"].items():
            if info["category"] not in categories:
                categories[info["category"]] = []
            categories[info["category"]].append(f"{lang} ({info['count']} files)")
        
        for category in sorted(categories.keys()):
            print(f"\n  {category}:")
            for lang in sorted(categories[category]):
                print(f"    - {lang}")

    if findings["build_tools"]:
        print("\nBuild Tools:")
        for tool in sorted(findings["build_tools"]):
            print(f"  - {tool}")

    if findings["environments"]:
        print("\nEnvironments:")
        for env in sorted(findings["environments"]):
            print(f"  - {env}")

    if findings["dependencies"]:
        print("\nKey Dependencies:")
        for dep in sorted(findings["dependencies"])[:10]:
            print(f"  - {dep}")
        if len(findings["dependencies"]) > 10:
            print(f"  ... and {len(findings['dependencies']) - 10} more")

    if findings["testing"]:
        print("\nTesting:")
        for test in sorted(findings["testing"]):
            print(f"  - {test}")

    if findings["ci_cd"]:
        print("\nCI/CD Systems:")
        for ci in sorted(findings["ci_cd"]):
            print(f"  - {ci}")

    if findings["documentation"]:
        print("\nDocumentation:")
        categories = {}
        for doc, info in findings["documentation"].items():
            if info["category"] not in categories:
                categories[info["category"]] = []
            categories[info["category"]].append(f"{doc} ({info['count']} files)")
        
        for category in sorted(categories.keys()):
            print(f"\n  {category}:")
            for doc in sorted(categories[category]):
                print(f"    - {doc}")

    if findings["config"]:
        print("\nConfiguration:")
        for config in sorted(findings["config"]):
            print(f"  - {config}")

    print("\nContainer Technologies:")
    print(f"  - Docker: {'Yes' if findings['containers']['docker'] else 'No'}")
    print(f"  - Kubernetes: {'Yes' if findings['containers']['kubernetes'] else 'No'}")

    # Generate summary
    print("\nProject Summary:")
    if findings["languages"]:
        primary_lang = max(findings["languages"].items(), key=lambda x: x[1]["count"])
        print(f"  Primary Language: {primary_lang[0]} ({primary_lang[1]['category']})")
    if findings["build_tools"]:
        print(f"  Build System: {next(iter(findings['build_tools']))}")
    if findings["environments"]:
        print(f"  Environment: {next(iter(findings['environments']))}")
    if findings["testing"]:
        print(f"  Testing Framework: {next(iter(findings['testing']))}")
    if findings["ci_cd"]:
        print(f"  CI/CD: {next(iter(findings['ci_cd']))}")
    print(f"  Containerized: {'Yes' if findings['containers']['docker'] else 'No'}") 