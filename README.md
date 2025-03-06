# GhostForge AI

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
- **New:** Secure filesystem operations for LLMs via TinyFS

## Installation

```bash
pip install ghostforge-ai
```

Or install from source:

```bash
git clone https://github.com/dmaynor/ghostforge.git
cd ghostforge
pip install -e .
```

### Automatic Environment Setup

GhostForge now includes a setup script that configures your environment and downloads the required model:

```bash
# Set up the virtual environment and direnv for automatic activation
./setup_venv.sh

# Download the TinyLlama model
python tinyfs_auto_download_simple.py
```

## Quick Start

1. Start the GhostForge shell:
```bash
ghostforge
```

2. Index your project files:
```bash
ghostforge> index
```

3. Analyze files:
```bash
ghostforge> analyze logs/error.log
```

4. Search indexed files:
```bash
ghostforge> search error --type=log
```

5. Use the new TinyFS file operations:
```bash
ghostforge> fs list
ghostforge> fs read config.json
```

## Configuration

GhostForge uses several configuration files stored in the `~/.ghostforge` directory:

- `config.yaml`: General configuration
- `ci.yaml`: CI/CD provider settings
- `kubernetes.yaml`: Kubernetes cluster settings
- `docker.yaml`: Docker host settings

Example configuration:

```yaml
# ~/.ghostforge/config.yaml
model:
  path: ~/.ghostforge/models/tinyllama-1.1b-chat.Q4_K_M.gguf
  context_size: 2048
  gpu_layers: 0
  threads: 4
  f16_kv: true

# ~/.ghostforge/docker.yaml
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

Below is a comprehensive list of commands available in the GhostForge shell:

### File Operations
- `index [directory]`: Index project files for searching and analysis
- `search <query> [--type=filetype]`: Search indexed files using keywords
- `analyze <file> [--prompt=template]`: Analyze files using TinyLlama

### TinyFS Commands
- `fs read <path>`: Read and display the contents of a file
- `fs write <path> <content>`: Write content to a file
- `fs list [path]`: List contents of a directory (defaults to current directory)
- `fs mkdir <path>`: Create a new directory
- `fs delete <path>`: Delete a file
- `fs copy <source> <destination>`: Copy a file to a new location
- `fs move <source> <destination>`: Move a file to a new location
- `fs exists <path>`: Check if a file or directory exists
- `fs info <path>`: Display information about a file or directory

### Docker Commands
- `docker list-images`: List available Docker images
- `docker list-containers`: List running Docker containers
- `docker analyze-image <image>`: Analyze a Docker image
- `docker analyze-container <container>`: Analyze a running container
- `docker analyze-dockerfile <path>`: Analyze a Dockerfile

### Kubernetes Commands
- `kubernetes analyze-manifests <directory>`: Analyze Kubernetes manifest files
- `kubernetes analyze-cluster`: Analyze the current Kubernetes cluster
- `kubernetes list-resources`: List resources in the current cluster

### CI/CD Commands
- `cicd analyze <directory>`: Analyze CI/CD configuration files

### Monitoring Commands
- `watch <file|command>`: Watch a file or command output in real-time
- `unwatch <id>`: Stop watching a file or command
- `watches`: List active watches

### Configuration Commands
- `config get <key>`: View a configuration value
- `config set <key> <value>`: Set a configuration value
- `config list`: List all configuration values
- `prompt list`: List available prompt templates
- `prompt show <name>`: Show a specific prompt template
- `prompt create <name>`: Create a new prompt template
- `model info`: Show information about the current model
- `model load <path>`: Load a different model

### Shell Commands
- `help`: Display help information and available commands
- `history`: View or search command history
- `exit` or `quit`: Exit the GhostForge shell
- `hello`: Test command to verify the shell is working

## Sample Help Output

When you run the `help` command in the GhostForge shell, you'll see output similar to this:

```
Welcome to GhostForge Shell. Type help or ? to list commands.

Documented commands (type help <topic>):

File Operations:
  analyze  index  search  fs

Docker Commands:
  docker

Kubernetes Commands:
  kubernetes  k8s

CI/CD Commands:
  cicd

Watch Commands:
  watch  unwatch  watches

Configuration:
  config  model  prompts

Shell Commands:
  help  exit  quit  hello

Type help <command> for detailed information on a specific command.
For example: help analyze
```

## Understanding the Codebase

GhostForge is organized around several key components:

### Shell

The command-line interface is powered by the Python `cmd` module, with command implementations in:
- `ghostforge/shell.py`: Core shell implementation with command categories and completions
- `ghostforge/commands.py`: Individual command implementations 

### File Indexing

The indexing system scans your codebase and stores content for quick retrieval:

```bash
ghostforge> index
```

The indexer will scan your project files and gracefully handle binary files by skipping them with a message:

```
[GhostForge]: ./.git/index will not be indexed.
[GhostForge]: ./binary-file.png will not be indexed.
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
black ghostforge
```

4. Run linter:
```bash
pylint ghostforge
```

## Troubleshooting

### Common Issues

1. **Indexing errors with binary files**: These are expected and won't affect GhostForge's functionality. Binary files are automatically skipped during indexing.

2. **Help command exits the shell**: If you encounter this issue, make sure your installation includes the latest fixes that properly implement the command categories and prompt commands.

3. **Docker/Kubernetes analysis errors**: Ensure you have the proper permissions to access container and cluster information.

4. **Model loading errors**: If you encounter errors loading the model, run the `tinyfs_auto_download_simple.py` script to download the required model.

5. **Environment setup issues**: Use the `setup_venv.sh` script to create a properly configured virtual environment. For automatic environment activation, install direnv and run `direnv allow` in the project directory.

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