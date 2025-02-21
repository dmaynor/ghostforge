"""Export functionality for BuildBot."""

import json
import csv
import datetime
from typing import List, Dict, Any, Optional

class Exporter:
    """Base class for BuildBot exporters."""
    
    @staticmethod
    def export(data: List[Dict[str, Any]], format_type: str, output_file: str) -> None:
        """Export data in the specified format."""
        if format_type == "json":
            Exporter._export_json(data, output_file)
        elif format_type == "csv":
            Exporter._export_csv(data, output_file)
        else:
            Exporter._export_text(data, output_file)

    @staticmethod
    def _export_json(data: List[Dict[str, Any]], output_file: str) -> None:
        """Export data in JSON format."""
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _export_csv(data: List[Dict[str, Any]], output_file: str) -> None:
        """Export data in CSV format."""
        if not data:
            return

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(data[0].keys())
            # Write data
            for item in data:
                writer.writerow(item.values())

    @staticmethod
    def _export_text(data: List[Dict[str, Any]], output_file: str) -> None:
        """Export data in text format."""
        with open(output_file, "w") as f:
            for item in data:
                f.write("=== Entry ===\n")
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")

class AnalysisExporter(Exporter):
    """Exporter for analysis results."""
    
    @staticmethod
    def format_data(results: List[tuple]) -> List[Dict[str, Any]]:
        """Format analysis results for export."""
        return [{
            "timestamp": r[1],
            "file_path": r[2],
            "content": r[3],
            "analysis": r[4]
        } for r in results]

class SearchExporter(Exporter):
    """Exporter for search results."""
    
    @staticmethod
    def format_data(results: List[tuple]) -> List[Dict[str, Any]]:
        """Format search results for export."""
        return [{
            "path": r[0],
            "content": r[1]
        } for r in results]

class HistoryExporter(Exporter):
    """Exporter for command history."""
    
    @staticmethod
    def format_data(history: List[Dict[str, Any]], last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Format command history for export."""
        if last_n:
            history = history[-last_n:]
        
        return [{
            "timestamp": entry["timestamp"],
            "command": entry["command"]
        } for entry in history]

    @staticmethod
    def _export_text(data: List[Dict[str, Any]], output_file: str) -> None:
        """Special text format for history."""
        with open(output_file, "w") as f:
            for entry in data:
                timestamp = datetime.datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {entry['command']}\n") 