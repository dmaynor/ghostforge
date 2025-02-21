"""BuildBot interactive shell."""

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
from .utils import load_prompt

# Load environment variables with defaults
MODEL_URL = os.getenv("BUILDBOT_MODEL_URL", "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-GGUF/resolve/main/tinyllama-1.1b-chat.Q4_K_M.gguf")
MODEL_DIR = os.getenv("BUILDBOT_MODEL_DIR", os.path.expanduser("~/.buildbot/models"))
MODEL_PATH = os.path.join(MODEL_DIR, "tinyllama-1.1b-chat.Q4_K_M.gguf")
PROMPT_DIR = os.getenv("BUILDBOT_PROMPT_DIR", os.path.expanduser("~/.buildbot/prompts"))
CONFIG_DIR = os.getenv("BUILDBOT_CONFIG_DIR", os.path.expanduser("~/.buildbot"))

# Ensure the directories exist
os.makedirs(PROMPT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

def check_dependency(module_name):
    """Check if a Python module is installed."""
    if importlib.util.find_spec(module_name) is None:
        raise ImportError(f"[BuildBot]: Missing dependency '{module_name}'. Please install it using: pip install {module_name}")

check_dependency("llama_cpp")
from llama_cpp import Llama

def load_prompt(prompt_name, context={}):
    """Load and render a YAML prompt file."""
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
    intro = "BuildBot REPL v1.0\nType 'help' for commands, or press TAB to list all commands."
    prompt = "> "
    history = []  # Stores past commands
    watch_threads = {}  # Stores active watch threads

    # Command categories for better organization
    COMMAND_CATEGORIES = {
        "Core Commands": ["help", "exit"],
        "File Operations": ["index", "search", "analyze"],
        "Configuration": ["config", "prompt", "model", "prompts"],
        "Monitoring": ["watch", "unwatch", "watches"],
        "Analysis": ["docker", "analyze"],
        "History": ["history"]
    }

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

    def load_config(self):
        """Load BuildBot configuration."""
        print("[DEBUG]: Loading configuration file")
        try:
            with open(os.path.join(CONFIG_DIR, "config.yaml"), "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print("[BuildBot]: Warning - Config file not found. Using defaults.")
            return {}

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

    def init_database(self):
        """Initialize the SQLite database."""
        print("[DEBUG]: Initializing database")
        os.makedirs(CONFIG_DIR, exist_ok=True)
        conn = sqlite3.connect(os.path.join(CONFIG_DIR, "index.db"))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, path TEXT UNIQUE, content TEXT, last_modified TIMESTAMP)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_content ON files(content)")
        conn.commit()
        return conn

    def emptyline(self):
        """Handle empty line + Enter."""
        self.do_help("")

    def default(self, line):
        """Handle unknown commands."""
        print(f"[BuildBot]: Unknown command: {line}")
        print("Type 'help' for a list of commands or press TAB for command completion.")

    def completenames(self, text, *ignored):
        """Return list of command names matching the text."""
        commands = [name[3:] for name in self.get_names() if name.startswith('do_')]
        if not text:
            return commands
        return [cmd for cmd in commands if cmd.startswith(text)]

    def complete_analyze(self, text, line, begidx, endidx):
        """Command completion for analyze command."""
        args = line[:endidx].split()
        if len(args) <= 2:  # Complete file paths
            if not text:
                completions = os.listdir('.')
            else:
                completions = [f for f in os.listdir('.') 
                             if f.startswith(text)]
            return [f + ('/' if os.path.isdir(f) else '') for f in completions]
        elif len(args) == 3:  # Complete prompt names
            prompt_dir = os.path.join(PROMPT_DIR)
            if os.path.exists(prompt_dir):
                prompts = [f[:-5] for f in os.listdir(prompt_dir) 
                          if f.endswith('.yaml')]
                if not text:
                    return prompts
                return [p for p in prompts if p.startswith(text)]
        return []

    def complete_docker(self, text, line, begidx, endidx):
        """Command completion for docker command."""
        args = line[:endidx].split()
        if len(args) <= 2:
            options = ['container', 'image']
            if not text:
                return options
            return [opt for opt in options if opt.startswith(text)]
        elif len(args) == 3:
            if args[1] == 'container':
                try:
                    output = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}']).decode()
                    containers = output.splitlines()
                    if not text:
                        return containers
                    return [c for c in containers if c.startswith(text)]
                except:
                    return []
            elif args[1] == 'image':
                try:
                    output = subprocess.check_output(['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}']).decode()
                    images = output.splitlines()
                    if not text:
                        return images
                    return [i for i in images if i.startswith(text)]
                except:
                    return []
        return []

    def complete_watch(self, text, line, begidx, endidx):
        """Command completion for watch command."""
        args = line[:endidx].split()
        if len(args) <= 2:
            options = ['file', 'command']
            if not text:
                return options
            return [opt for opt in options if opt.startswith(text)]
        elif len(args) == 3 and args[1] == 'file':
            if not text:
                completions = os.listdir('.')
            else:
                completions = [f for f in os.listdir('.') 
                             if f.startswith(text)]
            return [f + ('/' if os.path.isdir(f) else '') for f in completions]
        return []

    def complete_unwatch(self, text, line, begidx, endidx):
        """Command completion for unwatch command."""
        if not text:
            return list(self.watch_threads.keys())
        return [w for w in self.watch_threads.keys() if w.startswith(text)]

    def complete_config(self, text, line, begidx, endidx):
        """Command completion for config command."""
        options = ['view', 'edit', 'set', 'unset']
        if not text:
            return options
        return [opt for opt in options if opt.startswith(text)]

    def complete_model(self, text, line, begidx, endidx):
        """Command completion for model command."""
        args = line[:endidx].split()
        if len(args) <= 2:
            options = ['list', 'download', 'switch', 'info']
            if not text:
                return options
            return [opt for opt in options if opt.startswith(text)]
        elif len(args) == 3 and args[1] == 'switch':
            model_dir = os.path.expanduser("~/.buildbot/models")
            if os.path.exists(model_dir):
                models = [f for f in os.listdir(model_dir) if f.endswith('.gguf')]
                if not text:
                    return models
                return [m for m in models if m.startswith(text)]
        return []

    def complete_prompts(self, text, line, begidx, endidx):
        """Command completion for prompts command."""
        args = line[:endidx].split()
        
        # Complete actions
        if len(args) <= 2:
            actions = ['list', 'view', 'info']
            if not text:
                return actions
            return [a for a in actions if a.startswith(text)]
        
        # Complete template names for view and info actions
        elif len(args) == 3 and args[1] in ['view', 'info']:
            if os.path.exists(PROMPT_DIR):
                templates = [f[:-5] for f in os.listdir(PROMPT_DIR) 
                           if f.endswith('.yaml')]
                if not text:
                    return templates
                return [t for t in templates if t.startswith(text)]
        return []

    def get_command_categories(self):
        """Get all commands organized by category."""
        return self.COMMAND_CATEGORIES

    def print_topics(self, header, cmds, cmdlen, maxcol):
        """Override print_topics to group commands by category."""
        if not cmds:
            return

        if header == "Documented commands (type help <topic>):":
            print("\nAvailable Commands:")
            for category, commands in self.get_command_categories().items():
                print(f"\n{category}:")
                for cmd in commands:
                    doc = getattr(self, f'do_{cmd}').__doc__ or ''
                    print(f"  {cmd:<15} {doc.split('\n')[0]}")
            print("\nType 'help <command>' for detailed information about a command.")
            return

        super().print_topics(header, cmds, cmdlen, maxcol)

    # Import all the command methods from buildbot.py
    from .commands import (
        do_exit, do_index, do_search, do_analyze, do_prompt,
        do_config, do_docker, do_history, do_watch, do_unwatch,
        do_watches, do_help, do_model
    ) 