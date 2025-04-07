#!/usr/bin/env python3

import os
import sys
import json
import argparse
import yaml
from typing import Optional, Dict, Any
from datetime import datetime

from drive_manager import DriveManager
from utilities import DriveUtilities

class GDriveTool:
    """Command-line interface for Google Drive automation tool."""

    def __init__(self):
        """Initialize the tool with configuration and drive manager."""
        self.config_path = 'config.yaml'
        self.batch_commands_path = 'batch_commands.json'
        
        # Load configuration
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            sys.exit(f"Error loading configuration: {e}")

        # Initialize utilities and drive manager
        self.utils = DriveUtilities()
        self.logger = self.utils.setup_logging(self.config)
        self.drive_manager = DriveManager(self.config_path)

    def setup_argparse(self) -> argparse.ArgumentParser:
        """
        Set up command-line argument parsing.
        
        Returns:
            argparse.ArgumentParser: Configured argument parser
        """
        parser = argparse.ArgumentParser(
            description='Google Drive Automation Tool',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        subparsers = parser.add_subparsers(dest='command', help='Commands')

        # Copy command
        copy_parser = subparsers.add_parser('copy', help='Copy files/folders between drives')
        copy_parser.add_argument('--url', required=True, help='Shared Google Drive URL')
        copy_parser.add_argument('--destination', help='Destination folder ID (optional)')
        copy_parser.add_argument('--new-name', help='New name for the copied item (optional)')

        # Modify command
        modify_parser = subparsers.add_parser('modify', help='Batch modify files/folders')
        modify_parser.add_argument('--folder-id', required=True, help='ID of the folder to process')
        modify_parser.add_argument('--target', required=True, help='Target pattern (e.g., "*.docx")')
        modify_parser.add_argument('--prefix', help='Prefix to add to matching items')
        modify_parser.add_argument('--suffix', help='Suffix to add to matching items')

        # Delete command
        delete_parser = subparsers.add_parser('delete', help='Delete files/folders matching pattern')
        delete_parser.add_argument('--folder-id', required=True, help='ID of the folder to process')
        delete_parser.add_argument('--pattern', required=True, help='Pattern to match items for deletion')

        # Batch command
        batch_parser = subparsers.add_parser('batch', help='Execute commands from batch file')
        batch_parser.add_argument('--file', help=f'Path to batch commands file (default: {self.batch_commands_path})')

        # Copy to subfolders command
        copy_sub_parser = subparsers.add_parser('copy-to-subfolders', 
            help='Copy a file to all subfolders')
        copy_sub_parser.add_argument('--source-id', required=True, help='ID of the file to copy')
        copy_sub_parser.add_argument('--folder-id', required=True, 
            help='ID of the parent folder containing subfolders')

        return parser

    def execute_copy(self, args: argparse.Namespace) -> None:
        """
        Execute the copy command.
        
        Args:
            args: Parsed command-line arguments
        """
        try:
            self.logger.info(f"Copying from URL: {args.url}")
            file_id = self.drive_manager.parse_shared_link(args.url)
            new_id = self.drive_manager.copy_drive_item(
                file_id, 
                args.destination, 
                args.new_name
            )
            self.logger.info(f"Successfully copied. New item ID: {new_id}")
        except Exception as e:
            self.logger.error(f"Copy operation failed: {e}")
            sys.exit(1)

    def execute_modify(self, args: argparse.Namespace) -> None:
        """
        Execute the modify command.
        
        Args:
            args: Parsed command-line arguments
        """
        try:
            if not args.prefix and not args.suffix:
                raise ValueError("Either --prefix or --suffix must be specified")

            self.logger.info(
                f"Modifying items in folder {args.folder_id} "
                f"matching pattern: {args.target}"
            )
            
            renamed = self.drive_manager.batch_rename(
                args.folder_id,
                args.target,
                args.prefix,
                args.suffix
            )
            
            self.logger.info(f"Successfully renamed {len(renamed)} items")
            for old_name, new_name in renamed:
                self.logger.info(f"Renamed: {old_name} -> {new_name}")
        except Exception as e:
            self.logger.error(f"Modify operation failed: {e}")
            sys.exit(1)

    def execute_delete(self, args: argparse.Namespace) -> None:
        """
        Execute the delete command.
        
        Args:
            args: Parsed command-line arguments
        """
        try:
            self.logger.info(
                f"Deleting items in folder {args.folder_id} "
                f"matching pattern: {args.pattern}"
            )
            
            deleted = self.drive_manager.delete_items(
                args.folder_id,
                args.pattern
            )
            
            self.logger.info(f"Successfully deleted {len(deleted)} items")
            for item in deleted:
                self.logger.info(f"Deleted: {item}")
        except Exception as e:
            self.logger.error(f"Delete operation failed: {e}")
            sys.exit(1)

    def execute_copy_to_subfolders(self, args: argparse.Namespace) -> None:
        """
        Execute the copy-to-subfolders command.
        
        Args:
            args: Parsed command-line arguments
        """
        try:
            self.logger.info(
                f"Copying file {args.source_id} to all subfolders "
                f"in folder {args.folder_id}"
            )
            
            copied = self.drive_manager.copy_to_subfolders(
                args.source_id,
                args.folder_id
            )
            
            self.logger.info(f"Successfully copied to {len(copied)} subfolders")
            for copy_id in copied:
                self.logger.info(f"Created copy with ID: {copy_id}")
        except Exception as e:
            self.logger.error(f"Copy to subfolders operation failed: {e}")
            sys.exit(1)

    def execute_batch(self, args: argparse.Namespace) -> None:
        """
        Execute commands from a batch file.
        
        Args:
            args: Parsed command-line arguments
        """
        batch_file = args.file or self.batch_commands_path
        
        try:
            with open(batch_file, 'r') as f:
                commands = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading batch commands file: {e}")
            sys.exit(1)

        results = []
        for cmd in commands.get('commands', []):
            try:
                self.logger.info(f"Executing batch command: {cmd.get('action')}")
                result = self.drive_manager.execute_batch_command(cmd)
                results.append(result)
                
                if result['status'] == 'success':
                    self.logger.info(f"Command completed successfully: {cmd.get('description', '')}")
                else:
                    self.logger.error(f"Command failed: {result.get('error')}")
            except Exception as e:
                self.logger.error(f"Error executing batch command: {e}")
                results.append({
                    'action': cmd.get('action'),
                    'status': 'error',
                    'error': str(e)
                })

        # Save results to a report file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'batch_report_{timestamp}.json'
        try:
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Batch execution report saved to: {report_file}")
        except Exception as e:
            self.logger.error(f"Error saving batch report: {e}")

    def run(self) -> None:
        """Run the tool with the provided command-line arguments."""
        parser = self.setup_argparse()
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(1)

        command_map = {
            'copy': self.execute_copy,
            'modify': self.execute_modify,
            'delete': self.execute_delete,
            'batch': self.execute_batch,
            'copy-to-subfolders': self.execute_copy_to_subfolders
        }

        command_map[args.command](args)

def main():
    """Main entry point for the tool."""
    try:
        tool = GDriveTool()
        tool.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()