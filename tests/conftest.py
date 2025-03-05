"""Test fixtures for GhostForge unit tests."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    temp_dir = tempfile.mkdtemp(prefix="ghostforge_test_")
    old_cwd = os.getcwd()
    os.chdir(temp_dir)
    
    yield Path(temp_dir)
    
    # Clean up
    os.chdir(old_cwd)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_config(temp_workspace):
    """Create a mock configuration directory."""
    config_dir = temp_workspace / ".ghostforge"
    config_dir.mkdir(exist_ok=True)
    
    # Create a basic config file
    config_file = config_dir / "config.yaml"
    config_file.write_text("""
model:
  type: llama
  api_key: test_api_key
  model_name: test-model

prompts_directory: prompts
database_path: .ghostforge/ghostforge.db
exclude_patterns:
  - "*.pyc"
  - "__pycache__/*"
  - ".git/*"
  - "*.log"
  - "*.bin"
  - "*.png"
  - "*.jpg"
""")
    
    # Create prompts directory
    prompts_dir = config_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    
    # Create a default analysis prompt
    default_prompt = prompts_dir / "default_analysis.yaml"
    default_prompt.write_text("""
name: default_analysis
description: Default analysis prompt
system_prompt: |
  You are an AI assistant specialized in code analysis.
user_template: |
  Analyze this file and provide suggestions for improvements:
  
  Filename: {{filename}}
  
  Content:
  ```
  {{content}}
  ```
""")
    
    # Create an error analysis prompt
    error_prompt = prompts_dir / "error_analysis.yaml"
    error_prompt.write_text("""
name: error_analysis
description: Error analysis prompt
system_prompt: |
  You are an AI assistant specialized in finding errors in code.
user_template: |
  Analyze this file for errors and potential bugs:
  
  Filename: {{filename}}
  
  Content:
  ```
  {{content}}
  ```
""")
    
    yield config_dir

@pytest.fixture
def mock_db(temp_workspace):
    """Create a mock database with some sample entries."""
    db_dir = temp_workspace / ".ghostforge"
    db_dir.mkdir(exist_ok=True)
    
    # Create a simple mock database
    db_file = db_dir / "ghostforge.db"
    
    # We won't actually create a real database here,
    # as the individual tests can mock database operations
    # This fixture is mainly to provide the expected path
    
    yield db_file

@pytest.fixture
def sample_python_file(temp_workspace):
    """Create a sample Python file for testing."""
    file_path = temp_workspace / "sample.py"
    file_path.write_text("""
def add(a, b):
    return a + b

def divide(a, b):
    # Missing error handling for division by zero
    return a / b

# Example usage
result = add(10, 20)
print(f"Result: {result}")

# This will cause an error if b is zero
quotient = divide(10, 2)
print(f"Quotient: {quotient}")
""")
    
    yield file_path

@pytest.fixture
def sample_dockerfile(temp_workspace):
    """Create a sample Dockerfile for testing."""
    file_path = temp_workspace / "Dockerfile"
    file_path.write_text("""
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Security issue: Running as root (no USER instruction)
# Security issue: Using environment variable for secrets
ENV API_KEY="secret_key_12345"

EXPOSE 8080

CMD ["python", "app.py"]
""")
    
    yield file_path

@pytest.fixture
def sample_kubernetes_manifests(temp_workspace):
    """Create sample Kubernetes manifest files for testing."""
    k8s_dir = temp_workspace / "k8s"
    k8s_dir.mkdir(exist_ok=True)
    
    # Create a deployment manifest
    deployment_file = k8s_dir / "deployment.yaml"
    deployment_file.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app-container
        image: my-app:latest
        ports:
        - containerPort: 8080
        securityContext:
          privileged: true
          capabilities:
            add: ["ALL"]
        env:
        - name: API_KEY
          value: "secret-api-key-12345"
""")
    
    # Create a service manifest
    service_file = k8s_dir / "service.yaml"
    service_file.write_text("""
apiVersion: v1
kind: Service
metadata:
  name: web-app-service
  namespace: default
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
""")
    
    # Create an ingress manifest
    ingress_file = k8s_dir / "ingress.yaml"
    ingress_file.write_text("""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: default
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-app-service
            port:
              number: 80
""")
    
    yield k8s_dir

@pytest.fixture
def sample_ci_files(temp_workspace):
    """Create sample CI/CD configuration files for testing."""
    # GitHub Actions workflow
    github_dir = temp_workspace / ".github" / "workflows"
    github_dir.mkdir(parents=True, exist_ok=True)
    github_file = github_dir / "ci.yml"
    github_file.write_text("""
name: CI Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: pytest
    - name: Build and push
      uses: docker/build-push-action@latest
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
        push: true
        tags: myapp
""")
    
    # GitLab CI configuration
    gitlab_file = temp_workspace / ".gitlab-ci.yml"
    gitlab_file.write_text("""
stages:
  - test
  - build
  - deploy

variables:
  DB_PASSWORD: "insecure_password"
  API_TOKEN: "1234567890abcdef"

test:
  stage: test
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - pytest

build:
  stage: build
  image: docker:latest
  script:
    - docker build -t myapp .
    - docker push myapp

deploy_production:
  stage: deploy
  script:
    - curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com/deploy/prod
""")
    
    # Jenkins configuration
    jenkins_file = temp_workspace / "Jenkinsfile"
    jenkins_file.write_text("""
pipeline {
    agent any
    
    environment {
        API_KEY = 'secret-key-12345'
    }
    
    stages {
        stage('Build') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'python setup.py build'
            }
        }
        
        stage('Test') {
            steps {
                sh 'pytest'
            }
        }
        
        stage('Deploy') {
            steps {
                sh 'curl -H "Authorization: Bearer ${API_KEY}" https://api.example.com/deploy'
                sh 'docker build -t myapp .'
                sh 'docker push myapp:latest'
            }
        }
    }
}
""")
    
    yield {
        "github_actions": github_file,
        "gitlab_ci": gitlab_file,
        "jenkins": jenkins_file
    } 