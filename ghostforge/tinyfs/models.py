"""
Data models for the TinyFS module.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
import time


class OperationSecurity(Enum):
    """Security levels for filesystem operations."""
    READ_ONLY = 1  # Safe operations like reading files
    WRITE = 2      # Potentially dangerous write operations
    EXECUTE = 3    # Command execution (highest risk)


class ActionType(Enum):
    """Types of actions the filesystem tool can perform."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    GIT = "git"
    ENV = "env"


@dataclass
class FileInfo:
    """Information about a file or directory."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified_time: Optional[float] = None
    
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


@dataclass
class ActionRecord:
    """Record of an action performed by the tool."""
    action_type: ActionType
    timestamp: float
    path: Optional[str] = None
    command: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    user_approved: bool = False
    
    @classmethod
    def create(cls, action_type, path=None, command=None, success=True, 
               error_message=None, user_approved=False):
        """Create a new action record with the current timestamp."""
        return cls(
            action_type=action_type,
            timestamp=time.time(),
            path=path,
            command=command,
            success=success,
            error_message=error_message,
            user_approved=user_approved
        )


@dataclass
class CommandResult:
    """Result of a command execution."""
    stdout: str
    stderr: str
    return_code: int
    success: bool
    duration: float 