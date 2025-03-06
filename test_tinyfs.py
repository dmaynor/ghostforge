#!/usr/bin/env python3
"""
Simple test script for TinyFS functionality.
This script demonstrates the core functionality of the TinyFS module
without requiring the full GhostForge infrastructure.
"""

import os
import sys
import logging
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Import TinyFS classes directly
sys.path.insert(0, os.path.abspath('.'))

# Define the classes inline for independence
class SecurityError(Exception):
    """Exception raised for security violations."""
    pass

class PathValidationError(SecurityError):
    """Exception raised when a path fails validation."""
    pass

class OperationNotAllowedError(SecurityError):
    """Exception raised when an operation is not allowed due to security restrictions."""
    pass

class OperationCancelledError(Exception):
    """Exception raised when an operation is cancelled by the user."""
    pass

class FileInfo:
    """Information about a file or directory."""
    
    def __init__(self, name, path, is_directory, size=None, modified_time=None):
        self.name = name
        self.path = path
        self.is_directory = is_directory
        self.size = size
        self.modified_time = modified_time
    
    @classmethod
    def from_path(cls, path_obj, relative_to=None):
        """Create a FileInfo object from a pathlib.Path object."""
        stat = path_obj.stat()
        
        if relative_to:
            try:
                rel_path = path_obj.relative_to(relative_to)
            except ValueError:
                rel_path = path_obj
        else:
            rel_path = path_obj
            
        return cls(
            name=path_obj.name,
            path=str(rel_path),
            is_directory=path_obj.is_dir(),
            size=stat.st_size if not path_obj.is_dir() else None,
            modified_time=stat.st_mtime
        )

