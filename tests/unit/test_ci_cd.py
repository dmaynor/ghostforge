"""Unit tests for CI/CD pipeline analysis functionality."""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import GhostForge components
from ghostforge.ci_cd import CICDAnalyzer

class TestCICDAnalyzer:
    """Test suite for CI/CD pipeline analysis functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Fixture to provide a CICDAnalyzer instance."""
        return CICDAnalyzer()
    
    def test_detect_ci_system(self, analyzer, temp_workspace):
        """Test detection of CI/CD system type from configuration files."""
        # Create test CI/CD configuration files
        
        # GitHub Actions workflow
        github_dir = temp_workspace / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)
        github_workflow = github_dir / "ci.yml"
        github_workflow.write_text("""
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
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
    - name: Run tests
      run: pytest
""")
        
        # GitLab CI configuration
        gitlab_ci = temp_workspace / ".gitlab-ci.yml"
        gitlab_ci.write_text("""
stages:
  - test
  - build
  - deploy

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
""")
        
        # Jenkins configuration
        jenkins_file = temp_workspace / "Jenkinsfile"
        jenkins_file.write_text("""
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest'
            }
        }
    }
}
""")
        
        # Test CI system detection
        results = analyzer.detect_ci_systems(str(temp_workspace))
        
        # Check that all CI systems are detected
        assert "github_actions" in results
        assert "gitlab_ci" in results
        assert "jenkins" in results
        
        # Check file paths are correct
        assert results["github_actions"] == [str(github_workflow)]
        assert results["gitlab_ci"] == [str(gitlab_ci)]
        assert results["jenkins"] == [str(jenkins_file)]
    
    def test_analyze_github_actions(self, analyzer, temp_workspace):
        """Test analyzing GitHub Actions workflow."""
        # Create a GitHub Actions workflow with security issues
        github_dir = temp_workspace / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)
        github_workflow = github_dir / "ci.yml"
        github_workflow.write_text("""
name: CI Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    # Security issue: No timeout - could run indefinitely
    steps:
    - uses: actions/checkout@v2
      # Security issue: No commit/branch specified in checkout
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
      # Security issue: No action version pinned
      uses: docker/build-push-action@latest
      with:
        # Security issue: Hardcoded credentials
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
        # Security issue: No image tag - uses latest by default
        push: true
        tags: myapp
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    # Security issue: No branch protection for deployment
    steps:
    - name: Deploy to production
      # Security issue: Using a third-party action without hash
      uses: some-vendor/deploy-action@v1
      with:
        # Security issue: Hardcoded credential
        api-key: "1234567890abcdef"
""")
        
        # Mock the LLM analysis
        def mock_analyze_github_actions(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "high", "description": "No commit/branch specified in checkout action", "line": 10},
                    {"severity": "high", "description": "Docker action version not pinned to specific hash", "line": 24},
                    {"severity": "critical", "description": "Hardcoded API key in workflow file", "line": 41},
                    {"severity": "high", "description": "Using third-party action without hash pinning", "line": 38}
                ],
                "best_practices": [
                    {"severity": "medium", "description": "No timeout specified for jobs", "line": 9},
                    {"severity": "medium", "description": "No branch protection for deployment job", "line": 30},
                    {"severity": "medium", "description": "Docker image not tagged with specific version", "line": 27}
                ]
            }
        
        # Patch the analyze method
        with patch.object(analyzer, 'analyze_github_actions', side_effect=mock_analyze_github_actions):
            # Analyze the GitHub Actions workflow
            results = analyzer.analyze_ci_cd(str(temp_workspace))
            
            # Check that security issues are identified
            assert "github_actions" in results
            github_results = results["github_actions"][str(github_workflow)]
            
            assert len(github_results["security_issues"]) == 4
            assert any("checkout action" in issue["description"] for issue in github_results["security_issues"])
            assert any("Docker action" in issue["description"] for issue in github_results["security_issues"])
            assert any("API key" in issue["description"] for issue in github_results["security_issues"])
            assert any("third-party action" in issue["description"] for issue in github_results["security_issues"])
            
            # Check that best practices are identified
            assert len(github_results["best_practices"]) == 3
            assert any("timeout" in issue["description"] for issue in github_results["best_practices"])
            assert any("branch protection" in issue["description"] for issue in github_results["best_practices"])
            assert any("Docker image" in issue["description"] for issue in github_results["best_practices"])
    
    def test_analyze_gitlab_ci(self, analyzer, temp_workspace):
        """Test analyzing GitLab CI configuration."""
        # Create a GitLab CI configuration with security issues
        gitlab_ci = temp_workspace / ".gitlab-ci.yml"
        gitlab_ci.write_text("""
stages:
  - test
  - build
  - deploy

variables:
  # Security issue: Credentials in variables
  DB_PASSWORD: "insecure_password"
  API_TOKEN: "1234567890abcdef"

test:
  stage: test
  image: python:3.9  # Security issue: No specific version
  script:
    - pip install -r requirements.txt
    - pytest
  # Best practice issue: No artifacts for test results

build:
  stage: build
  image: docker:latest  # Security issue: Using latest tag
  script:
    # Security issue: No authentication to Docker registry
    - docker build -t myapp .
    - docker push myapp
  # Best practice issue: No caching

deploy_staging:
  stage: deploy
  script:
    # Security issue: Using curl with credentials
    - curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com/deploy
  # Security issue: No environment defined
  # Best practice issue: No rules to limit when job runs

deploy_production:
  stage: deploy
  script:
    - curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com/deploy/prod
  # Security issue: No manual approval for production
  # Best practice issue: No rollback strategy
""")
        
        # Mock the LLM analysis
        def mock_analyze_gitlab_ci(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "critical", "description": "Credentials in plaintext variables", "line": 7},
                    {"severity": "high", "description": "No authentication to Docker registry", "line": 23},
                    {"severity": "high", "description": "Using curl with credentials in script", "line": 32},
                    {"severity": "medium", "description": "No environment defined for deployment", "line": 29}
                ],
                "best_practices": [
                    {"severity": "medium", "description": "Using latest tag for Docker image", "line": 18},
                    {"severity": "medium", "description": "No test artifacts preserved", "line": 14},
                    {"severity": "medium", "description": "No caching configured", "line": 25},
                    {"severity": "high", "description": "No manual approval for production deployment", "line": 39},
                    {"severity": "medium", "description": "No rollback strategy defined", "line": 41}
                ]
            }
        
        # Patch the analyze method
        with patch.object(analyzer, 'analyze_gitlab_ci', side_effect=mock_analyze_gitlab_ci):
            # Analyze the GitLab CI configuration
            results = analyzer.analyze_ci_cd(str(temp_workspace))
            
            # Check that security issues are identified
            assert "gitlab_ci" in results
            gitlab_results = results["gitlab_ci"][str(gitlab_ci)]
            
            assert len(gitlab_results["security_issues"]) == 4
            assert any("Credentials" in issue["description"] for issue in gitlab_results["security_issues"])
            assert any("Docker registry" in issue["description"] for issue in gitlab_results["security_issues"])
            assert any("curl with credentials" in issue["description"] for issue in gitlab_results["security_issues"])
            assert any("environment" in issue["description"] for issue in gitlab_results["security_issues"])
            
            # Check that best practices are identified
            assert len(gitlab_results["best_practices"]) == 5
            assert any("latest tag" in issue["description"] for issue in gitlab_results["best_practices"])
            assert any("artifacts" in issue["description"] for issue in gitlab_results["best_practices"])
            assert any("caching" in issue["description"] for issue in gitlab_results["best_practices"])
            assert any("manual approval" in issue["description"] for issue in gitlab_results["best_practices"])
            assert any("rollback" in issue["description"] for issue in gitlab_results["best_practices"])
    
    def test_analyze_jenkinsfile(self, analyzer, temp_workspace):
        """Test analyzing Jenkinsfile."""
        # Create a Jenkinsfile with security issues
        jenkins_file = temp_workspace / "Jenkinsfile"
        jenkins_file.write_text("""
pipeline {
    agent any  // Security issue: Running on any agent without constraints
    
    environment {
        // Security issue: Credentials in environment variables
        API_KEY = 'secret-key-12345'
        // Best practice: Using credentials binding
        DOCKER_CREDS = credentials('docker-hub-credentials')
    }
    
    stages {
        stage('Build') {
            steps {
                // Security issue: Using shell command directly
                sh 'pip install -r requirements.txt'
                sh 'python setup.py build'
            }
            // Best practice issue: No timeout
        }
        
        stage('Test') {
            steps {
                sh 'pytest'
            }
            // Best practice issue: No test result archiving
        }
        
        stage('Deploy') {
            // Security issue: No approval for deployment
            steps {
                // Security issue: Using credentials in shell command
                sh 'curl -H "Authorization: Bearer ${API_KEY}" https://api.example.com/deploy'
                
                // Best practice issue: No error handling
                sh 'docker build -t myapp .'
                sh 'docker push myapp:latest'  // Security issue: Using latest tag
            }
        }
    }
    
    // Best practice issue: No post-actions for cleanup or notifications
}
""")
        
        # Mock the LLM analysis
        def mock_analyze_jenkinsfile(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "high", "description": "Running on any agent without constraints", "line": 2},
                    {"severity": "critical", "description": "Credentials in plaintext environment variables", "line": 6},
                    {"severity": "high", "description": "Using credentials in shell command", "line": 32},
                    {"severity": "medium", "description": "No approval gate for deployment", "line": 28}
                ],
                "best_practices": [
                    {"severity": "medium", "description": "No timeout specified for build stage", "line": 17},
                    {"severity": "medium", "description": "No test result archiving", "line": 22},
                    {"severity": "medium", "description": "No error handling in deploy stage", "line": 35},
                    {"severity": "medium", "description": "Using latest tag for Docker image", "line": 36},
                    {"severity": "medium", "description": "No post-actions for cleanup or notifications", "line": 39}
                ]
            }
        
        # Patch the analyze method
        with patch.object(analyzer, 'analyze_jenkinsfile', side_effect=mock_analyze_jenkinsfile):
            # Analyze the Jenkinsfile
            results = analyzer.analyze_ci_cd(str(temp_workspace))
            
            # Check that security issues are identified
            assert "jenkins" in results
            jenkins_results = results["jenkins"][str(jenkins_file)]
            
            assert len(jenkins_results["security_issues"]) == 4
            assert any("agent" in issue["description"] for issue in jenkins_results["security_issues"])
            assert any("Credentials" in issue["description"] for issue in jenkins_results["security_issues"])
            assert any("shell command" in issue["description"] for issue in jenkins_results["security_issues"])
            assert any("approval" in issue["description"] for issue in jenkins_results["security_issues"])
            
            # Check that best practices are identified
            assert len(jenkins_results["best_practices"]) == 5
            assert any("timeout" in issue["description"] for issue in jenkins_results["best_practices"])
            assert any("test result" in issue["description"] for issue in jenkins_results["best_practices"])
            assert any("error handling" in issue["description"] for issue in jenkins_results["best_practices"])
            assert any("latest tag" in issue["description"] for issue in jenkins_results["best_practices"])
            assert any("post-actions" in issue["description"] for issue in jenkins_results["best_practices"])
    
    def test_generate_remediation(self, analyzer):
        """Test generating remediation for CI/CD issues."""
        # Issues to remediate
        issues = {
            "security_issues": [
                {"severity": "critical", "description": "Credentials in plaintext environment variables", "line": 6},
                {"severity": "high", "description": "No authentication to Docker registry", "line": 23}
            ],
            "best_practices": [
                {"severity": "medium", "description": "No timeout specified for build stage", "line": 17},
                {"severity": "high", "description": "No manual approval for production deployment", "line": 39}
            ]
        }
        
        # Mock the LLM remediation
        def mock_generate_remediation(*args, **kwargs):
            return {
                "remediation_steps": [
                    {
                        "issue": "Credentials in plaintext environment variables",
                        "solution": "Use secrets management instead of hardcoding credentials",
                        "example": """
# GitHub Actions example
env:
  # Remove hardcoded credentials
  # API_KEY: "1234567890abcdef"

# Instead use secrets
steps:
  - name: Deploy
    env:
      API_KEY: ${{ secrets.API_KEY }}
                        """
                    },
                    {
                        "issue": "No authentication to Docker registry",
                        "solution": "Add authentication to Docker registry before pushing images",
                        "example": """
# GitLab CI example
build:
  stage: build
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA
                        """
                    },
                    {
                        "issue": "No timeout specified for build stage",
                        "solution": "Add timeout to prevent jobs from running indefinitely",
                        "example": """
# GitHub Actions example
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      # ...

# Jenkins example
stage('Build') {
  options {
    timeout(time: 15, unit: 'MINUTES')
  }
  steps {
    // ...
  }
}
                        """
                    },
                    {
                        "issue": "No manual approval for production deployment",
                        "solution": "Add manual approval gate before production deployment",
                        "example": """
# GitLab CI example
deploy_production:
  stage: deploy
  script:
    - ./deploy-production.sh
  environment:
    name: production
  when: manual
  only:
    - master

# GitHub Actions example
jobs:
  deploy_prod:
    needs: build
    environment:
      name: production
      url: https://production.example.com
    runs-on: ubuntu-latest
    steps:
      # Deployment steps
                        """
                    }
                ]
            }
        
        # Patch the generate_remediation method
        with patch.object(analyzer, 'generate_ci_cd_remediation', side_effect=mock_generate_remediation):
            # Generate remediation
            remediation = analyzer.generate_remediation(issues)
            
            # Check remediation steps
            assert len(remediation["remediation_steps"]) == 4
            assert any("secrets" in step["solution"] for step in remediation["remediation_steps"])
            assert any("Docker registry" in step["solution"] for step in remediation["remediation_steps"])
            assert any("timeout" in step["solution"] for step in remediation["remediation_steps"])
            assert any("manual approval" in step["solution"] for step in remediation["remediation_steps"]) 