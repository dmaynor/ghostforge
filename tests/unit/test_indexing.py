"""Unit tests for the file indexing functionality."""

import os
import pytest
import tempfile
from pathlib import Path

# Import GhostForge components
from ghostforge.shell import GhostForgeShell

def test_file_indexing_basic(temp_workspace, mock_config):
    """Test basic file indexing functionality."""
    # Create a test file
    test_file = temp_workspace / "test.txt"
    test_file.write_text("This is a test file with some sample content for indexing.")
    
    # Initialize shell
    shell = GhostForgeShell()
    shell.db_conn = shell.init_database()
    
    # Run indexing on the temp workspace
    os.chdir(temp_workspace)
    shell.do_index(".")
    
    # Query the database to verify the file was indexed
    cursor = shell.db_conn.cursor()
    cursor.execute("SELECT * FROM files WHERE path = ?", (str(Path("test.txt")),))
    indexed_file = cursor.fetchone()
    
    assert indexed_file is not None
    assert indexed_file[1] == str(Path("test.txt"))  # Path
    assert "sample content" in indexed_file[2]  # Content

def test_file_indexing_with_exclusions(temp_workspace, mock_config):
    """Test file indexing with exclusions."""
    # Create test files
    (temp_workspace / "include.txt").write_text("This file should be indexed")
    (temp_workspace / "exclude.bin").write_text("This file should be excluded")
    (temp_workspace / ".hidden").write_text("This hidden file should be excluded")
    
    # Create a nested directory
    nested_dir = temp_workspace / "nested"
    nested_dir.mkdir()
    (nested_dir / "nested_file.txt").write_text("This nested file should be indexed")
    
    # Initialize shell
    shell = GhostForgeShell()
    shell.db_conn = shell.init_database()
    
    # Run indexing on the temp workspace
    os.chdir(temp_workspace)
    shell.do_index(".")
    
    # Query the database to verify correct indexing
    cursor = shell.db_conn.cursor()
    
    # Include.txt should be indexed
    cursor.execute("SELECT * FROM files WHERE path = ?", (str(Path("include.txt")),))
    include_file = cursor.fetchone()
    assert include_file is not None
    
    # Exclude.bin should not be indexed (binary file)
    cursor.execute("SELECT * FROM files WHERE path = ?", (str(Path("exclude.bin")),))
    exclude_file = cursor.fetchone()
    assert exclude_file is None
    
    # .hidden should not be indexed (hidden file)
    cursor.execute("SELECT * FROM files WHERE path = ?", (str(Path(".hidden")),))
    hidden_file = cursor.fetchone()
    assert hidden_file is None
    
    # Nested file should be indexed
    cursor.execute("SELECT * FROM files WHERE path LIKE ?", ("%nested_file.txt",))
    nested_file = cursor.fetchone()
    assert nested_file is not None

def test_search_functionality(temp_workspace, mock_config):
    """Test search functionality after indexing."""
    # Create test files with specific content
    (temp_workspace / "file1.txt").write_text("This file contains apple and banana")
    (temp_workspace / "file2.txt").write_text("This file contains orange and grape")
    (temp_workspace / "file3.log").write_text("Error: Could not find apple")
    
    # Initialize shell
    shell = GhostForgeShell()
    shell.db_conn = shell.init_database()
    
    # Run indexing on the temp workspace
    os.chdir(temp_workspace)
    shell.do_index(".")
    
    # Use the search command and capture results
    # Since do_search prints to stdout, we need to monkey patch it
    search_results = []
    
    def mock_print(*args, **kwargs):
        search_results.append(" ".join(str(arg) for arg in args))
    
    # Save original print function
    original_print = print
    
    try:
        # Monkey patch print function
        __builtins__["print"] = mock_print
        
        # Search for 'apple'
        shell.do_search("apple")
        
        # Check results
        result_texts = "\n".join(search_results)
        assert "file1.txt" in result_texts
        assert "file3.log" in result_texts
        assert "file2.txt" not in result_texts
        
        # Reset results for next search
        search_results.clear()
        
        # Search with type filter
        shell.do_search("apple --type=log")
        
        # Check filtered results
        result_texts = "\n".join(search_results)
        assert "file3.log" in result_texts
        assert "file1.txt" not in result_texts
        
    finally:
        # Restore original print function
        __builtins__["print"] = original_print 