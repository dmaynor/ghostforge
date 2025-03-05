"""Unit tests for the command-line interface."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import GhostForge components
from ghostforge.cli import parse_args

class TestCommandLineInterface:
    """Test suite for command-line interface functionality."""
    
    def test_parse_args_analyze(self):
        """Test parsing analyze command arguments."""
        with patch.object(sys, 'argv', ['ghostforge', 'analyze', 'file.py']):
            args = parse_args()
            assert args.command == 'analyze'
            assert args.file == 'file.py'
            assert args.prompt is None  # Default value
        
        # Test with prompt option
        with patch.object(sys, 'argv', ['ghostforge', 'analyze', 'file.py', '--prompt', 'security']):
            args = parse_args()
            assert args.command == 'analyze'
            assert args.file == 'file.py'
            assert args.prompt == 'security'
    
    def test_parse_args_docker(self):
        """Test parsing docker command arguments."""
        # Test docker analyze-image
        with patch.object(sys, 'argv', ['ghostforge', 'docker', 'analyze-image', 'python:3.9']):
            args = parse_args()
            assert args.command == 'docker'
            assert args.docker_command == 'analyze-image'
            assert args.image == 'python:3.9'
        
        # Test docker analyze-container
        with patch.object(sys, 'argv', ['ghostforge', 'docker', 'analyze-container', 'web-app']):
            args = parse_args()
            assert args.command == 'docker'
            assert args.docker_command == 'analyze-container'
            assert args.container == 'web-app'
        
        # Test docker analyze-dockerfile
        with patch.object(sys, 'argv', ['ghostforge', 'docker', 'analyze-dockerfile', 'Dockerfile']):
            args = parse_args()
            assert args.command == 'docker'
            assert args.docker_command == 'analyze-dockerfile'
            assert args.dockerfile == 'Dockerfile'
    
    def test_parse_args_kubernetes(self):
        """Test parsing kubernetes command arguments."""
        # Test kubernetes analyze-manifests
        with patch.object(sys, 'argv', ['ghostforge', 'kubernetes', 'analyze-manifests', './k8s']):
            args = parse_args()
            assert args.command == 'kubernetes'
            assert args.kubernetes_command == 'analyze-manifests'
            assert args.directory == './k8s'
        
        # Test kubernetes analyze-cluster
        with patch.object(sys, 'argv', ['ghostforge', 'kubernetes', 'analyze-cluster']):
            args = parse_args()
            assert args.command == 'kubernetes'
            assert args.kubernetes_command == 'analyze-cluster'
    
    def test_parse_args_cicd(self):
        """Test parsing CI/CD command arguments."""
        with patch.object(sys, 'argv', ['ghostforge', 'cicd', 'analyze', './project']):
            args = parse_args()
            assert args.command == 'cicd'
            assert args.cicd_command == 'analyze'
            assert args.directory == './project'
    
    def test_parse_args_index(self):
        """Test parsing index command arguments."""
        # Test basic index command
        with patch.object(sys, 'argv', ['ghostforge', 'index']):
            args = parse_args()
            assert args.command == 'index'
            assert args.directory == '.'  # Default value
        
        # Test with directory specified
        with patch.object(sys, 'argv', ['ghostforge', 'index', './src']):
            args = parse_args()
            assert args.command == 'index'
            assert args.directory == './src'
    
    def test_parse_args_search(self):
        """Test parsing search command arguments."""
        with patch.object(sys, 'argv', ['ghostforge', 'search', 'function calculate_total']):
            args = parse_args()
            assert args.command == 'search'
            assert args.query == 'function calculate_total'
            assert args.file_type is None  # Default value
        
        # Test with file type filter
        with patch.object(sys, 'argv', ['ghostforge', 'search', 'error handling', '--file-type', 'py']):
            args = parse_args()
            assert args.command == 'search'
            assert args.query == 'error handling'
            assert args.file_type == 'py'
    
    def test_parse_args_shell(self):
        """Test parsing shell command arguments."""
        with patch.object(sys, 'argv', ['ghostforge', 'shell']):
            args = parse_args()
            assert args.command == 'shell'
    
    def test_parse_args_version(self):
        """Test parsing version command arguments."""
        with patch.object(sys, 'argv', ['ghostforge', '--version']):
            with pytest.raises(SystemExit) as e:
                parse_args()
            assert e.type == SystemExit
    
    def test_parse_args_help(self):
        """Test parsing help command arguments."""
        with patch.object(sys, 'argv', ['ghostforge', '--help']):
            with pytest.raises(SystemExit) as e:
                parse_args()
            assert e.type == SystemExit


@patch('ghostforge.cli.run_analyze_command')
@patch('ghostforge.cli.run_docker_command')
@patch('ghostforge.cli.run_kubernetes_command')
@patch('ghostforge.cli.run_cicd_command')
@patch('ghostforge.cli.run_index_command')
@patch('ghostforge.cli.run_search_command')
@patch('ghostforge.cli.run_shell_command')
def test_main(mock_shell, mock_search, mock_index, mock_cicd, mock_k8s, mock_docker, mock_analyze):
    """Test main function routing to appropriate command handlers."""
    from ghostforge.cli import main
    
    # Test analyze command
    with patch.object(sys, 'argv', ['ghostforge', 'analyze', 'file.py']):
        main()
        mock_analyze.assert_called_once()
        mock_docker.assert_not_called()
        mock_k8s.assert_not_called()
        mock_cicd.assert_not_called()
        mock_index.assert_not_called()
        mock_search.assert_not_called()
        mock_shell.assert_not_called()
    
    # Reset mocks
    for mock in [mock_analyze, mock_docker, mock_k8s, mock_cicd, mock_index, mock_search, mock_shell]:
        mock.reset_mock()
    
    # Test docker command
    with patch.object(sys, 'argv', ['ghostforge', 'docker', 'analyze-image', 'python:3.9']):
        main()
        mock_analyze.assert_not_called()
        mock_docker.assert_called_once()
        mock_k8s.assert_not_called()
        mock_cicd.assert_not_called()
        mock_index.assert_not_called()
        mock_search.assert_not_called()
        mock_shell.assert_not_called()
    
    # Reset mocks
    for mock in [mock_analyze, mock_docker, mock_k8s, mock_cicd, mock_index, mock_search, mock_shell]:
        mock.reset_mock()
    
    # Test kubernetes command
    with patch.object(sys, 'argv', ['ghostforge', 'kubernetes', 'analyze-cluster']):
        main()
        mock_analyze.assert_not_called()
        mock_docker.assert_not_called()
        mock_k8s.assert_called_once()
        mock_cicd.assert_not_called()
        mock_index.assert_not_called()
        mock_search.assert_not_called()
        mock_shell.assert_not_called()
    
    # Reset mocks
    for mock in [mock_analyze, mock_docker, mock_k8s, mock_cicd, mock_index, mock_search, mock_shell]:
        mock.reset_mock()
    
    # Test cicd command
    with patch.object(sys, 'argv', ['ghostforge', 'cicd', 'analyze', './project']):
        main()
        mock_analyze.assert_not_called()
        mock_docker.assert_not_called()
        mock_k8s.assert_not_called()
        mock_cicd.assert_called_once()
        mock_index.assert_not_called()
        mock_search.assert_not_called()
        mock_shell.assert_not_called()
    
    # Reset mocks
    for mock in [mock_analyze, mock_docker, mock_k8s, mock_cicd, mock_index, mock_search, mock_shell]:
        mock.reset_mock()
    
    # Test index command
    with patch.object(sys, 'argv', ['ghostforge', 'index', './src']):
        main()
        mock_analyze.assert_not_called()
        mock_docker.assert_not_called()
        mock_k8s.assert_not_called()
        mock_cicd.assert_not_called()
        mock_index.assert_called_once()
        mock_search.assert_not_called()
        mock_shell.assert_not_called()
    
    # Reset mocks
    for mock in [mock_analyze, mock_docker, mock_k8s, mock_cicd, mock_index, mock_search, mock_shell]:
        mock.reset_mock()
    
    # Test search command
    with patch.object(sys, 'argv', ['ghostforge', 'search', 'query']):
        main()
        mock_analyze.assert_not_called()
        mock_docker.assert_not_called()
        mock_k8s.assert_not_called()
        mock_cicd.assert_not_called()
        mock_index.assert_not_called()
        mock_search.assert_called_once()
        mock_shell.assert_not_called()
    
    # Reset mocks
    for mock in [mock_analyze, mock_docker, mock_k8s, mock_cicd, mock_index, mock_search, mock_shell]:
        mock.reset_mock()
    
    # Test shell command
    with patch.object(sys, 'argv', ['ghostforge', 'shell']):
        main()
        mock_analyze.assert_not_called()
        mock_docker.assert_not_called()
        mock_k8s.assert_not_called()
        mock_cicd.assert_not_called()
        mock_index.assert_not_called()
        mock_search.assert_not_called()
        mock_shell.assert_called_once() 