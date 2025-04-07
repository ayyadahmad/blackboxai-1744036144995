#!/usr/bin/env python3

import os
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from tqdm import tqdm
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from auth import DriveAuth
from utilities import DriveUtilities

class DriveManager:
    """Manages Google Drive operations including file transfers and batch modifications."""

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize DriveManager with configuration.
        
        Args:
            config_path: Path to configuration file
        """
        self.auth = DriveAuth(config_path)
        self.service = self.auth.get_service()
        self.utils = DriveUtilities()
        self.logger = self.utils.setup_logging(self.auth.config)
        self.config = self.auth.config
        self.batch_size = self.config['batch_size']
        self.max_retries = self.config['max_retries']
        self.retry_delay = self.config['retry_delay']

    def _execute_with_retry(self, request: Any) -> Dict:
        """
        Execute a Google Drive API request with exponential backoff retry logic.
        
        Args:
            request: Google Drive API request object
            
        Returns:
            Dict: API response
            
        Raises:
            HttpError: If request fails after all retries
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                return request.execute()
            except HttpError as error:
                if error.resp.status in [429, 500, 503]:  # Rate limit or server errors
                    retry_count += 1
                    if retry_count == self.max_retries:
                        raise
                    wait_time = (2 ** retry_count) * self.retry_delay
                    self.logger.warning(f"Request failed, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise

    def parse_shared_link(self, url: str) -> str:
        """
        Parse a Google Drive shared URL and extract the file/folder ID.
        
        Args:
            url: Google Drive shared URL
            
        Returns:
            str: File/folder ID
            
        Raises:
            ValueError: If URL is invalid or ID cannot be extracted
        """
        file_id = self.utils.extract_file_id_from_url(url)
        if not file_id:
            raise ValueError("Invalid Google Drive URL or could not extract file ID")
        return file_id

    def get_file_metadata(self, file_id: str) -> Dict:
        """
        Get metadata for a file/folder.
        
        Args:
            file_id: Google Drive file/folder ID
            
        Returns:
            Dict: File metadata
        """
        try:
            return self._execute_with_retry(
                self.service.files().get(
                    fileId=file_id,
                    fields='id, name, mimeType, parents, size, modifiedTime'
                )
            )
        except HttpError as error:
            self.logger.error(f"Error getting file metadata: {error}")
            raise

    def copy_drive_item(self, item_id: str, destination_folder_id: Optional[str] = None,
                       new_name: Optional[str] = None) -> str:
        """
        Copy a file or folder to the specified destination.
        
        Args:
            item_id: ID of the item to copy
            destination_folder_id: ID of destination folder (None for root)
            new_name: New name for the copied item (None to keep original)
            
        Returns:
            str: ID of the copied item
        """
        try:
            metadata = self.get_file_metadata(item_id)
            is_folder = metadata['mimeType'] == 'application/vnd.google-apps.folder'

            if is_folder:
                return self._copy_folder(item_id, destination_folder_id, new_name)
            else:
                return self._copy_file(item_id, destination_folder_id, new_name)
        except Exception as e:
            self.logger.error(f"Error copying drive item: {e}")
            raise

    def _copy_file(self, file_id: str, parent_id: Optional[str] = None,
                   new_name: Optional[str] = None) -> str:
        """
        Copy a single file.
        
        Args:
            file_id: ID of the file to copy
            parent_id: ID of the parent folder
            new_name: New name for the copied file
            
        Returns:
            str: ID of the copied file
        """
        body = {'parents': [parent_id]} if parent_id else {}
        if new_name:
            body['name'] = new_name

        copied_file = self._execute_with_retry(
            self.service.files().copy(
                fileId=file_id,
                body=body
            )
        )
        return copied_file['id']

    def _copy_folder(self, folder_id: str, parent_id: Optional[str] = None,
                    new_name: Optional[str] = None) -> str:
        """
        Copy a folder and its contents recursively.
        
        Args:
            folder_id: ID of the folder to copy
            parent_id: ID of the parent folder
            new_name: New name for the copied folder
            
        Returns:
            str: ID of the copied folder
        """
        # Create the new folder
        folder_metadata = self.get_file_metadata(folder_id)
        new_folder = {
            'name': new_name or folder_metadata['name'],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            new_folder['parents'] = [parent_id]

        created_folder = self._execute_with_retry(
            self.service.files().create(body=new_folder)
        )
        new_folder_id = created_folder['id']

        # List and copy all items in the folder
        items = self.list_folder_contents(folder_id)
        for item in tqdm(items, desc=f"Copying folder: {folder_metadata['name']}"):
            self.copy_drive_item(item['id'], new_folder_id)

        return new_folder_id

    def list_folder_contents(self, folder_id: str) -> List[Dict]:
        """
        List all items in a folder.
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            List[Dict]: List of items in the folder
        """
        items = []
        page_token = None

        while True:
            results = self._execute_with_retry(
                self.service.files().list(
                    q=f"'{folder_id}' in parents",
                    pageSize=self.batch_size,
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType)"
                )
            )
            items.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            if not page_token:
                break

        return items

    def batch_rename(self, folder_id: str, pattern: str, prefix: Optional[str] = None,
                    suffix: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Rename files/folders matching a pattern in the specified folder.
        
        Args:
            folder_id: ID of the folder to process
            pattern: Pattern to match files/folders
            prefix: Prefix to add
            suffix: Suffix to add (before extension)
            
        Returns:
            List[Tuple[str, str]]: List of (old_name, new_name) pairs
        """
        if not prefix and not suffix:
            raise ValueError("Either prefix or suffix must be specified")

        renamed_items = []
        items = self.list_folder_contents(folder_id)

        for item in tqdm(items, desc="Renaming items"):
            if self.utils.pattern_matches(item['name'], pattern):
                name, ext = os.path.splitext(item['name'])
                new_name = f"{prefix or ''}{name}{suffix or ''}{ext}"
                
                try:
                    self._execute_with_retry(
                        self.service.files().update(
                            fileId=item['id'],
                            body={'name': new_name}
                        )
                    )
                    renamed_items.append((item['name'], new_name))
                    self.logger.info(f"Renamed: {item['name']} -> {new_name}")
                except HttpError as e:
                    self.logger.error(f"Error renaming {item['name']}: {e}")

        return renamed_items

    def delete_items(self, folder_id: str, pattern: str) -> List[str]:
        """
        Delete items matching a pattern in the specified folder.
        
        Args:
            folder_id: ID of the folder to process
            pattern: Pattern to match items for deletion
            
        Returns:
            List[str]: Names of deleted items
        """
        deleted_items = []
        items = self.list_folder_contents(folder_id)

        for item in tqdm(items, desc="Deleting items"):
            if self.utils.pattern_matches(item['name'], pattern):
                try:
                    self._execute_with_retry(
                        self.service.files().delete(fileId=item['id'])
                    )
                    deleted_items.append(item['name'])
                    self.logger.info(f"Deleted: {item['name']}")
                except HttpError as e:
                    self.logger.error(f"Error deleting {item['name']}: {e}")

        return deleted_items

    def copy_to_subfolders(self, source_file_id: str, folder_id: str) -> List[str]:
        """
        Copy a file to all subfolders in the specified folder.
        
        Args:
            source_file_id: ID of the file to copy
            folder_id: ID of the parent folder
            
        Returns:
            List[str]: IDs of created copies
        """
        copied_files = []
        subfolders = self._execute_with_retry(
            self.service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            )
        ).get('files', [])

        source_metadata = self.get_file_metadata(source_file_id)
        for folder in tqdm(subfolders, desc=f"Copying {source_metadata['name']} to subfolders"):
            try:
                copied_id = self.copy_drive_item(source_file_id, folder['id'])
                copied_files.append(copied_id)
                self.logger.info(f"Copied to folder {folder['name']}")
            except Exception as e:
                self.logger.error(f"Error copying to folder {folder['name']}: {e}")

        return copied_files

    def execute_batch_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a batch command from batch_commands.json.
        
        Args:
            command: Command dictionary with action and parameters
            
        Returns:
            Dict[str, Any]: Result of the command execution
        """
        action = command.get('action')
        if not action:
            raise ValueError("Command must specify an 'action'")

        result = {
            'action': action,
            'status': 'success',
            'details': {}
        }

        try:
            if action == 'copy':
                source_id = self.parse_shared_link(command['source'])
                dest_id = command.get('destination')
                new_id = self.copy_drive_item(source_id, dest_id)
                result['details']['new_id'] = new_id

            elif action == 'rename':
                folder_id = command['folder_id']
                pattern = command['target']
                prefix = command.get('prefix')
                suffix = command.get('suffix')
                renamed = self.batch_rename(folder_id, pattern, prefix, suffix)
                result['details']['renamed_items'] = renamed

            elif action == 'delete':
                folder_id = command['folder_id']
                pattern = command['pattern']
                deleted = self.delete_items(folder_id, pattern)
                result['details']['deleted_items'] = deleted

            elif action == 'copy_to_subfolders':
                source_id = command['source_id']
                folder_id = command['folder_id']
                copied = self.copy_to_subfolders(source_id, folder_id)
                result['details']['copied_files'] = copied

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self.logger.error(f"Error executing batch command: {e}")

        return result

if __name__ == "__main__":
    # Example usage
    manager = DriveManager()
    
    # Test copying a shared file
    try:
        shared_url = "https://drive.google.com/file/d/your_file_id/view"
        file_id = manager.parse_shared_link(shared_url)
        new_id = manager.copy_drive_item(file_id)
        print(f"Successfully copied file. New ID: {new_id}")
    except Exception as e:
        print(f"Error: {e}")