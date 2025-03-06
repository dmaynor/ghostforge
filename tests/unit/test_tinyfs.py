"""Unit tests for the TinyFS module."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from ghostforge.tinyfs.client import TinyFSClient
from ghostforge.tinyfs.exceptions import PathValidationError, OperationCancelledError
from ghostforge.tinyfs.models import FileInfo, ActionType


class TestTinyFSClient:
    """Test suite for TinyFSClient."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp(prefix="tinyfs_test_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def fs_client(self, temp_workspace):
        """Create a TinyFSClient instance with auto-confirm enabled."""
        return TinyFSClient(workspace_dir=temp_workspace, auto_confirm=True)
    
    @pytest.fixture
    def interactive_client(self, temp_workspace):
        """Create a TinyFSClient instance with confirmation required."""
        return TinyFSClient(workspace_dir=temp_workspace, auto_confirm=False)
    
    @pytest.fixture
    def sample_file(self, temp_workspace):
        """Create a sample file in the workspace."""
        file_path = temp_workspace / "sample.txt"
        with open(file_path, "w") as f:
            f.write("Hello, world!")
        return file_path
    
    @pytest.fixture
    def sample_dir(self, temp_workspace):
        """Create a sample directory structure in the workspace."""
        dir_path = temp_workspace / "sample_dir"
        dir_path.mkdir(exist_ok=True)
        
        # Create some files in the directory
        (dir_path / "file1.txt").write_text("File 1 content")
        (dir_path / "file2.txt").write_text("File 2 content")
        
        # Create a subdirectory
        subdir = dir_path / "subdir"
        subdir.mkdir(exist_ok=True)
        (subdir / "file3.txt").write_text("File 3 content")
        
        return dir_path
    
    def test_init(self, temp_workspace):
        """Test client initialization."""
        client = TinyFSClient(workspace_dir=temp_workspace)
        
        assert client.workspace_dir == temp_workspace
        assert client.auto_confirm is False
        assert len(client.action_history) == 0
    
    def test_validate_path_inside_workspace(self, fs_client, temp_workspace):
        """Test path validation for paths inside the workspace."""
        # Test with absolute path
        abs_path = temp_workspace / "test.txt"
        validated = fs_client._validate_path(abs_path, must_exist=False)
        assert validated == abs_path
        
        # Test with relative path
        rel_path = "test.txt"
        validated = fs_client._validate_path(rel_path, must_exist=False)
        assert validated == temp_workspace / "test.txt"
    
    def test_validate_path_outside_workspace(self, fs_client, temp_workspace):
        """Test path validation for paths outside the workspace."""
        outside_path = Path("/tmp/outside.txt")
        
        with pytest.raises(PathValidationError):
            fs_client._validate_path(outside_path)
        
        # Test with a tricky path that tries to escape using ..
        escape_path = str(temp_workspace) + "/../outside.txt"
        
        with pytest.raises(PathValidationError):
            fs_client._validate_path(escape_path)
    
    def test_read_file(self, fs_client, sample_file):
        """Test reading a file."""
        content = fs_client.read_file(sample_file)
        assert content == "Hello, world!"
        
        # Check that the action was recorded
        history = fs_client.get_history()
        assert len(history) == 1
        assert history[0].action_type == ActionType.READ
        assert history[0].path == "sample.txt"
        assert history[0].success is True
    
    def test_read_file_not_found(self, fs_client, temp_workspace):
        """Test reading a non-existent file."""
        non_existent = temp_workspace / "non_existent.txt"
        
        with pytest.raises(FileNotFoundError):
            fs_client.read_file(non_existent)
    
    def test_read_file_is_directory(self, fs_client, sample_dir):
        """Test reading a directory as a file."""
        with pytest.raises(IsADirectoryError):
            fs_client.read_file(sample_dir)
    
    def test_write_file(self, fs_client, temp_workspace):
        """Test writing to a file."""
        file_path = temp_workspace / "new_file.txt"
        content = "This is a test file."
        
        result = fs_client.write_file(file_path, content)
        assert result is True
        
        # Verify the file was created with the correct content
        assert file_path.exists()
        assert file_path.read_text() == content
        
        # Check that the action was recorded
        history = fs_client.get_history()
        assert len(history) == 1
        assert history[0].action_type == ActionType.WRITE
        assert history[0].path == "new_file.txt"
        assert history[0].success is True
    
    def test_write_file_with_confirmation(self, interactive_client, temp_workspace):
        """Test writing to a file with confirmation."""
        file_path = temp_workspace / "confirm_file.txt"
        content = "This file requires confirmation."
        
        # Mock the confirmation to return True
        with patch.object(interactive_client, '_request_confirmation', return_value=True):
            result = interactive_client.write_file(file_path, content)
            assert result is True
            
            # Verify the file was created
            assert file_path.exists()
            assert file_path.read_text() == content
        
        # Mock the confirmation to return False
        with patch.object(interactive_client, '_request_confirmation', return_value=False):
            with pytest.raises(OperationCancelledError):
                interactive_client.write_file(file_path, "This should not be written.")
    
    def test_list_directory(self, fs_client, sample_dir):
        """Test listing the contents of a directory."""
        files = fs_client.list_directory(sample_dir)
        
        # Check that we found the correct number of items
        assert len(files) == 3  # 2 files + 1 subdirectory
        
        # Check that each item has the right properties
        names = {f.name for f in files}
        assert names == {"file1.txt", "file2.txt", "subdir"}
        
        # Check that types are correct
        for file_info in files:
            if file_info.name == "subdir":
                assert file_info.is_directory is True
                assert file_info.size is None  # Directories don't have a size
            else:
                assert file_info.is_directory is False
                assert file_info.size is not None
        
        # Check the action history
        history = fs_client.get_history()
        assert len(history) == 1
        assert history[0].action_type == ActionType.READ
        assert history[0].path == "sample_dir"
    
    def test_list_directory_not_found(self, fs_client, temp_workspace):
        """Test listing a non-existent directory."""
        non_existent = temp_workspace / "non_existent_dir"
        
        with pytest.raises(FileNotFoundError):
            fs_client.list_directory(non_existent)
    
    def test_list_directory_not_a_directory(self, fs_client, sample_file):
        """Test listing a file as a directory."""
        with pytest.raises(NotADirectoryError):
            fs_client.list_directory(sample_file)
    
    def test_create_directory(self, fs_client, temp_workspace):
        """Test creating a directory."""
        dir_path = temp_workspace / "new_dir"
        
        result = fs_client.create_directory(dir_path)
        assert result is True
        
        # Verify the directory was created
        assert dir_path.exists()
        assert dir_path.is_dir()
        
        # Check the action history
        history = fs_client.get_history()
        assert len(history) == 1
        assert history[0].action_type == ActionType.WRITE
        assert history[0].path == "new_dir"
    
    def test_create_nested_directory(self, fs_client, temp_workspace):
        """Test creating a nested directory structure."""
        dir_path = temp_workspace / "parent" / "child" / "grandchild"
        
        result = fs_client.create_directory(dir_path)
        assert result is True
        
        # Verify the directory hierarchy was created
        assert dir_path.exists()
        assert dir_path.is_dir()
        assert (temp_workspace / "parent" / "child").is_dir()
        assert (temp_workspace / "parent").is_dir()
    
    def test_create_existing_directory(self, fs_client, sample_dir):
        """Test creating a directory that already exists."""
        # This should succeed without error (exist_ok=True)
        result = fs_client.create_directory(sample_dir)
        assert result is True
    
    def test_delete_file(self, fs_client, sample_file):
        """Test deleting a file."""
        assert sample_file.exists()
        
        result = fs_client.delete_file(sample_file)
        assert result is True
        
        # Verify the file was deleted
        assert not sample_file.exists()
        
        # Check the action history
        history = fs_client.get_history()
        assert len(history) == 1
        assert history[0].action_type == ActionType.WRITE
        assert history[0].path == "sample.txt"
    
    def test_delete_file_not_found(self, fs_client, temp_workspace):
        """Test deleting a non-existent file."""
        non_existent = temp_workspace / "non_existent.txt"
        
        with pytest.raises(FileNotFoundError):
            fs_client.delete_file(non_existent)
    
    def test_delete_file_is_directory(self, fs_client, sample_dir):
        """Test deleting a directory as a file."""
        with pytest.raises(IsADirectoryError):
            fs_client.delete_file(sample_dir)
    
    def test_move_file(self, fs_client, sample_file, temp_workspace):
        """Test moving a file."""
        dest_path = temp_workspace / "moved.txt"
        
        result = fs_client.move_file(sample_file, dest_path)
        assert result is True
        
        # Verify the file was moved
        assert not sample_file.exists()
        assert dest_path.exists()
        assert dest_path.read_text() == "Hello, world!"
        
        # Check the action history
        history = fs_client.get_history()
        assert len(history) == 1
        assert history[0].action_type == ActionType.WRITE
        assert "sample.txt -> moved.txt" in history[0].path
    
    def test_copy_file(self, fs_client, sample_file, temp_workspace):
        """Test copying a file."""
        dest_path = temp_workspace / "copied.txt"
        
        result = fs_client.copy_file(sample_file, dest_path)
        assert result is True
        
        # Verify the file was copied
        assert sample_file.exists()  # Original still exists
        assert dest_path.exists()
        assert dest_path.read_text() == "Hello, world!"
        
        # Check the action history
        history = fs_client.get_history()
        assert len(history) == 1
        assert history[0].action_type == ActionType.WRITE
        assert "sample.txt -> copied.txt" in history[0].path
    
    def test_file_exists(self, fs_client, sample_file, temp_workspace):
        """Test checking if a file exists."""
        # Existing file
        assert fs_client.file_exists(sample_file) is True
        
        # Non-existent file
        non_existent = temp_workspace / "non_existent.txt"
        assert fs_client.file_exists(non_existent) is False
        
        # Directory (not a file)
        dir_path = temp_workspace / "test_dir"
        dir_path.mkdir()
        assert fs_client.file_exists(dir_path) is False
    
    def test_directory_exists(self, fs_client, sample_dir, temp_workspace):
        """Test checking if a directory exists."""
        # Existing directory
        assert fs_client.directory_exists(sample_dir) is True
        
        # Non-existent directory
        non_existent = temp_workspace / "non_existent_dir"
        assert fs_client.directory_exists(non_existent) is False
        
        # File (not a directory)
        assert fs_client.directory_exists(sample_dir / "file1.txt") is False
    
    def test_get_file_info(self, fs_client, sample_file, sample_dir):
        """Test getting file information."""
        # Get info for a file
        file_info = fs_client.get_file_info(sample_file)
        assert file_info is not None
        assert file_info.name == "sample.txt"
        assert file_info.is_directory is False
        assert file_info.size == 13  # "Hello, world!" is 13 bytes
        
        # Get info for a directory
        dir_info = fs_client.get_file_info(sample_dir)
        assert dir_info is not None
        assert dir_info.name == "sample_dir"
        assert dir_info.is_directory is True
        assert dir_info.size is None
        
        # Get info for a non-existent path
        non_existent = fs_client.get_file_info(sample_dir / "non_existent.txt")
        assert non_existent is None 