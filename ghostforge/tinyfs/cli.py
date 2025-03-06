"""
Command-line interface for TinyFS.
"""

import argparse
import os
import sys
import logging
from pathlib import Path
import json

from .client import TinyFSClient
from .exceptions import TinyFSError, SecurityError, OperationCancelledError


def setup_args_parser():
    """Set up the argument parser for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="TinyFS - Secure Filesystem Interface for LLMs in GhostForge"
    )
    
    parser.add_argument(
        "--workspace", "-w",
        default=".",
        help="Path to the workspace directory (default: current directory)"
    )
    
    parser.add_argument(
        "--auto-confirm", "-y",
        action="store_true",
        help="Automatically confirm all operations without prompting"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Read command
    read_parser = subparsers.add_parser("read", help="Read a file")
    read_parser.add_argument("path", help="Path to the file to read")
    
    # Write command
    write_parser = subparsers.add_parser("write", help="Write to a file")
    write_parser.add_argument("path", help="Path to the file to write")
    write_parser.add_argument(
        "--content", "-c",
        help="Content to write (if not provided, read from stdin)"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List directory contents")
    list_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the directory to list (default: current directory)"
    )
    list_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format"
    )
    
    # Create directory command
    mkdir_parser = subparsers.add_parser("mkdir", help="Create a directory")
    mkdir_parser.add_argument("path", help="Path to the directory to create")
    
    # Delete file command
    delete_parser = subparsers.add_parser("delete", help="Delete a file")
    delete_parser.add_argument("path", help="Path to the file to delete")
    
    # Move file command
    move_parser = subparsers.add_parser("move", help="Move a file")
    move_parser.add_argument("source", help="Source path")
    move_parser.add_argument("destination", help="Destination path")
    
    # Copy file command
    copy_parser = subparsers.add_parser("copy", help="Copy a file")
    copy_parser.add_argument("source", help="Source path")
    copy_parser.add_argument("destination", help="Destination path")
    
    # Exists command
    exists_parser = subparsers.add_parser("exists", help="Check if a file or directory exists")
    exists_parser.add_argument("path", help="Path to check")
    exists_parser.add_argument(
        "--type", "-t",
        choices=["file", "directory"],
        help="Type of path to check for"
    )
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Get information about a file or directory")
    info_parser.add_argument("path", help="Path to get information about")
    
    return parser


def execute_command(args):
    """Execute the command specified by the parsed arguments."""
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create the client
    workspace_path = Path(os.path.abspath(args.workspace))
    client = TinyFSClient(
        workspace_dir=workspace_path,
        auto_confirm=args.auto_confirm,
        log_level=log_level
    )
    
    # Execute the appropriate command
    try:
        if args.command == "read":
            content = client.read_file(args.path)
            print(content, end="")
            return 0
            
        elif args.command == "write":
            # Get content from argument or stdin
            if args.content is not None:
                content = args.content
            else:
                content = sys.stdin.read()
                
            client.write_file(args.path, content)
            print(f"Successfully wrote to {args.path}")
            return 0
            
        elif args.command == "list":
            files = client.list_directory(args.path)
            
            if args.json:
                # Convert to dictionary and print as JSON
                files_dict = [
                    {
                        "name": f.name,
                        "path": f.path,
                        "type": "directory" if f.is_directory else "file",
                        "size": f.size
                    }
                    for f in files
                ]
                print(json.dumps(files_dict, indent=2))
            else:
                # Print in a human-readable format
                print(f"Contents of {args.path}:")
                for f in sorted(files, key=lambda x: (not x.is_directory, x.name)):
                    if f.is_directory:
                        print(f"📁 {f.name}/")
                    else:
                        size_str = f"{f.size} bytes" if f.size is not None else "N/A"
                        print(f"📄 {f.name} ({size_str})")
            return 0
            
        elif args.command == "mkdir":
            client.create_directory(args.path)
            print(f"Successfully created directory {args.path}")
            return 0
            
        elif args.command == "delete":
            client.delete_file(args.path)
            print(f"Successfully deleted {args.path}")
            return 0
            
        elif args.command == "move":
            client.move_file(args.source, args.destination)
            print(f"Successfully moved {args.source} to {args.destination}")
            return 0
            
        elif args.command == "copy":
            client.copy_file(args.source, args.destination)
            print(f"Successfully copied {args.source} to {args.destination}")
            return 0
            
        elif args.command == "exists":
            if args.type == "file":
                exists = client.file_exists(args.path)
                entity_type = "file"
            elif args.type == "directory":
                exists = client.directory_exists(args.path)
                entity_type = "directory"
            else:
                # Check if either a file or directory exists
                exists = (
                    client.file_exists(args.path) or 
                    client.directory_exists(args.path)
                )
                entity_type = "path"
                
            if exists:
                print(f"The {entity_type} {args.path} exists.")
                return 0
            else:
                print(f"The {entity_type} {args.path} does not exist.")
                return 1
                
        elif args.command == "info":
            file_info = client.get_file_info(args.path)
            
            if file_info is None:
                print(f"No information available for {args.path}")
                return 1
                
            print(f"Information for {args.path}:")
            print(f"  Name: {file_info.name}")
            print(f"  Type: {'Directory' if file_info.is_directory else 'File'}")
            
            if not file_info.is_directory and file_info.size is not None:
                print(f"  Size: {file_info.size} bytes")
                
            if file_info.modified_time is not None:
                from datetime import datetime
                mod_time = datetime.fromtimestamp(file_info.modified_time)
                print(f"  Modified: {mod_time}")
                
            return 0
            
        else:
            # No command specified or unrecognized command
            print("Error: No command specified. Run with --help for usage information.")
            return 1
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except SecurityError as e:
        print(f"Security Error: {e}")
        return 2
    except OperationCancelledError as e:
        print(f"Operation Cancelled: {e}")
        return 3
    except TinyFSError as e:
        print(f"TinyFS Error: {e}")
        return 4
    except Exception as e:
        print(f"Unexpected Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 5


def main():
    """Main entry point for the CLI."""
    parser = setup_args_parser()
    args = parser.parse_args()
    
    return execute_command(args)


if __name__ == "__main__":
    sys.exit(main()) 