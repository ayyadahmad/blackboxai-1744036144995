#!/usr/bin/env python3

import os
import re
import hashlib
import fnmatch
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

class DriveUtilities:
    """Utility functions for Google Drive operations."""

    @staticmethod
    def setup_logging(config: Dict[str, Any]) -> logging.Logger:
        """
        Set up logging configuration.
        
        Args:
            config: Configuration dictionary containing logging settings
        
        Returns:
            logging.Logger: Configured logger instance
        """
        log_config = config.get('logging', {})
        log_file = log_config.get('file', 'audit.log')
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_format = log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s')

        # Create logger
        logger = logging.getLogger('gdrive_tool')
        logger.setLevel(log_level)

        # Create handlers
        file_handler = logging.FileHandler(log_file)
        console_handler = logging.StreamHandler()

        # Create formatters and add it to handlers
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    @staticmethod
    def extract_file_id_from_url(url: str) -> Optional[str]:
        """
        Extract Google Drive file ID from various types of Google Drive URLs.
        
        Args:
            url: Google Drive URL
            
        Returns:
            str: File ID if found, None otherwise
            
        Examples:
            >>> extract_file_id_from_url("https://drive.google.com/file/d/1234567890/view")
            "1234567890"
            >>> extract_file_id_from_url("https://drive.google.com/drive/folders/1234567890")
            "1234567890"
        """
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'/folders/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
            r'/drive/([a-zA-Z0-9_-]+)'
        ]

        parsed_url = urlparse(url)
        
        # Try to extract ID using patterns
        for pattern in patterns:
            match = re.search(pattern, parsed_url.path)
            if match:
                return match.group(1)

        # Try to get ID from query parameters
        query_params = parse_qs(parsed_url.query)
        if 'id' in query_params:
            return query_params['id'][0]

        return None

    @staticmethod
    def compute_file_checksum(file_path: str, block_size: int = 65536) -> str:
        """
        Compute SHA-256 checksum of a file.
        
        Args:
            file_path: Path to the file
            block_size: Size of blocks to read
            
        Returns:
            str: Hexadecimal representation of the file's SHA-256 hash
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                sha256_hash.update(block)
                
        return sha256_hash.hexdigest()

    @staticmethod
    def pattern_matches(filename: str, pattern: str) -> bool:
        """
        Check if filename matches the given pattern.
        Supports both glob patterns and regex patterns.
        
        Args:
            filename: Name of the file to check
            pattern: Pattern to match against (glob or regex)
            
        Returns:
            bool: True if filename matches the pattern, False otherwise
        """
        # Try regex first
        try:
            if pattern.startswith('r:'):
                # Remove the 'r:' prefix for regex patterns
                regex_pattern = pattern[2:]
                return bool(re.match(regex_pattern, filename))
        except re.error:
            pass

        # Fall back to glob pattern matching
        return fnmatch.fnmatch(filename, pattern)

    @staticmethod
    def get_mime_type(filename: str) -> str:
        """
        Get the MIME type for a file based on its extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            str: MIME type of the file
        """
        extension_map = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.zip': 'application/zip',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript'
        }
        
        ext = os.path.splitext(filename)[1].lower()
        return extension_map.get(ext, 'application/octet-stream')

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            str: Formatted size string (e.g., "1.23 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def is_valid_path(path: str) -> bool:
        """
        Validate if a path is safe and valid.
        
        Args:
            path: Path to validate
            
        Returns:
            bool: True if path is valid, False otherwise
        """
        try:
            # Normalize path
            normalized_path = os.path.normpath(path)
            
            # Check for path traversal attempts
            if '..' in normalized_path.split(os.sep):
                return False
                
            # Check if path is absolute
            if os.path.isabs(normalized_path):
                return False
                
            return True
        except Exception:
            return False

    @staticmethod
    def parse_schedule(schedule: str) -> int:
        """
        Parse schedule string into seconds.
        
        Args:
            schedule: Schedule string (e.g., "1h", "1d", "1w")
            
        Returns:
            int: Number of seconds
        """
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        match = re.match(r'(\d+)([smhdw])', schedule.lower())
        if not match:
            raise ValueError("Invalid schedule format. Use format like '1h', '1d', '1w'")
            
        value, unit = match.groups()
        return int(value) * units[unit]

    @staticmethod
    def generate_backup_path(base_path: str, original_name: str) -> str:
        """
        Generate a backup path with timestamp.
        
        Args:
            base_path: Base backup directory path
            original_name: Original filename
            
        Returns:
            str: Backup path with timestamp
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename, ext = os.path.splitext(original_name)
        return os.path.join(base_path, f"{filename}_{timestamp}{ext}")

if __name__ == "__main__":
    # Example usage and testing
    utils = DriveUtilities()
    
    # Test URL parsing
    test_url = "https://drive.google.com/file/d/1234567890/view"
    file_id = utils.extract_file_id_from_url(test_url)
    print(f"Extracted file ID: {file_id}")
    
    # Test pattern matching
    filename = "document.txt"
    pattern = "*.txt"
    matches = utils.pattern_matches(filename, pattern)
    print(f"Pattern match result: {matches}")