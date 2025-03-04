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

BuildBot uses several configuration files stored in the `~/.buildbot` directory:

- `config.yaml`: General configuration
- `ci.yaml`: CI/CD provider settings
- `kubernetes.yaml`: Kubernetes cluster settings
- `docker.yaml`: Docker host settings

Example configuration:

```yaml
# ~/.buildbot/config.yaml
model:
  path: ~/.buildbot/models/tinyllama-1.1b-chat.Q4_K_M.gguf
  context_size: 2048
  gpu_layers: 0
  threads: 4
  f16_kv: true

# ~/.buildbot/docker.yaml
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

- `help`: Display help information and available commands
- `index`: Index project files for troubleshooting
- `search`: Search indexed files using keywords
- `analyze`: Analyze files using TinyLlama
- `prompt`: Manage YAML prompt templates
- `prompts`: List or view available prompt templates
- `config`: View or modify BuildBot configuration
- `docker`: Docker-specific analysis and troubleshooting
- `history`: View or search command history
- `watch`: Watch files or command output in real-time
- `unwatch`: Stop watching a file or command
- `watches`: List active watches
- `model`: Manage LLM models
- `detect`: Detect and analyze project characteristics
- `exit`: Exit the BuildBot shell

## Understanding the Codebase

BuildBot is organized around several key components:

### Shell

The command-line interface is powered by the Python `cmd` module, with command implementations in:
- `buildbot/shell.py`: Core shell implementation with command categories and completions
- `buildbot/commands.py`: Individual command implementations 

### File Indexing

The indexing system scans your codebase and stores content for quick retrieval:

```bash
> index
```

The indexer will scan your project files and gracefully handle binary files by skipping them with a message:

```
[BuildBot]: ./.git/index will not be indexed.
[BuildBot]: ./binary-file.png will not be indexed.
```

### Custom Prompts

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

## Troubleshooting

### Common Issues

1. **Indexing errors with binary files**: These are expected and won't affect BuildBot's functionality. Binary files are automatically skipped during indexing.

2. **Help command exits the shell**: If you encounter this issue, make sure your installation includes the latest fixes that properly implement the command categories and prompt commands.

3. **Docker/Kubernetes analysis errors**: Ensure you have the proper permissions to access container and cluster information.

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