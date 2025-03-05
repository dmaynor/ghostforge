"""Unit tests for the file analysis functionality."""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import GhostForge components
from ghostforge.shell import GhostForgeShell

class MockLlama:
    """Mock LLM model for testing."""
    
    def create_completion(self, prompt, max_tokens=100, temperature=0.7, stop=None):
        """Mock completion generation."""
        response = "This is a mock analysis response.\n"
        if "error" in prompt.lower():
            response += "Found errors in the code: Missing error handling.\n"
        if "security" in prompt.lower():
            response += "Security issues: Hardcoded credentials detected.\n"
        if "dockerfile" in prompt.lower():
            response += "Dockerfile analysis: Running as root is a security concern.\n"
            
        return {
            "choices": [
                {
                    "text": response
                }
            ]
        }

@pytest.fixture
def mock_llm():
    """Fixture to provide a mock LLM model."""
    return MockLlama()

def test_analyze_text_file(temp_workspace, mock_config, mock_llm):
    """Test analyzing a text file."""
    # Create a test file
    test_file = temp_workspace / "test.txt"
    test_file.write_text("This is a sample text file with some content for analysis.")
    
    # Initialize shell
    shell = GhostForgeShell()
    shell.model = mock_llm
    
    # Capture analysis output
    analysis_results = []
    
    def mock_print(*args, **kwargs):
        analysis_results.append(" ".join(str(arg) for arg in args))
    
    # Save original print function
    original_print = print
    
    try:
        # Monkey patch print function
        __builtins__["print"] = mock_print
        
        # Run analysis on the test file
        os.chdir(temp_workspace)
        shell.do_analyze("test.txt")
        
        # Check results
        result_text = "\n".join(analysis_results)
        assert "mock analysis response" in result_text.lower()
        
    finally:
        # Restore original print function
        __builtins__["print"] = original_print

def test_analyze_code_with_errors(temp_workspace, mock_config, mock_llm):
    """Test analyzing code with errors."""
    # Create a test Python file with errors
    test_file = temp_workspace / "buggy.py"
    test_file.write_text("""
def divide(a, b):
    # Missing error handling for division by zero
    return a / b

result = divide(10, 0)  # Will cause an error
""")
    
    # Initialize shell
    shell = GhostForgeShell()
    shell.model = mock_llm
    
    # Capture analysis output
    analysis_results = []
    
    def mock_print(*args, **kwargs):
        analysis_results.append(" ".join(str(arg) for arg in args))
    
    # Save original print function
    original_print = print
    
    try:
        # Monkey patch print function
        __builtins__["print"] = mock_print
        
        # Run analysis on the test file
        os.chdir(temp_workspace)
        shell.do_analyze("buggy.py --prompt=error_analysis")
        
        # Check results
        result_text = "\n".join(analysis_results)
        assert "mock analysis response" in result_text.lower()
        assert "missing error handling" in result_text.lower()
        
    finally:
        # Restore original print function
        __builtins__["print"] = original_print

def test_analyze_dockerfile(temp_workspace, mock_config, mock_llm):
    """Test analyzing a Dockerfile."""
    # Create a test Dockerfile with issues
    test_file = temp_workspace / "Dockerfile"
    test_file.write_text("""
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
# Security issue: Running as root
CMD ["python", "app.py"]
""")
    
    # Initialize shell
    shell = GhostForgeShell()
    shell.model = mock_llm
    
    # Capture analysis output
    analysis_results = []
    
    def mock_print(*args, **kwargs):
        analysis_results.append(" ".join(str(arg) for arg in args))
    
    # Save original print function
    original_print = print
    
    try:
        # Monkey patch print function
        __builtins__["print"] = mock_print
        
        # Run analysis on the test file
        os.chdir(temp_workspace)
        shell.do_analyze("Dockerfile")
        
        # Check results
        result_text = "\n".join(analysis_results)
        assert "dockerfile analysis" in result_text.lower()
        assert "security concern" in result_text.lower()
        
    finally:
        # Restore original print function
        __builtins__["print"] = original_print

def test_analyze_with_custom_prompt(temp_workspace, mock_config, mock_llm):
    """Test analyzing with a custom prompt."""
    # Create a test file
    test_file = temp_workspace / "secrets.py"
    test_file.write_text("""
# Security issue: Hardcoded credentials
API_KEY = "1234567890abcdef"
DB_PASSWORD = "insecure_password"

def authenticate():
    return API_KEY
""")
    
    # Create a custom prompt
    prompt_dir = mock_config / "prompts"
    prompt_dir.mkdir(exist_ok=True)
    
    custom_prompt = prompt_dir / "security_scan.yaml"
    custom_prompt.write_text("""
name: security_scan
description: Security scan prompt
system_prompt: |
  You are a security scanner analyzing code for security issues.
user_template: |
  Analyze this file for security issues:
  
  Filename: {{filename}}
  
  Content:
  ```
  {{content}}
  ```
""")
    
    # Initialize shell
    shell = GhostForgeShell()
    shell.model = mock_llm
    
    # Capture analysis output
    analysis_results = []
    
    def mock_print(*args, **kwargs):
        analysis_results.append(" ".join(str(arg) for arg in args))
    
    # Save original print function
    original_print = print
    
    try:
        # Monkey patch print function
        __builtins__["print"] = mock_print
        
        # Run analysis on the test file with custom prompt
        os.chdir(temp_workspace)
        shell.do_analyze("secrets.py --prompt=security_scan")
        
        # Check results
        result_text = "\n".join(analysis_results)
        assert "security issues" in result_text.lower()
        assert "hardcoded credentials" in result_text.lower()
        
    finally:
        # Restore original print function
        __builtins__["print"] = original_print 