"""Unit tests for Kubernetes analysis functionality."""

import os
import yaml
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import GhostForge components
from ghostforge.kubernetes import KubernetesAnalyzer

class TestKubernetesAnalyzer:
    """Test suite for Kubernetes analysis functionality."""
    
    @pytest.fixture
    def mock_k8s_client(self):
        """Fixture to provide a mock Kubernetes client."""
        mock = MagicMock()
        
        # Mock for getting deployments
        mock_deployment_list = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.metadata.name = "web-app"
        mock_deployment.metadata.namespace = "default"
        mock_deployment.spec.replicas = 3
        mock_deployment.spec.template.spec.containers = [
            MagicMock(
                name="web-app-container",
                image="my-app:latest",
                ports=[MagicMock(container_port=8080)],
                security_context=MagicMock(
                    privileged=False,
                    run_as_user=None,  # Running as root
                    capabilities=MagicMock(add=["NET_ADMIN"])
                ),
                resources=MagicMock(
                    requests={"cpu": "100m", "memory": "256Mi"},
                    limits=None  # No resource limits
                ),
                liveness_probe=None,  # No health checks
                volume_mounts=[MagicMock(name="config-volume", mount_path="/etc/config")]
            )
        ]
        mock_deployment_list.items = [mock_deployment]
        mock.AppsV1Api.return_value.list_deployment_for_all_namespaces.return_value = mock_deployment_list
        
        # Mock for getting pods
        mock_pod_list = MagicMock()
        mock_pod1 = MagicMock()
        mock_pod1.metadata.name = "web-app-pod-1"
        mock_pod1.metadata.namespace = "default"
        mock_pod1.status.phase = "Running"
        mock_pod1.status.container_statuses = [
            MagicMock(name="web-app-container", ready=True, restart_count=5)
        ]
        mock_pod_list.items = [mock_pod1]
        mock.CoreV1Api.return_value.list_pod_for_all_namespaces.return_value = mock_pod_list
        
        # Mock for getting services
        mock_service_list = MagicMock()
        mock_service = MagicMock()
        mock_service.metadata.name = "web-app-service"
        mock_service.metadata.namespace = "default"
        mock_service.spec.type = "LoadBalancer"
        mock_service.spec.ports = [MagicMock(port=80, target_port=8080)]
        mock_service_list.items = [mock_service]
        mock.CoreV1Api.return_value.list_service_for_all_namespaces.return_value = mock_service_list
        
        # Mock for getting ingresses
        mock_ingress_list = MagicMock()
        mock_ingress = MagicMock()
        mock_ingress.metadata.name = "web-app-ingress"
        mock_ingress.metadata.namespace = "default"
        mock_ingress.metadata.annotations = {}  # No security annotations
        mock_ingress.spec.tls = []  # No TLS
        mock_ingress_list.items = [mock_ingress]
        mock.NetworkingV1Api.return_value.list_ingress_for_all_namespaces.return_value = mock_ingress_list
        
        return mock
    
    @pytest.fixture
    def analyzer(self, mock_k8s_client):
        """Fixture to provide a KubernetesAnalyzer with mock client."""
        with patch('kubernetes.client.Configuration'), \
             patch('kubernetes.config.load_kube_config'), \
             patch('kubernetes.client.ApiClient', return_value=mock_k8s_client):
            analyzer = KubernetesAnalyzer()
            # Inject mock clients
            analyzer.apps_v1 = mock_k8s_client.AppsV1Api()
            analyzer.core_v1 = mock_k8s_client.CoreV1Api()
            analyzer.networking_v1 = mock_k8s_client.NetworkingV1Api()
            return analyzer
    
    def test_list_resources(self, analyzer):
        """Test listing Kubernetes resources."""
        resources = analyzer.list_resources()
        
        # Check deployments
        assert len(resources['deployments']) == 1
        assert resources['deployments'][0]['name'] == 'web-app'
        assert resources['deployments'][0]['namespace'] == 'default'
        assert resources['deployments'][0]['replicas'] == 3
        
        # Check pods
        assert len(resources['pods']) == 1
        assert resources['pods'][0]['name'] == 'web-app-pod-1'
        assert resources['pods'][0]['namespace'] == 'default'
        assert resources['pods'][0]['status'] == 'Running'
        
        # Check services
        assert len(resources['services']) == 1
        assert resources['services'][0]['name'] == 'web-app-service'
        assert resources['services'][0]['namespace'] == 'default'
        assert resources['services'][0]['type'] == 'LoadBalancer'
        
        # Check ingresses
        assert len(resources['ingresses']) == 1
        assert resources['ingresses'][0]['name'] == 'web-app-ingress'
        assert resources['ingresses'][0]['namespace'] == 'default'
    
    def test_analyze_manifests(self, analyzer, temp_workspace):
        """Test analyzing Kubernetes manifests."""
        # Create test manifests
        manifests_dir = temp_workspace / "k8s"
        manifests_dir.mkdir(exist_ok=True)
        
        # Create a deployment manifest with security issues
        deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "web-app",
                "namespace": "default"
            },
            "spec": {
                "replicas": 3,
                "selector": {
                    "matchLabels": {"app": "web-app"}
                },
                "template": {
                    "metadata": {
                        "labels": {"app": "web-app"}
                    },
                    "spec": {
                        "containers": [{
                            "name": "web-app-container",
                            "image": "my-app:latest",  # No specific version
                            "ports": [{"containerPort": 8080}],
                            "securityContext": {
                                "privileged": True,  # Security issue: privileged container
                                "capabilities": {
                                    "add": ["ALL"]   # Security issue: excessive capabilities
                                }
                            },
                            "env": [
                                {"name": "API_KEY", "value": "secret-api-key-12345"}  # Security issue: hardcoded secret
                            ],
                            # No resource limits - potential resource exhaustion
                            # No liveness/readiness probes - reliability issue
                        }]
                    }
                }
            }
        }
        
        # Create a service manifest with security issues
        service_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "web-app-service",
                "namespace": "default"
            },
            "spec": {
                "selector": {"app": "web-app"},
                "ports": [{"port": 80, "targetPort": 8080}],
                "type": "LoadBalancer",  # Exposing directly to internet
                "externalTrafficPolicy": "Cluster"  # Source IP not preserved
            }
        }
        
        # Write the manifests to files
        deployment_file = manifests_dir / "deployment.yaml"
        with open(deployment_file, 'w') as f:
            yaml.dump(deployment_manifest, f)
        
        service_file = manifests_dir / "service.yaml"
        with open(service_file, 'w') as f:
            yaml.dump(service_manifest, f)
        
        # Mock the LLM analysis
        def mock_analyze_manifests(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "critical", "description": "Deployment 'web-app' uses privileged container", "manifest": "deployment.yaml", "kind": "Deployment"},
                    {"severity": "high", "description": "Deployment 'web-app' container has excessive capabilities", "manifest": "deployment.yaml", "kind": "Deployment"},
                    {"severity": "high", "description": "Deployment 'web-app' contains hardcoded secret in environment variable", "manifest": "deployment.yaml", "kind": "Deployment"},
                    {"severity": "medium", "description": "Service 'web-app-service' is exposed via LoadBalancer without restrictions", "manifest": "service.yaml", "kind": "Service"}
                ],
                "best_practices": [
                    {"severity": "medium", "description": "Deployment 'web-app' containers have no resource limits defined", "manifest": "deployment.yaml", "kind": "Deployment"},
                    {"severity": "medium", "description": "Deployment 'web-app' containers have no liveness/readiness probes", "manifest": "deployment.yaml", "kind": "Deployment"},
                    {"severity": "low", "description": "Deployment 'web-app' uses 'latest' tag which is not a specific version", "manifest": "deployment.yaml", "kind": "Deployment"}
                ]
            }
        
        # Patch the analyze method
        with patch.object(analyzer, 'analyze_manifest_files', side_effect=mock_analyze_manifests):
            # Analyze the manifests
            results = analyzer.analyze_manifests(str(manifests_dir))
            
            # Check that security issues are identified
            assert len(results["security_issues"]) == 4
            assert any("privileged" in issue["description"] for issue in results["security_issues"])
            assert any("capabilities" in issue["description"] for issue in results["security_issues"])
            assert any("hardcoded secret" in issue["description"] for issue in results["security_issues"])
            assert any("LoadBalancer" in issue["description"] for issue in results["security_issues"])
            
            # Check that best practices are identified
            assert len(results["best_practices"]) == 3
            assert any("resource limits" in issue["description"] for issue in results["best_practices"])
            assert any("liveness/readiness probes" in issue["description"] for issue in results["best_practices"])
            assert any("latest" in issue["description"] for issue in results["best_practices"])
    
    def test_analyze_cluster_resources(self, analyzer):
        """Test analyzing live Kubernetes cluster resources."""
        # Mock the LLM analysis
        def mock_analyze_resources(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "high", "description": "Container 'web-app-container' in deployment 'web-app' runs with NET_ADMIN capability", "resource": "deployment/web-app", "namespace": "default"},
                    {"severity": "high", "description": "Container 'web-app-container' in deployment 'web-app' runs as root", "resource": "deployment/web-app", "namespace": "default"},
                    {"severity": "medium", "description": "Ingress 'web-app-ingress' does not use TLS", "resource": "ingress/web-app-ingress", "namespace": "default"},
                    {"severity": "medium", "description": "Service 'web-app-service' is exposed via LoadBalancer", "resource": "service/web-app-service", "namespace": "default"}
                ],
                "best_practices": [
                    {"severity": "medium", "description": "Container 'web-app-container' in deployment 'web-app' has no resource limits defined", "resource": "deployment/web-app", "namespace": "default"},
                    {"severity": "medium", "description": "Container 'web-app-container' in deployment 'web-app' has no liveness probe", "resource": "deployment/web-app", "namespace": "default"},
                    {"severity": "low", "description": "Pod 'web-app-pod-1' has high restart count (5)", "resource": "pod/web-app-pod-1", "namespace": "default"}
                ]
            }
        
        # Patch the analyze method
        with patch.object(analyzer, 'analyze_cluster', side_effect=mock_analyze_resources):
            # Analyze the cluster resources
            results = analyzer.analyze_cluster()
            
            # Check that security issues are identified
            assert len(results["security_issues"]) == 4
            assert any("NET_ADMIN" in issue["description"] for issue in results["security_issues"])
            assert any("root" in issue["description"] for issue in results["security_issues"])
            assert any("TLS" in issue["description"] for issue in results["security_issues"])
            assert any("LoadBalancer" in issue["description"] for issue in results["security_issues"])
            
            # Check that best practices are identified
            assert len(results["best_practices"]) == 3
            assert any("resource limits" in issue["description"] for issue in results["best_practices"])
            assert any("liveness probe" in issue["description"] for issue in results["best_practices"])
            assert any("restart count" in issue["description"] for issue in results["best_practices"])
    
    def test_generate_remediation(self, analyzer):
        """Test generating remediation for Kubernetes issues."""
        # Issues to remediate
        issues = {
            "security_issues": [
                {"severity": "high", "description": "Container 'web-app-container' in deployment 'web-app' runs as root", "resource": "deployment/web-app", "namespace": "default"},
                {"severity": "medium", "description": "Ingress 'web-app-ingress' does not use TLS", "resource": "ingress/web-app-ingress", "namespace": "default"}
            ],
            "best_practices": [
                {"severity": "medium", "description": "Container 'web-app-container' in deployment 'web-app' has no resource limits defined", "resource": "deployment/web-app", "namespace": "default"}
            ]
        }
        
        # Mock the LLM remediation
        def mock_generate_remediation(*args, **kwargs):
            return {
                "remediation_steps": [
                    {
                        "issue": "Container runs as root",
                        "solution": "Add securityContext with runAsNonRoot and runAsUser",
                        "example": """
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
                        """
                    },
                    {
                        "issue": "Ingress does not use TLS",
                        "solution": "Configure TLS for the ingress",
                        "example": """
spec:
  tls:
  - hosts:
    - myapp.example.com
    secretName: myapp-tls-cert
                        """
                    },
                    {
                        "issue": "No resource limits defined",
                        "solution": "Add resource limits to prevent resource exhaustion",
                        "example": """
resources:
  limits:
    cpu: "1"
    memory: "512Mi"
  requests:
    cpu: "100m"
    memory: "256Mi"
                        """
                    }
                ]
            }
        
        # Patch the generate_remediation method
        with patch.object(analyzer, 'generate_kubernetes_remediation', side_effect=mock_generate_remediation):
            # Generate remediation
            remediation = analyzer.generate_remediation(issues)
            
            # Check remediation steps
            assert len(remediation["remediation_steps"]) == 3
            assert any("runAsNonRoot" in step["example"] for step in remediation["remediation_steps"])
            assert any("TLS" in step["example"] for step in remediation["remediation_steps"])
            assert any("resource limits" in step["solution"] and "cpu" in step["example"] for step in remediation["remediation_steps"]) 