# BuildBot AI

An AI-powered troubleshooting assistant for DevOps that integrates with TinyLlama to help analyze and troubleshoot various project files, Docker containers, Kubernetes clusters, and CI/CD pipelines.

## Features

- File indexing and semantic search
- AI-powered file analysis
- Docker container analysis and management
- Kubernetes cluster analysis
- CI/CD pipeline integration (GitHub Actions, GitLab CI, Jenkins)
- Real-time file and command monitoring
- Custom prompt templates
- Export functionality
- Remote Docker host support

## Installation

```bash
pip install buildbot-ai
```

Or install from source:

```bash
git clone https://github.com/dmaynor/buildbot.git
cd buildbot
pip install -e .
```

## Quick Start

1. Start the BuildBot shell:
```bash
buildbot
```

2. Index your project files:
```bash
> index
```

3. Analyze files:
```bash
> analyze logs/error.log
```

4. Search indexed files:
```bash
> search error --type=log
```

## Configuration

BuildBot uses several configuration files stored in the `.buildbot` directory:

- `config.yaml`: General configuration
- `ci.yaml`: CI/CD provider settings
- `kubernetes.yaml`: Kubernetes cluster settings
- `docker.yaml`: Docker host settings

Example configuration:

```yaml
# .buildbot/config.yaml
model:
  path: ./models/tinyllama-1.1b-chat.Q4_K_M.gguf
  context_size: 2048
  gpu_layers: 0
  threads: 4
  f16_kv: true

# .buildbot/docker.yaml
docker_hosts:
  prod:
    enabled: true
    url: tcp://prod-server:2375
    tls: true
  staging:
    enabled: true
    use_ssh: true
    hostname: staging-server
    username: docker
    key_file: ~/.ssh/docker_key
```

## Commands

- `index`: Index project files for troubleshooting
- `search`: Search indexed files using keywords
- `analyze`: Analyze files using TinyLlama
- `prompt`: Manage YAML prompt templates
- `config`: View or modify BuildBot configuration
- `docker`: Docker-specific analysis and troubleshooting
- `history`: View or search command history
- `watch`: Watch files or command output in real-time
- `model`: Manage LLM models
- `export`: Export analysis results or command output

## Custom Prompts

Create custom analysis prompts in YAML format:

```yaml
# prompts/custom_analysis.yaml
description: Custom analysis template
template: |
  Analyze this content and provide insights:
  {{ content }}

  Please provide:
  1. Summary
  2. Key findings
  3. Recommendations
```

## Development

1. Set up development environment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Format code:
```bash
black buildbot
```

4. Run linter:
```bash
pylint buildbot
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker. 