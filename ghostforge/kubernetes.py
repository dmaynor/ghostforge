"""Kubernetes analysis and management for GhostForge."""

import os
import yaml
import json
import subprocess
from typing import Dict, Any, List, Optional

class KubernetesAnalyzer:
    """Kubernetes cluster analyzer and manager."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context = config.get("context")
        if self.context:
            os.environ["KUBECONFIG"] = self.context

    def _run_kubectl(self, command: List[str]) -> Dict[str, Any]:
        """Run kubectl command and return JSON output."""
        try:
            result = subprocess.run(
                ["kubectl"] + command + ["-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"kubectl command failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse kubectl output: {e}")

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status."""
        nodes = self._run_kubectl(["get", "nodes"])
        pods = self._run_kubectl(["get", "pods", "--all-namespaces"])
        services = self._run_kubectl(["get", "services", "--all-namespaces"])
        deployments = self._run_kubectl(["get", "deployments", "--all-namespaces"])

        return {
            "nodes": nodes,
            "pods": pods,
            "services": services,
            "deployments": deployments
        }

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get resource usage metrics."""
        metrics = self._run_kubectl(["top", "nodes"])
        pod_metrics = self._run_kubectl(["top", "pods", "--all-namespaces"])

        return {
            "nodes": metrics,
            "pods": pod_metrics
        }

    def get_pod_logs(self, pod_name: str, namespace: str = "default") -> str:
        """Get logs for a specific pod."""
        try:
            result = subprocess.run(
                ["kubectl", "logs", pod_name, "-n", namespace],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get pod logs: {e.stderr}")

    def analyze_deployment(self, name: str, namespace: str = "default") -> Dict[str, Any]:
        """Analyze a specific deployment."""
        deployment = self._run_kubectl(["get", "deployment", name, "-n", namespace])
        pods = self._run_kubectl(["get", "pods", "-l", f"app={name}", "-n", namespace])
        events = self._run_kubectl(["get", "events", "-n", namespace, 
                                  "--field-selector", f"involvedObject.name={name}"])

        return {
            "deployment": deployment,
            "pods": pods,
            "events": events
        }

    def analyze_service(self, name: str, namespace: str = "default") -> Dict[str, Any]:
        """Analyze a specific service."""
        service = self._run_kubectl(["get", "service", name, "-n", namespace])
        endpoints = self._run_kubectl(["get", "endpoints", name, "-n", namespace])
        events = self._run_kubectl(["get", "events", "-n", namespace,
                                  "--field-selector", f"involvedObject.name={name}"])

        return {
            "service": service,
            "endpoints": endpoints,
            "events": events
        }

    def analyze_with_llm(self, data: Dict[str, Any], model) -> str:
        """Analyze Kubernetes data using the LLM model."""
        prompt = f"""Analyze this Kubernetes cluster data and provide insights:

Cluster Data:
{json.dumps(data, indent=2)}

Please provide a comprehensive analysis covering:

1. Cluster Health Overview:
   - Node status and capacity
   - Pod distribution and health
   - Service availability
   - Resource utilization

2. Performance Analysis:
   - Resource bottlenecks
   - Scaling recommendations
   - Network connectivity
   - Storage usage

3. Security Assessment:
   - Pod security policies
   - Network policies
   - Resource restrictions
   - Access controls

4. Best Practices Review:
   - Configuration compliance
   - High availability setup
   - Resource management
   - Monitoring and logging

5. Recommendations:
   - Performance improvements
   - Security enhancements
   - Scaling suggestions
   - Maintenance tasks

Please format the response in a clear, structured manner with sections for each point above.
Highlight any critical issues or recommendations that require immediate attention.
"""

        response = model.create_completion(
            prompt,
            max_tokens=1000,
            temperature=0.7,
            stop=["<end>"]
        )

        return response["choices"][0]["text"].strip()

class KubernetesManager:
    """Manager class for Kubernetes operations."""
    
    def __init__(self, config_file: str):
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
        self.analyzer = KubernetesAnalyzer(self.config.get("kubernetes", {}))

    def analyze_cluster(self, model) -> Dict[str, Any]:
        """Perform comprehensive cluster analysis."""
        # Gather cluster data
        status = self.analyzer.get_cluster_status()
        usage = self.analyzer.get_resource_usage()

        data = {
            "status": status,
            "resource_usage": usage
        }

        # Analyze with LLM
        analysis = self.analyzer.analyze_with_llm(data, model)

        return {
            "data": data,
            "analysis": analysis
        }

    def analyze_component(self, component_type: str, name: str, 
                        namespace: str, model) -> Dict[str, Any]:
        """Analyze specific Kubernetes component."""
        if component_type == "deployment":
            data = self.analyzer.analyze_deployment(name, namespace)
        elif component_type == "service":
            data = self.analyzer.analyze_service(name, namespace)
        else:
            raise ValueError(f"Unsupported component type: {component_type}")

        # Add logs for related pods
        try:
            data["logs"] = self.analyzer.get_pod_logs(name, namespace)
        except RuntimeError:
            data["logs"] = "No logs available"

        # Analyze with LLM
        analysis = self.analyzer.analyze_with_llm(data, model)

        return {
            "data": data,
            "analysis": analysis
        } 