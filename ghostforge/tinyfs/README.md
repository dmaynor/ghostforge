# TinyFS: Secure Filesystem Operations for LLMs

TinyFS is a secure filesystem interface that enables large language models (LLMs) to safely interact with the filesystem. It provides robust security controls, path validation, and user confirmation mechanisms to prevent potentially dangerous operations.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
  - [Python API](#python-api)
  - [Command Line Interface](#command-line-interface)
  - [GhostForge Shell Integration](#ghostforge-shell-integration)
- [Core Concepts](#core-concepts)
  - [Workspace Isolation](#workspace-isolation)
  - [Path Validation](#path-validation)
  - [Operation Confirmation](#operation-confirmation)
  - [Action Logging](#action-logging)
- [Security Considerations](#security-considerations)
- [API Reference](#api-reference)
- [Implementation Notes](#implementation-notes)
- [Future Roadmap](#future-roadmap)

## Overview

TinyFS provides a secure way for language models to perform filesystem operations while maintaining strong security boundaries. It includes:

- **Secure File Operations**: Read, write, copy, move, and delete files within a designated workspace
- **Directory Management**: List, create, and navigate directory structures
- **Path Validation**: Prevents directory traversal attacks and restricts operations to the workspace
- **User Confirmation**: Interactive confirmation for potentially dangerous operations
- **Detailed Logging**: Comprehensive logging for audit trails
- **Sandboxing**: (Coming in Phase 2) Docker-based sandboxing for command execution

## Installation

TinyFS is integrated into GhostForge. To use it:

```bash
# Clone the GhostForge repository
git clone https://github.com/yourusername/ghostforge.git
cd ghostforge

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Python API

```python
from ghostforge.tinyfs import TinyFSClient

# Initialize with a workspace directory
client = TinyFSClient(workspace_dir="/path/to/workspace")

# Read a file
content = client.read_file("example.txt")
print(content)

# Write to a file (requires confirmation unless auto_confirm=True)
client.write_file("output.txt", "Hello, world!")

# List directory contents
files = client.list_directory(".")
for file_info in files:
    print(f"{file_info.name}: {'Directory' if file_info.is_directory else 'File'}")

# Create a directory
client.create_directory("new_directory")

# Copy a file
client.copy_file("source.txt", "destination.txt")

# Delete a file
client.delete_file("to_delete.txt")
```

### Command Line Interface

```bash
# Read a file
python -m ghostforge.tinyfs.cli read example.txt

# Write to a file
python -m ghostforge.tinyfs.cli write output.txt "Hello, world!"

# List directory contents
python -m ghostforge.tinyfs.cli list

# Create a directory
python -m ghostforge.tinyfs.cli mkdir new_directory

# Set a specific workspace and enable auto-confirmation
python -m ghostforge.tinyfs.cli --workspace /path/to/project --auto-confirm write config.json '{"version": "1.0"}'
```

### GhostForge Shell Integration

```
# Start the GhostForge shell
python -m ghostforge.shell

# Inside the shell:
ghostforge> fs help
# Shows help for all fs commands

ghostforge> fs read example.txt
# Reads and displays the content of example.txt

ghostforge> fs write output.txt "Hello, world!"
# Writes text to output.txt

ghostforge> fs list
# Lists the contents of the current directory
```

## Core Concepts

### Workspace Isolation

TinyFS operates within a designated "workspace" directory. All operations are restricted to this workspace to prevent unauthorized access to the broader filesystem. The workspace is specified when creating a TinyFSClient instance:

```python
client = TinyFSClient(workspace_dir="/path/to/workspace")
```

### Path Validation

All path operations are validated to ensure they remain within the workspace boundary. This prevents directory traversal attacks and unauthorized access to files outside the workspace.

```python
# This succeeds if example.txt is in the workspace
client.read_file("example.txt")

# This fails with a SecurityError
client.read_file("/etc/passwd")

# This fails with a SecurityError
client.read_file("../outside_workspace.txt")
```

### Operation Confirmation

Potentially dangerous operations (write, delete, etc.) require user confirmation before execution. This prevents unintended or malicious changes to the filesystem.

```python
# This will prompt for confirmation unless auto_confirm=True
client.write_file("important_file.txt", "New content")

# To bypass confirmation
client = TinyFSClient(workspace_dir="/path/to/workspace", auto_confirm=True)
```

### Action Logging

All operations are logged with detailed information for audit purposes. This includes the action type, timestamp, path, and success/failure status.

```python
# Configure logging level
client = TinyFSClient(workspace_dir="/path/to/workspace", log_level=logging.DEBUG)
```

## Security Considerations

TinyFS implements several security measures:

1. **Workspace Isolation**: All operations are contained within a designated workspace directory.
2. **Path Validation**: All paths are validated to prevent directory traversal and access outside the workspace.
3. **User Confirmation**: Potentially dangerous operations require explicit confirmation.
4. **Parent Directory Creation**: When writing to files, parent directories are automatically created but cannot escape the workspace boundary.
5. **Error Handling**: Proper error handling prevents information leakage and maintains security boundaries.

## API Reference

### Core Classes

#### `TinyFSClient`

The main client for interacting with the filesystem.

```python
def __init__(self, workspace_dir: Union[str, Path], auto_confirm: bool = False, log_level: int = logging.INFO, history_size: int = 100)
```

- `workspace_dir`: Root directory for all operations
- `auto_confirm`: Whether to auto-confirm operations
- `log_level`: Logging verbosity level
- `history_size`: Maximum number of actions to keep in history

#### File Operations

```python
def read_file(self, path: Union[str, Path]) -> str
def write_file(self, path: Union[str, Path], content: str, confirm: bool = True) -> bool
def delete_file(self, path: Union[str, Path], confirm: bool = True) -> bool
def copy_file(self, source: Union[str, Path], destination: Union[str, Path], confirm: bool = True) -> bool
def move_file(self, source: Union[str, Path], destination: Union[str, Path], confirm: bool = True) -> bool
```

#### Directory Operations

```python
def list_directory(self, path: Union[str, Path] = ".") -> List[FileInfo]
def create_directory(self, path: Union[str, Path], confirm: bool = True) -> bool
def directory_exists(self, path: Union[str, Path]) -> bool
```

#### Utility Operations

```python
def file_exists(self, path: Union[str, Path]) -> bool
def get_file_info(self, path: Union[str, Path]) -> Optional[FileInfo]
def get_history(self) -> List[ActionRecord]
```

## Implementation Notes

TinyFS is implemented in pure Python with a focus on security and simplicity. Key design decisions include:

1. **Path Validation**: All paths are validated using `Path.resolve()` to get canonical paths and prevent path traversal attacks.
2. **Workspace Boundary**: The workspace boundary is enforced by checking if the resolved path starts with the resolved workspace path.
3. **Parent Directory Creation**: When writing to a file, parent directories are automatically created but cannot escape the workspace boundary.
4. **Error Handling**: Detailed exception hierarchy for different types of errors (security, validation, cancellation).
5. **Confirmation System**: Interactive confirmation system for potentially dangerous operations with auto-confirm option for non-interactive use.

## Future Roadmap

TinyFS is being developed in phases:

### Phase 1 (Current): Core Functionality
- ✅ File read/write operations with path validation
- ✅ Directory listing and navigation
- ✅ Basic logging infrastructure

### Phase 2: Sandbox & Execution
- 🔄 Docker-based sandboxing
- 🔄 Command execution with security controls
- 🔄 User confirmation system enhancements

### Phase 3: Git & Advanced Features
- 🔜 Git repository operations
- 🔜 Dependency management
- 🔜 Diffing and patching support

### Phase 4: GhostForge Integration
- 🔜 Custom commands for GhostForge shell
- 🔜 LLM prompting for tool usage
- 🔜 GUI confirmation dialogs

### Phase 5: Production Readiness
- 🔜 Comprehensive testing and security review
- 🔜 Documentation and examples
- 🔜 Performance optimization
