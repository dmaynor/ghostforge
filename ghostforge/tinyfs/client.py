"""
Core TinyFS client implementation for secure filesystem operations.
"""

import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import shutil

from .models import FileInfo, ActionRecord, CommandResult, ActionType, OperationSecurity
from .exceptions import (
    SecurityError, 
    PathValidationError, 
    OperationNotAllowedError,
    OperationCancelledError
)


class TinyFSClient:
    """Core filesystem operations client for Tiny LLM."""
    
    def __init__(
        self, 
        workspace_dir: Union[str, Path],
        auto_confirm: bool = False,
        log_level: int = logging.INFO,
        history_size: int = 100
    ):
        """
        Initialize the filesystem client with security boundaries.
        
        Args:
            workspace_dir: Root directory for all operations
            auto_confirm: Whether to auto-confirm operations
            log_level: Logging verbosity
            history_size: Maximum number of actions to keep in history
        """
        self.workspace_dir = Path(workspace_dir).resolve()
        self.auto_confirm = auto_confirm
        self.logger = self._setup_logger(log_level)
        self.history_size = history_size
        self.action_history: List[ActionRecord] = []
        
        # Create workspace directory if it doesn't exist
        if not self.workspace_dir.exists():
            self.logger.info(f"Creating workspace directory: {self.workspace_dir}")
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            
        self.logger.info(f"Initialized TinyFSClient with workspace: {self.workspace_dir}")
    
    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Configure logging for the client."""
        logger = logging.getLogger("tinyfs")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        logger.setLevel(log_level)
        return logger
    
    def _record_action(self, action: ActionRecord) -> None:
        """Record an action in the history."""
        self.action_history.append(action)
        
        # Trim history if it exceeds the maximum size
        if len(self.action_history) > self.history_size:
            self.action_history = self.action_history[-self.history_size:]
    
    def _validate_path(self, path: Union[str, Path], must_exist: bool = True) -> Path:
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
    
    def _request_confirmation(self, operation: str, details: str) -> bool:
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
            
        # In a real implementation, this would interact with the user
        # For now, we'll just log and return True
        self.logger.info(f"Requesting confirmation for: {operation}\nDetails: {details}")
        
        # TODO: Implement actual confirmation mechanism
        # This could be a callback, a CLI prompt, a GUI dialog, etc.
        return True
    
    def get_history(self) -> List[ActionRecord]:
        """Get the action history."""
        return self.action_history.copy()
        
    def read_file(self, path: Union[str, Path]) -> str:
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
            
        action = ActionRecord.create(
            action_type=ActionType.READ,
            path=str(validated_path.relative_to(self.workspace_dir))
        )
        
        try:
            self.logger.info(f"Reading file: {validated_path}")
            with open(validated_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            action.success = True
            return content
        except Exception as e:
            action.success = False
            action.error_message = str(e)
            self.logger.error(f"Failed to read file: {e}")
            raise
        finally:
            self._record_action(action)
    
    def write_file(
        self, 
        path: Union[str, Path], 
        content: str,
        confirm: bool = True
    ) -> bool:
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
        
        action = ActionRecord.create(
            action_type=ActionType.WRITE,
            path=rel_path
        )
        
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
            action.user_approved = confirmed
            
            if not confirmed:
                action.success = False
                action.error_message = "Operation cancelled by user"
                self._record_action(action)
                raise OperationCancelledError(f"Write to {rel_path} cancelled by user")
        
        try:
            self.logger.info(f"Writing to file: {validated_path}")
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            action.success = True
            return True
        except Exception as e:
            action.success = False
            action.error_message = str(e)
            self.logger.error(f"Failed to write file: {e}")
            raise
        finally:
            self._record_action(action)
    
    def list_directory(self, path: Union[str, Path] = ".") -> List[FileInfo]:
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
        
        rel_path = str(target_dir.relative_to(self.workspace_dir))
        
        action = ActionRecord.create(
            action_type=ActionType.READ,
            path=rel_path
        )
        
        try:
            self.logger.info(f"Listing directory: {target_dir}")
            
            results = []
            for item in target_dir.iterdir():
                file_info = FileInfo.from_path(item, relative_to=self.workspace_dir)
                results.append(file_info)
                
            action.success = True
            return results
        except Exception as e:
            action.success = False
            action.error_message = str(e)
            self.logger.error(f"Failed to list directory: {e}")
            raise
        finally:
            self._record_action(action)
    
    def create_directory(
        self, 
        path: Union[str, Path],
        confirm: bool = True
    ) -> bool:
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
        
        action = ActionRecord.create(
            action_type=ActionType.WRITE,
            path=rel_path
        )
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            confirmation_details = f"Creating directory: {rel_path}"
            confirmed = self._request_confirmation("Create Directory", confirmation_details)
            action.user_approved = confirmed
            
            if not confirmed:
                action.success = False
                action.error_message = "Operation cancelled by user"
                self._record_action(action)
                raise OperationCancelledError(f"Directory creation cancelled by user")
        
        try:
            self.logger.info(f"Creating directory: {validated_path}")
            validated_path.mkdir(parents=True, exist_ok=True)
            
            action.success = True
            return True
        except Exception as e:
            action.success = False
            action.error_message = str(e)
            self.logger.error(f"Failed to create directory: {e}")
            raise
        finally:
            self._record_action(action)
    
    def delete_file(
        self, 
        path: Union[str, Path],
        confirm: bool = True
    ) -> bool:
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
        
        action = ActionRecord.create(
            action_type=ActionType.WRITE,  # Delete is considered a write operation
            path=rel_path
        )
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            confirmation_details = f"Deleting file: {rel_path}"
            confirmed = self._request_confirmation("Delete File", confirmation_details)
            action.user_approved = confirmed
            
            if not confirmed:
                action.success = False
                action.error_message = "Operation cancelled by user"
                self._record_action(action)
                raise OperationCancelledError(f"File deletion cancelled by user")
        
        try:
            self.logger.info(f"Deleting file: {validated_path}")
            os.remove(validated_path)
            
            action.success = True
            return True
        except Exception as e:
            action.success = False
            action.error_message = str(e)
            self.logger.error(f"Failed to delete file: {e}")
            raise
        finally:
            self._record_action(action)
    
    def move_file(
        self, 
        source: Union[str, Path],
        destination: Union[str, Path],
        confirm: bool = True
    ) -> bool:
        """
        Move a file within the workspace.
        
        Args:
            source: Source path
            destination: Destination path
            confirm: Whether to require confirmation
            
        Returns:
            True if file moved successfully
        """
        src_path = self._validate_path(source)
        # Destination may not exist yet
        dest_path = self._validate_path(destination, must_exist=False)
        
        if src_path.is_dir():
            raise IsADirectoryError(f"Use move_directory for directories: {src_path}")
            
        rel_src = str(src_path.relative_to(self.workspace_dir))
        rel_dest = str(dest_path.relative_to(self.workspace_dir))
        
        action = ActionRecord.create(
            action_type=ActionType.WRITE,
            path=f"{rel_src} -> {rel_dest}"
        )
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            confirmation_details = f"Moving file: {rel_src} -> {rel_dest}"
            confirmed = self._request_confirmation("Move File", confirmation_details)
            action.user_approved = confirmed
            
            if not confirmed:
                action.success = False
                action.error_message = "Operation cancelled by user"
                self._record_action(action)
                raise OperationCancelledError(f"File move cancelled by user")
        
        try:
            self.logger.info(f"Moving file: {src_path} -> {dest_path}")
            
            # Create parent directories if they don't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(src_path, dest_path)
            
            action.success = True
            return True
        except Exception as e:
            action.success = False
            action.error_message = str(e)
            self.logger.error(f"Failed to move file: {e}")
            raise
        finally:
            self._record_action(action)
    
    def copy_file(
        self, 
        source: Union[str, Path],
        destination: Union[str, Path],
        confirm: bool = True
    ) -> bool:
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
        
        action = ActionRecord.create(
            action_type=ActionType.WRITE,
            path=f"{rel_src} -> {rel_dest}"
        )
        
        # Check if this needs confirmation
        if confirm and not self.auto_confirm:
            confirmation_details = f"Copying file: {rel_src} -> {rel_dest}"
            confirmed = self._request_confirmation("Copy File", confirmation_details)
            action.user_approved = confirmed
            
            if not confirmed:
                action.success = False
                action.error_message = "Operation cancelled by user"
                self._record_action(action)
                raise OperationCancelledError(f"File copy cancelled by user")
        
        try:
            self.logger.info(f"Copying file: {src_path} -> {dest_path}")
            
            # Create parent directories if they don't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(src_path, dest_path)
            
            action.success = True
            return True
        except Exception as e:
            action.success = False
            action.error_message = str(e)
            self.logger.error(f"Failed to copy file: {e}")
            raise
        finally:
            self._record_action(action)
    
    def file_exists(self, path: Union[str, Path]) -> bool:
        """
        Check if a file exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists
        """
        try:
            validated_path = self._validate_path(path, must_exist=False)
            return validated_path.exists() and validated_path.is_file()
        except SecurityError:
            # If path validation fails, treat as if file doesn't exist
            return False
    
    def directory_exists(self, path: Union[str, Path]) -> bool:
        """
        Check if a directory exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if directory exists
        """
        try:
            validated_path = self._validate_path(path, must_exist=False)
            return validated_path.exists() and validated_path.is_dir()
        except SecurityError:
            # If path validation fails, treat as if directory doesn't exist
            return False
            
    def get_file_info(self, path: Union[str, Path]) -> Optional[FileInfo]:
        """
        Get information about a file or directory.
        
        Args:
            path: Path to check
            
        Returns:
            FileInfo object if file exists, None otherwise
        """
        try:
            validated_path = self._validate_path(path)
            return FileInfo.from_path(validated_path, relative_to=self.workspace_dir)
        except (SecurityError, FileNotFoundError):
            return None 