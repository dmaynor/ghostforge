"""
Integration with GhostForge shell for TinyFS functionality.
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from .client import TinyFSClient


class TinyFSCommands:
    """
    Commands for TinyFS integration with GhostForge shell.
    
    This class provides shell commands for TinyFS functionality
    that can be mixed into the GhostForge shell.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize TinyFS commands."""
        # Don't call super().__init__ here to avoid circular calls
        
        # Create TinyFS client
        workspace_dir = Path(os.getcwd())
        self.fs_client = TinyFSClient(
            workspace_dir=workspace_dir,
            auto_confirm=False,
            log_level=logging.INFO
        )
        
        self.fs_logger = logging.getLogger("tinyfs.shell")
    
    def help_fs(self):
        """Show help for TinyFS commands."""
        print("TinyFS Commands (File Operations for LLMs):")
        print("")
        print("  fs read <path>")
        print("    Read a file and display its contents")
        print("")
        print("  fs write <path> <content>")
        print("    Write content to a file")
        print("")
        print("  fs list [path]")
        print("    List directory contents (defaults to current directory)")
        print("")
        print("  fs mkdir <path>")
        print("    Create a directory")
        print("")
        print("  fs delete <path>")
        print("    Delete a file")
        print("")
        print("  fs move <source> <destination>")
        print("    Move a file from source to destination")
        print("")
        print("  fs copy <source> <destination>")
        print("    Copy a file from source to destination")
        print("")
        print("  fs exists <path> [--type=file|directory]")
        print("    Check if a file or directory exists")
        print("")
        print("  fs info <path>")
        print("    Get information about a file or directory")
    
    def do_fs(self, arg):
        """
        Execute TinyFS filesystem operations.
        
        Usage: fs <command> [arguments]
        
        Examples:
          fs read file.txt
          fs write file.txt "Hello, world!"
          fs list
          fs mkdir new_dir
          fs delete file.txt
          fs move source.txt dest.txt
          fs copy source.txt dest.txt
          fs exists file.txt
          fs info file.txt
          
        Type 'fs help' for more information.
        """
        args = arg.split()
        
        if not args:
            print("Error: No command specified.")
            print("Type 'fs help' for usage information.")
            return
        
        cmd = args[0].lower()
        
        try:
            if cmd == "help":
                self.help_fs()
                
            elif cmd == "read":
                if len(args) < 2:
                    print("Error: Missing file path.")
                    print("Usage: fs read <path>")
                    return
                    
                path = args[1]
                content = self.fs_client.read_file(path)
                print(content)
                
            elif cmd == "write":
                if len(args) < 3:
                    print("Error: Missing arguments.")
                    print("Usage: fs write <path> <content>")
                    return
                    
                path = args[1]
                # Join the rest of the arguments as the content
                content = " ".join(args[2:])
                
                self.fs_client.write_file(path, content)
                print(f"Successfully wrote to {path}")
                
            elif cmd == "list":
                path = args[1] if len(args) > 1 else "."
                files = self.fs_client.list_directory(path)
                
                print(f"Contents of {path}:")
                for f in sorted(files, key=lambda x: (not x.is_directory, x.name)):
                    if f.is_directory:
                        print(f"📁 {f.name}/")
                    else:
                        size_str = f"{f.size} bytes" if f.size is not None else "N/A"
                        print(f"📄 {f.name} ({size_str})")
                        
            elif cmd == "mkdir":
                if len(args) < 2:
                    print("Error: Missing directory path.")
                    print("Usage: fs mkdir <path>")
                    return
                    
                path = args[1]
                self.fs_client.create_directory(path)
                print(f"Successfully created directory {path}")
                
            elif cmd == "delete":
                if len(args) < 2:
                    print("Error: Missing file path.")
                    print("Usage: fs delete <path>")
                    return
                    
                path = args[1]
                self.fs_client.delete_file(path)
                print(f"Successfully deleted {path}")
                
            elif cmd == "move":
                if len(args) < 3:
                    print("Error: Missing arguments.")
                    print("Usage: fs move <source> <destination>")
                    return
                    
                source = args[1]
                destination = args[2]
                self.fs_client.move_file(source, destination)
                print(f"Successfully moved {source} to {destination}")
                
            elif cmd == "copy":
                if len(args) < 3:
                    print("Error: Missing arguments.")
                    print("Usage: fs copy <source> <destination>")
                    return
                    
                source = args[1]
                destination = args[2]
                self.fs_client.copy_file(source, destination)
                print(f"Successfully copied {source} to {destination}")
                
            elif cmd == "exists":
                if len(args) < 2:
                    print("Error: Missing file path.")
                    print("Usage: fs exists <path> [--type=file|directory]")
                    return
                    
                path = args[1]
                # Check if type was specified
                check_type = None
                if len(args) > 2:
                    type_arg = args[2]
                    if type_arg.startswith("--type="):
                        check_type = type_arg.split("=")[1]
                
                if check_type == "file":
                    exists = self.fs_client.file_exists(path)
                    entity_type = "file"
                elif check_type == "directory":
                    exists = self.fs_client.directory_exists(path)
                    entity_type = "directory"
                else:
                    # Check if either a file or directory exists
                    exists = (
                        self.fs_client.file_exists(path) or 
                        self.fs_client.directory_exists(path)
                    )
                    entity_type = "path"
                    
                if exists:
                    print(f"The {entity_type} {path} exists.")
                else:
                    print(f"The {entity_type} {path} does not exist.")
                    
            elif cmd == "info":
                if len(args) < 2:
                    print("Error: Missing file path.")
                    print("Usage: fs info <path>")
                    return
                    
                path = args[1]
                file_info = self.fs_client.get_file_info(path)
                
                if file_info is None:
                    print(f"No information available for {path}")
                    return
                    
                print(f"Information for {path}:")
                print(f"  Name: {file_info.name}")
                print(f"  Type: {'Directory' if file_info.is_directory else 'File'}")
                
                if not file_info.is_directory and file_info.size is not None:
                    print(f"  Size: {file_info.size} bytes")
                    
                if file_info.modified_time is not None:
                    from datetime import datetime
                    mod_time = datetime.fromtimestamp(file_info.modified_time)
                    print(f"  Modified: {mod_time}")
                
            else:
                print(f"Error: Unknown command '{cmd}'.")
                print("Type 'fs help' for usage information.")
                
        except Exception as e:
            print(f"Error: {e}")
            self.fs_logger.error(f"Exception in fs command: {e}", exc_info=True) 