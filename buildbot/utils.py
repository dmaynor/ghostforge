"""Utility functions for BuildBot."""

import os
import yaml
from jinja2 import Template

def load_prompt(prompt_name, context={}):
    """Load and render a YAML prompt file."""
    prompt_dir = os.getenv("BUILDBOT_PROMPT_DIR", os.path.expanduser("~/.buildbot/prompts"))
    prompt_path = os.path.join(prompt_dir, f"{prompt_name}.yaml")
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