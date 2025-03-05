"""Unit tests for Docker analysis functionality."""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import GhostForge components
from ghostforge.docker_remote import DockerAnalyzer

class TestDockerAnalyzer:
    """Test suite for Docker analysis functionality."""
    
    @pytest.fixture
    def mock_client(self):
        """Fixture to provide a mock Docker client."""
        mock = MagicMock()
        mock.containers.list.return_value = [
            MagicMock(id="container1", name="web-app", status="running", 
                     image="python:3.9", ports={"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}),
            MagicMock(id="container2", name="db", status="running", 
                     image="mysql:8.0", ports={"3306/tcp": [{"HostIp": "0.0.0.0", "HostPort": "3306"}]})
        ]
        mock.images.list.return_value = [
            MagicMock(id="image1", tags=["python:3.9"]),
            MagicMock(id="image2", tags=["mysql:8.0"]),
            MagicMock(id="image3", tags=None)  # Untagged image
        ]
        return mock
    
    @pytest.fixture
    def analyzer(self, mock_client):
        """Fixture to provide a DockerAnalyzer with mock client."""
        with patch('docker.from_env', return_value=mock_client):
            analyzer = DockerAnalyzer()
            # Inject mock client
            analyzer.client = mock_client
            return analyzer
    
    def test_list_containers(self, analyzer):
        """Test listing Docker containers."""
        containers = analyzer.list_containers()
        
        # Check that correct number of containers are returned
        assert len(containers) == 2
        
        # Check container details
        assert any(c['id'] == 'container1' and c['name'] == 'web-app' for c in containers)
        assert any(c['id'] == 'container2' and c['name'] == 'db' for c in containers)
        
        # Check port mapping
        for container in containers:
            if container['name'] == 'web-app':
                assert '8080/tcp' in container['ports']
                assert container['ports']['8080/tcp'][0]['HostPort'] == '8080'
    
    def test_list_images(self, analyzer):
        """Test listing Docker images."""
        images = analyzer.list_images()
        
        # Check that correct number of images are returned
        assert len(images) == 3
        
        # Check image details
        assert any(i['id'] == 'image1' and 'python:3.9' in i['tags'] for i in images)
        assert any(i['id'] == 'image2' and 'mysql:8.0' in i['tags'] for i in images)
        assert any(i['id'] == 'image3' and (not i['tags'] or i['tags'] == ['<none>:<none>']) for i in images)
    
    def test_analyze_dockerfile(self, analyzer, temp_workspace):
        """Test analyzing a Dockerfile."""
        # Create a test Dockerfile with security issues
        test_file = temp_workspace / "Dockerfile"
        test_file.write_text("""
FROM python:3.9-slim
WORKDIR /app
COPY . .
# Security issue: Running as root
RUN pip install -r requirements.txt
# Security issue: Credentials in environment variable
ENV API_KEY="secret_key_12345"
# No specific user set
EXPOSE 8080
CMD ["python", "app.py"]
""")
        
        # Mock the LLM analysis
        def mock_analyze_file(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "high", "description": "Running as root", "line": 5},
                    {"severity": "high", "description": "Credentials in environment variable", "line": 7}
                ],
                "best_practices": [
                    {"severity": "medium", "description": "No USER instruction found", "line": None}
                ]
            }
        
        # Patch the analyze_file method
        with patch.object(analyzer, 'analyze_file', side_effect=mock_analyze_file):
            # Analyze the Dockerfile
            results = analyzer.analyze_dockerfile(str(test_file))
            
            # Check that security issues are identified
            assert len(results["security_issues"]) == 2
            assert any("root" in issue["description"] for issue in results["security_issues"])
            assert any("Credentials" in issue["description"] for issue in results["security_issues"])
            
            # Check that best practices are identified
            assert len(results["best_practices"]) == 1
            assert any("USER" in issue["description"] for issue in results["best_practices"])
    
    def test_analyze_image(self, analyzer):
        """Test analyzing a Docker image."""
        # Mock image inspection
        mock_image = MagicMock()
        analyzer.client.images.get.return_value = mock_image
        
        # Mock image inspection results
        mock_image.attrs = {
            "Config": {
                "User": "",  # Empty user means root
                "Env": ["API_KEY=secret_key", "PATH=/usr/local/bin"],
                "ExposedPorts": {"8080/tcp": {}},
                "Volumes": {"/data": {}}
            },
            "RootFS": {
                "Layers": ["layer1", "layer2", "layer3"]  # Multiple layers
            },
            "Size": 1200000000  # Large image size
        }
        
        # Mock the LLM analysis
        def mock_analyze_image(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "high", "description": "Image runs as root"},
                    {"severity": "high", "description": "Sensitive environment variables detected"}
                ],
                "optimizations": [
                    {"severity": "medium", "description": "Image size is too large (1.2GB)"},
                    {"severity": "low", "description": "Multiple layers could be consolidated"}
                ]
            }
        
        # Patch the analyze method
        with patch.object(analyzer, 'analyze_image_metadata', side_effect=mock_analyze_image):
            # Analyze the image
            results = analyzer.analyze_image("python:3.9")
            
            # Check that security issues are identified
            assert len(results["security_issues"]) == 2
            assert any("root" in issue["description"] for issue in results["security_issues"])
            assert any("environment variables" in issue["description"] for issue in results["security_issues"])
            
            # Check that optimizations are identified
            assert len(results["optimizations"]) == 2
            assert any("size" in opt["description"] for opt in results["optimizations"])
            assert any("layers" in opt["description"] for opt in results["optimizations"])
    
    def test_analyze_running_container(self, analyzer):
        """Test analyzing a running container."""
        # Mock container inspection
        mock_container = MagicMock()
        analyzer.client.containers.get.return_value = mock_container
        
        # Mock container inspection results
        mock_container.attrs = {
            "Config": {
                "User": "",  # Empty user means root
                "Env": ["DB_PASSWORD=insecure", "DEBUG=true"],
                "ExposedPorts": {"8080/tcp": {}}
            },
            "HostConfig": {
                "Privileged": True,  # Running in privileged mode
                "PortBindings": {"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]},
                "Binds": ["/host:/container:rw"]  # Host mount with write access
            },
            "NetworkSettings": {
                "Ports": {"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}
            },
            "State": {
                "Status": "running",
                "Running": True
            }
        }
        
        # Mock the LLM analysis
        def mock_analyze_container(*args, **kwargs):
            return {
                "security_issues": [
                    {"severity": "critical", "description": "Container runs in privileged mode"},
                    {"severity": "high", "description": "Container runs as root"},
                    {"severity": "high", "description": "Sensitive environment variables detected"},
                    {"severity": "high", "description": "Host filesystem mounted with write access"}
                ],
                "network_exposure": [
                    {"severity": "medium", "description": "Port 8080 exposed to all network interfaces (0.0.0.0)"}
                ]
            }
        
        # Patch the analyze method
        with patch.object(analyzer, 'analyze_container_metadata', side_effect=mock_analyze_container):
            # Analyze the container
            results = analyzer.analyze_container("web-app")
            
            # Check that security issues are identified
            assert len(results["security_issues"]) == 4
            assert any("privileged" in issue["description"] for issue in results["security_issues"])
            assert any("root" in issue["description"] for issue in results["security_issues"])
            assert any("environment variables" in issue["description"] for issue in results["security_issues"])
            assert any("filesystem" in issue["description"] for issue in results["security_issues"])
            
            # Check that network exposure issues are identified
            assert len(results["network_exposure"]) == 1
            assert any("0.0.0.0" in issue["description"] for issue in results["network_exposure"])
            
    def test_generate_remediation(self, analyzer):
        """Test generating remediation for Docker issues."""
        # Issues to remediate
        issues = {
            "security_issues": [
                {"severity": "high", "description": "Container runs as root"},
                {"severity": "high", "description": "Sensitive environment variables detected"}
            ],
            "best_practices": [
                {"severity": "medium", "description": "No health check defined"}
            ]
        }
        
        # Mock the LLM remediation
        def mock_generate_remediation(*args, **kwargs):
            return {
                "remediation_steps": [
                    {
                        "issue": "Container runs as root",
                        "solution": "Add 'USER nonroot' to your Dockerfile",
                        "example": "USER nonroot"
                    },
                    {
                        "issue": "Sensitive environment variables detected",
                        "solution": "Use Docker secrets or environment files instead of hardcoding secrets",
                        "example": "# Using Docker secrets\nRUN --mount=type=secret,id=api_key cat /run/secrets/api_key"
                    },
                    {
                        "issue": "No health check defined",
                        "solution": "Add a HEALTHCHECK instruction to your Dockerfile",
                        "example": 'HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8080/health || exit 1'
                    }
                ]
            }
        
        # Patch the generate_remediation method
        with patch.object(analyzer, 'generate_docker_remediation', side_effect=mock_generate_remediation):
            # Generate remediation
            remediation = analyzer.generate_remediation(issues)
            
            # Check remediation steps
            assert len(remediation["remediation_steps"]) == 3
            assert any("USER nonroot" in step["example"] for step in remediation["remediation_steps"])
            assert any("Docker secrets" in step["solution"] for step in remediation["remediation_steps"])
            assert any("HEALTHCHECK" in step["example"] for step in remediation["remediation_steps"]) 