"""CI/CD integration for GhostForge."""

import os
import yaml
import json
import requests
from typing import Dict, Any, Optional, List

class CIProvider:
    """Base class for CI/CD providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_status(self) -> Dict[str, Any]:
        """Get CI/CD status."""
        raise NotImplementedError

    def trigger_pipeline(self, pipeline: str) -> Dict[str, Any]:
        """Trigger a CI/CD pipeline."""
        raise NotImplementedError

    def get_logs(self, job_id: str) -> str:
        """Get logs for a specific job."""
        raise NotImplementedError

class GitHubActions(CIProvider):
    """GitHub Actions integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = config.get("github_token")
        self.repo = config.get("repo")
        self.api_url = f"https://api.github.com/repos/{self.repo}"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get_status(self) -> Dict[str, Any]:
        """Get GitHub Actions workflow status."""
        response = requests.get(
            f"{self.api_url}/actions/runs",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def trigger_pipeline(self, workflow_id: str) -> Dict[str, Any]:
        """Trigger a GitHub Actions workflow."""
        response = requests.post(
            f"{self.api_url}/actions/workflows/{workflow_id}/dispatches",
            headers=self.headers,
            json={"ref": "main"}
        )
        response.raise_for_status()
        return {"status": "triggered"}

    def get_logs(self, run_id: str) -> str:
        """Get logs for a specific workflow run."""
        response = requests.get(
            f"{self.api_url}/actions/runs/{run_id}/logs",
            headers=self.headers
        )
        response.raise_for_status()
        return response.text

class GitLabCI(CIProvider):
    """GitLab CI integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.token = config.get("gitlab_token")
        self.project_id = config.get("project_id")
        self.api_url = f"https://gitlab.com/api/v4/projects/{self.project_id}"
        self.headers = {"PRIVATE-TOKEN": self.token}

    def get_status(self) -> Dict[str, Any]:
        """Get GitLab CI pipeline status."""
        response = requests.get(
            f"{self.api_url}/pipelines",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def trigger_pipeline(self, ref: str = "main") -> Dict[str, Any]:
        """Trigger a GitLab CI pipeline."""
        response = requests.post(
            f"{self.api_url}/pipeline",
            headers=self.headers,
            json={"ref": ref}
        )
        response.raise_for_status()
        return response.json()

    def get_logs(self, job_id: str) -> str:
        """Get logs for a specific job."""
        response = requests.get(
            f"{self.api_url}/jobs/{job_id}/trace",
            headers=self.headers
        )
        response.raise_for_status()
        return response.text

class JenkinsCI(CIProvider):
    """Jenkins CI integration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("jenkins_url")
        self.user = config.get("jenkins_user")
        self.token = config.get("jenkins_token")
        self.auth = (self.user, self.token)

    def get_status(self) -> Dict[str, Any]:
        """Get Jenkins job status."""
        response = requests.get(
            f"{self.url}/api/json",
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()

    def trigger_pipeline(self, job_name: str) -> Dict[str, Any]:
        """Trigger a Jenkins job."""
        response = requests.post(
            f"{self.url}/job/{job_name}/build",
            auth=self.auth
        )
        response.raise_for_status()
        return {"status": "triggered"}

    def get_logs(self, job_name: str, build_number: str) -> str:
        """Get logs for a specific build."""
        response = requests.get(
            f"{self.url}/job/{job_name}/{build_number}/consoleText",
            auth=self.auth
        )
        response.raise_for_status()
        return response.text

class CIManager:
    """Manager class for CI/CD integrations."""
    
    PROVIDERS = {
        "github": GitHubActions,
        "gitlab": GitLabCI,
        "jenkins": JenkinsCI
    }

    def __init__(self, config_file: str):
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
        self.providers = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize configured CI providers."""
        for provider, config in self.config.get("ci_providers", {}).items():
            if provider in self.PROVIDERS and config.get("enabled", False):
                self.providers[provider] = self.PROVIDERS[provider](config)

    def get_status(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get status from all or specific provider."""
        if provider:
            if provider not in self.providers:
                raise ValueError(f"Provider {provider} not configured")
            return {provider: self.providers[provider].get_status()}
        
        return {name: provider.get_status() 
                for name, provider in self.providers.items()}

    def trigger_pipeline(self, provider: str, pipeline: str) -> Dict[str, Any]:
        """Trigger a pipeline on specified provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        return self.providers[provider].trigger_pipeline(pipeline)

    def get_logs(self, provider: str, job_id: str) -> str:
        """Get logs from specified provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        return self.providers[provider].get_logs(job_id)

    def analyze_pipeline(self, provider: str, pipeline: str, model) -> Dict[str, Any]:
        """Analyze a pipeline using the LLM model."""
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")

        # Get pipeline status and logs
        status = self.providers[provider].get_status()
        logs = self.providers[provider].get_logs(pipeline)

        # Prepare prompt for analysis
        prompt = f"""Analyze this CI/CD pipeline status and logs:

Status:
{json.dumps(status, indent=2)}

Logs:
{logs}

Please provide:
1. Pipeline Status Summary
2. Key Events and Stages
3. Issues or Failures
4. Performance Metrics
5. Recommendations for Improvement
"""

        # Generate analysis using the model
        response = model.create_completion(
            prompt,
            max_tokens=1000,
            temperature=0.7,
            stop=["<end>"]
        )

        return {
            "status": status,
            "logs": logs,
            "analysis": response["choices"][0]["text"].strip()
        } 