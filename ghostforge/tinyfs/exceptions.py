"""
Exceptions for the TinyFS module.
"""

class TinyFSError(Exception):
    """Base exception for all TinyFS errors."""
    pass

class SecurityError(TinyFSError):
    """Exception raised for security violations."""
    pass

class PathValidationError(SecurityError):
    """Exception raised when a path fails validation."""
    pass

class OperationNotAllowedError(SecurityError):
    """Exception raised when an operation is not allowed due to security restrictions."""
    pass

class SandboxError(TinyFSError):
    """Exception raised for sandbox-related errors."""
    pass

class CommandExecutionError(TinyFSError):
    """Exception raised when a command execution fails."""
    pass

class OperationCancelledError(TinyFSError):
    """Exception raised when an operation is cancelled by the user."""
    pass 