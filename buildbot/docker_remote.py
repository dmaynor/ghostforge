"""Remote Docker host support for BuildBot."""

import os
import json
import docker
import paramiko
from typing import Dict, Any, List, Optional, Union
from docker.models.containers import Container
from docker.models.images import Image

class DockerRemoteManager:
    """Manager for remote Docker hosts."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hosts = {}
        self._init_hosts()

    def _init_hosts(self):
        """Initialize connections to configured Docker hosts."""
        for host, cfg in self.config.get("docker_hosts", {}).items():
            if not cfg.get("enabled", False):
                continue

            try:
                if cfg.get("use_ssh", False):
                    # Connect via SSH
                    client = self._create_ssh_client(cfg)
                else:
                    # Connect via Docker daemon
                    client = docker.DockerClient(
                        base_url=cfg["url"],
                        tls=cfg.get("tls", False)
                    )
                self.hosts[host] = client
            except Exception as e:
                print(f"[BuildBot]: Failed to connect to Docker host {host}: {e}")

    def _create_ssh_client(self, config: Dict[str, Any]) -> docker.DockerClient:
        """Create Docker client over SSH."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect via SSH
        ssh.connect(
            hostname=config["hostname"],
            port=config.get("port", 22),
            username=config["username"],
            password=config.get("password"),
            key_filename=config.get("key_file")
        )

        # Create Docker client over SSH
        return docker.DockerClient(
            base_url=f"ssh://{config['username']}@{config['hostname']}",
            use_ssh_client=ssh
        )

    def get_host_info(self, host: str) -> Dict[str, Any]:
        """Get information about a Docker host."""
        if host not in self.hosts:
            raise ValueError(f"Host {host} not configured")

        client = self.hosts[host]
        info = client.info()
        version = client.version()
        
        return {
            "info": info,
            "version": version
        }

    def list_containers(self, host: str) -> List[Container]:
        """List containers on a host."""
        if host not in self.hosts:
            raise ValueError(f"Host {host} not configured")

        return self.hosts[host].containers.list(all=True)

    def list_images(self, host: str) -> List[Image]:
        """List images on a host."""
        if host not in self.hosts:
            raise ValueError(f"Host {host} not configured")

        return self.hosts[host].images.list()

    def get_container_logs(self, host: str, container_id: str) -> str:
        """Get container logs from a host."""
        if host not in self.hosts:
            raise ValueError(f"Host {host} not configured")

        container = self.hosts[host].containers.get(container_id)
        return container.logs().decode()

    def execute_command(self, host: str, container_id: str, 
                       command: str) -> Dict[str, Any]:
        """Execute command in a container."""
        if host not in self.hosts:
            raise ValueError(f"Host {host} not configured")

        container = self.hosts[host].containers.get(container_id)
        exit_code, output = container.exec_run(command)
        
        return {
            "exit_code": exit_code,
            "output": output.decode()
        }

    def analyze_host(self, host: str, model) -> Dict[str, Any]:
        """Analyze a Docker host using the LLM model."""
        if host not in self.hosts:
            raise ValueError(f"Host {host} not configured")

        # Gather host data
        info = self.get_host_info(host)
        containers = [c.attrs for c in self.list_containers(host)]
        images = [i.attrs for i in self.list_images(host)]

        data = {
            "host_info": info,
            "containers": containers,
            "images": images
        }

        # Prepare prompt for analysis
        prompt = f"""Analyze this Docker host and provide insights:

Host Information:
{json.dumps(info, indent=2)}

Containers ({len(containers)}):
{json.dumps(containers, indent=2)}

Images ({len(images)}):
{json.dumps(images, indent=2)}

Please provide a comprehensive analysis covering:

1. Host Overview:
   - System resources and capacity
   - Docker version and configuration
   - Performance metrics
   - Storage usage

2. Container Analysis:
   - Running containers
   - Resource allocation
   - Network configuration
   - Volume mounts
   - Health status

3. Image Analysis:
   - Image sizes and layers
   - Base images used
   - Build patterns
   - Storage efficiency

4. Security Assessment:
   - Container isolation
   - Resource limits
   - Network exposure
   - Volume security
   - Privilege settings

5. Recommendations:
   - Performance optimizations
   - Security improvements
   - Resource management
   - Best practices compliance

Please format the response in a clear, structured manner with sections for each point above.
Highlight any critical issues or recommendations that require immediate attention.
"""

        # Generate analysis using the model
        response = model.create_completion(
            prompt,
            max_tokens=1000,
            temperature=0.7,
            stop=["<end>"]
        )

        return {
            "data": data,
            "analysis": response["choices"][0]["text"].strip()
        }

    def analyze_container(self, host: str, container_id: str, 
                         model) -> Dict[str, Any]:
        """Analyze a specific container."""
        if host not in self.hosts:
            raise ValueError(f"Host {host} not configured")

        # Get container information
        container = self.hosts[host].containers.get(container_id)
        logs = container.logs().decode()
        stats = container.stats(stream=False)

        data = {
            "info": container.attrs,
            "logs": logs,
            "stats": stats
        }

        # Prepare prompt for analysis
        prompt = f"""Analyze this container and provide insights:

Container Information:
{json.dumps(container.attrs, indent=2)}

Container Stats:
{json.dumps(stats, indent=2)}

Recent Logs:
{logs}

Please provide:
1. Container Status Overview
2. Resource Usage Analysis
3. Log Analysis
4. Performance Assessment
5. Security Review
6. Recommendations
"""

        # Generate analysis using the model
        response = model.create_completion(
            prompt,
            max_tokens=1000,
            temperature=0.7,
            stop=["<end>"]
        )

        return {
            "data": data,
            "analysis": response["choices"][0]["text"].strip()
        } 