"""BuildBot - An AI-powered troubleshooting assistant."""

__version__ = "0.1.0"
__author__ = "David Maynor"
__email__ = "dmaynor@gmail.com"

from .shell import BuildBotShell
from .exporters import Exporter, AnalysisExporter, SearchExporter, HistoryExporter
from .ci_cd import CIManager, GitHubActions, GitLabCI, JenkinsCI
from .kubernetes import KubernetesManager, KubernetesAnalyzer
from .docker_remote import DockerRemoteManager

__all__ = [
    "BuildBotShell",
    "Exporter",
    "AnalysisExporter",
    "SearchExporter",
    "HistoryExporter",
    "CIManager",
    "GitHubActions",
    "GitLabCI",
    "JenkinsCI",
    "KubernetesManager",
    "KubernetesAnalyzer",
    "DockerRemoteManager",
] 