class TinyFSClient:
    """Core filesystem operations client for Tiny LLM."""
    
    def __init__(
        self, 
        workspace_dir=None,
        auto_confirm=False,
        log_level=logging.INFO
    ):
        """
        Initialize the filesystem client with security boundaries.
        
        Args:
            workspace_dir: Root directory for all operations (defaults to current directory)
            auto_confirm: Whether to auto-confirm operations
            log_level: Logging verbosity
        """
        # Use current directory as default workspace
        if workspace_dir is None:
            workspace_dir = os.getcwd()
            
        self.workspace_dir = Path(workspace_dir).resolve()
        self.auto_confirm = auto_confirm
        self.logger = logging.getLogger("tinyfs")
        self.logger.setLevel(log_level)
        
        # Create workspace directory if it doesn't exist
        if not self.workspace_dir.exists():
            self.logger.info(f"Creating workspace directory: {self.workspace_dir}")
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            
        self.logger.info(f"Initialized TinyFSClient with workspace: {self.workspace_dir}")
    
    def _validate_path(self, path, must_exist=True):
        """
        Ensure a path is within the workspace directory.
        
        Args:
            path: Path to validate
            must_exist: Whether the path must already exist
        
        Returns:
            Resolved Path object
            
        Raises:
            SecurityError: If path is outside workspace
            FileNotFoundError: If the path doesn't exist and must_exist is True
        """
        # Convert to Path object if it's a string
        if isinstance(path, str):
            # Handle relative paths
            if not os.path.isabs(path):
                target = (self.workspace_dir / path).resolve()
            else:
                target = Path(path).resolve()
        else:
            target = path.resolve()
        
        # Security check: ensure path is within workspace
        if not str(target).startswith(str(self.workspace_dir)):
            raise PathValidationError(f"Path '{path}' is outside workspace '{self.workspace_dir}'")
        
        # Existence check if required
        if must_exist and not target.exists():
            raise FileNotFoundError(f"Path not found: {target}")
            
        return target
    
    def _request_confirmation(self, operation, details):
        """
        Request user confirmation for an operation.
        
        Args:
            operation: Short description of the operation
            details: Detailed information about the operation
            
        Returns:
            True if confirmed, False otherwise
        """
        if self.auto_confirm:
            self.logger.info(f"Auto-confirming operation: {operation}")
            return True
            
        # Interactive confirmation
        print(f"\n=== Confirmation Required ===")
        print(f"Operation: {operation}")
        print(f"Details: {details}")
        print(f"===========================")
        
        response = input("Proceed? (y/N): ").strip().lower()
        return response in ('y', 'yes')
    
    def read_file(self, path):
        """
        Read a file within the workspace.
        
        Args:
            path: Path to the file
            
        Returns:
            File content as string
        """
        validated_path = self._validate_path(path)
        
        if validated_path.is_dir():
            raise IsADirectoryError(f"Cannot read directory as file: {validated_path}")
            
        self.logger.info(f"Reading file: {validated_path}")
        with open(validated_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content
    
    def write_file(self, path, content, confirm=True):
        """
        Write content to a file within the workspace.
        
        Args:
            path: Path to the file
            content: Content to write
            confirm: Whether to require confirmation
            
        Returns:
            True if write successful
        """
        # For write operations, the file doesn't need to exist yet
        validated_path = self._validate_path(path, must_exist=False)
        
        # Create parent directories if they don't exist
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        
        rel_path = str(validated_path.relative_to(self.workspace_dir))
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            preview = (
                f"{content[:100]}..." if len(content) > 100 else content
            )
            confirmation_details = (
                f"Writing {len(content)} bytes to {rel_path}\n"
                f"Preview: {preview}"
            )
            
            confirmed = self._request_confirmation("Write File", confirmation_details)
            
            if not confirmed:
                raise OperationCancelledError(f"Write to {rel_path} cancelled by user")
        
        self.logger.info(f"Writing to file: {validated_path}")
        with open(validated_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return True
    
    def list_directory(self, path="."):
        """
        List contents of a directory.
        
        Args:
            path: Directory to list
            
        Returns:
            List of FileInfo objects
        """
        target_dir = self._validate_path(path)
        
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {target_dir}")
        
        self.logger.info(f"Listing directory: {target_dir}")
        
        results = []
        for item in target_dir.iterdir():
            file_info = FileInfo.from_path(item, relative_to=self.workspace_dir)
            results.append(file_info)
            
        return results
    
    def create_directory(self, path, confirm=True):
        """
        Create a directory within the workspace.
        
        Args:
            path: Path to the directory
            confirm: Whether to require confirmation
            
        Returns:
            True if directory created successfully
        """
        # Directory doesn't need to exist yet
        validated_path = self._validate_path(path, must_exist=False)
        
        rel_path = str(validated_path.relative_to(self.workspace_dir))
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            confirmation_details = f"Creating directory: {rel_path}"
            confirmed = self._request_confirmation("Create Directory", confirmation_details)
            
            if not confirmed:
                raise OperationCancelledError(f"Directory creation cancelled by user")
        
        self.logger.info(f"Creating directory: {validated_path}")
        validated_path.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def delete_file(self, path, confirm=True):
        """
        Delete a file within the workspace.
        
        Args:
            path: Path to the file
            confirm: Whether to require confirmation
            
        Returns:
            True if file deleted successfully
        """
        validated_path = self._validate_path(path)
        
        if validated_path.is_dir():
            raise IsADirectoryError(f"Cannot delete directory as file: {validated_path}")
            
        rel_path = str(validated_path.relative_to(self.workspace_dir))
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            confirmation_details = f"Deleting file: {rel_path}"
            confirmed = self._request_confirmation("Delete File", confirmation_details)
            
            if not confirmed:
                raise OperationCancelledError(f"File deletion cancelled by user")
        
        self.logger.info(f"Deleting file: {validated_path}")
        os.remove(validated_path)
        
        return True
    
    def copy_file(self, source, destination, confirm=True):
        """
        Copy a file within the workspace.
        
        Args:
            source: Source path
            destination: Destination path
            confirm: Whether to require confirmation
            
        Returns:
            True if file copied successfully
        """
        src_path = self._validate_path(source)
        # Destination may not exist yet
        dest_path = self._validate_path(destination, must_exist=False)
        
        if src_path.is_dir():
            raise IsADirectoryError(f"Use copy_directory for directories: {src_path}")
            
        rel_src = str(src_path.relative_to(self.workspace_dir))
        rel_dest = str(dest_path.relative_to(self.workspace_dir))
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            confirmation_details = f"Copying file: {rel_src} -> {rel_dest}"
            confirmed = self._request_confirmation("Copy File", confirmation_details)
            
            if not confirmed:
                raise OperationCancelledError(f"File copy cancelled by user")
        
        self.logger.info(f"Copying file: {src_path} -> {dest_path}")
        
        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(src_path, dest_path)
        
        return True

def main():
    """Run a simple demo of TinyFS functionality."""
    print("TinyFS Demo")
    print("==========")
    
    # Create a workspace directory
    workspace_dir = Path("tinyfs_demo_workspace")
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(exist_ok=True)
    
    # Create a TinyFS client
    client = TinyFSClient(workspace_dir=workspace_dir, auto_confirm=True)
    
    try:
        # Create a test file
        print("\n1. Creating a test file...")
        client.write_file("test.txt", "Hello, World!\nThis is a test file.\n")
        print(f"File created: {workspace_dir}/test.txt")
        
        # Read the file
        print("\n2. Reading the file...")
        content = client.read_file("test.txt")
        print(f"File content:\n{content}")
        
        # Create a directory
        print("\n3. Creating a directory...")
        client.create_directory("subdir")
        print(f"Directory created: {workspace_dir}/subdir")
        
        # Create a file in the subdirectory
        print("\n4. Creating a file in the subdirectory...")
        client.write_file("subdir/test2.txt", "This is another test file in a subdirectory.")
        print(f"File created: {workspace_dir}/subdir/test2.txt")
        
        # List directory contents
        print("\n5. Listing directory contents...")
        files = client.list_directory(".")
        print("Files in workspace:")
        for file_info in files:
            if file_info.is_directory:
                print(f"  📁 {file_info.path}/")
            else:
                print(f"  📄 {file_info.path} ({file_info.size} bytes)")
        
        # Copy a file
        print("\n6. Copying a file...")
        client.copy_file("test.txt", "test_copy.txt")
        print(f"File copied: {workspace_dir}/test.txt -> {workspace_dir}/test_copy.txt")
        
        # Try to access a file outside the workspace (should fail)
        print("\n7. Trying to access a file outside the workspace (should fail)...")
        try:
            client.read_file("/etc/passwd")
        except PathValidationError as e:
            print(f"Security check passed: {e}")
        
        print("\nDemo completed successfully!")
        
    finally:
        # Clean up the workspace
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
            print(f"\nCleaned up workspace: {workspace_dir}")

if __name__ == "__main__":
    main() 