# Google Drive Automation Tool

A Python-based command-line tool for automating Google Drive operations, including cross-drive file transfers, batch modifications, and custom commands.

## Features

- **Drive-to-Drive Operations**
  - Copy files/folders between Google Drive accounts
  - Preserve folder hierarchy during copying
  - Handle shared Drive links

- **Batch Modifications**
  - Add prefixes/suffixes to files/folders recursively
  - Copy files to all subfolders
  - Delete files matching specific patterns

- **Automation & Customization**
  - Execute commands from batch files
  - Schedule recurring tasks
  - Configurable settings via YAML

- **Intelligent Features**
  - Duplicate detection
  - Rate limit handling with exponential backoff
  - Progress tracking for large operations

- **Security & Logging**
  - Secure credential storage using keyring
  - Comprehensive logging
  - Detailed operation reports

## Prerequisites

- Python 3.7 or higher
- Google Cloud Project with Drive API enabled
- Required Python packages:
  ```
  google-api-python-client
  oauth2client
  PyYAML
  tqdm
  keyring
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/gdrive-tool.git
   cd gdrive-tool
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the Google Drive API
   - Create OAuth 2.0 credentials
   - Download the credentials and save as `credentials.json` in the project directory

## Configuration

### config.yaml

The tool's behavior can be customized through `config.yaml`:

```yaml
google_api:
  credentials_file: "credentials.json"
  scopes:
    - "https://www.googleapis.com/auth/drive"

default_paths:
  backup_folder: "Backups"
  temp_folder: "temp"

batch_size: 50
max_retries: 5
retry_delay: 1

logging:
  level: "INFO"
  file: "audit.log"
  format: "%(asctime)s - %(levelname)s - %(message)s"

scheduler:
  enabled: true
  task_interval: "24h"
```

### batch_commands.json

Define batch operations in `batch_commands.json`:

```json
{
  "commands": [
    {
      "action": "copy",
      "target": "README.txt",
      "destination": "all_subfolders",
      "description": "Copy README.txt to all subfolders"
    },
    {
      "action": "rename",
      "target": "*.docx",
      "suffix": "_2024",
      "description": "Add '_2024' suffix to all .docx files"
    }
  ]
}
```

## Usage

### Basic Commands

1. **Copy a shared Drive file/folder:**
   ```bash
   python gdrive_tool.py copy --url "https://drive.google.com/drive/folders/your-folder-id"
   ```

2. **Rename files with a pattern:**
   ```bash
   python gdrive_tool.py modify --folder-id "folder-id" --target "*.docx" --suffix "_2024"
   ```

3. **Delete files matching a pattern:**
   ```bash
   python gdrive_tool.py delete --folder-id "folder-id" --pattern "draft_*"
   ```

4. **Copy file to all subfolders:**
   ```bash
   python gdrive_tool.py copy-to-subfolders --source-id "file-id" --folder-id "folder-id"
   ```

5. **Execute batch commands:**
   ```bash
   python gdrive_tool.py batch --file "batch_commands.json"
   ```

### Command Options

- **copy:**
  - `--url`: Shared Google Drive URL (required)
  - `--destination`: Destination folder ID (optional)
  - `--new-name`: New name for the copied item (optional)

- **modify:**
  - `--folder-id`: ID of the folder to process (required)
  - `--target`: Target pattern (e.g., "*.docx") (required)
  - `--prefix`: Prefix to add to matching items
  - `--suffix`: Suffix to add to matching items

- **delete:**
  - `--folder-id`: ID of the folder to process (required)
  - `--pattern`: Pattern to match items for deletion (required)

- **copy-to-subfolders:**
  - `--source-id`: ID of the file to copy (required)
  - `--folder-id`: ID of the parent folder (required)

## Error Handling

The tool includes comprehensive error handling:
- Rate limit handling with exponential backoff
- Network error recovery
- Permission error detection
- Detailed error logging in audit.log

## Logging

All operations are logged to `audit.log` with timestamps and details:
- Operation type and parameters
- Success/failure status
- Error messages and stack traces
- Progress updates

## Security Considerations

1. **Credential Storage:**
   - OAuth2 credentials are securely stored using keyring
   - Access tokens are automatically refreshed
   - No sensitive data is logged

2. **Data Privacy:**
   - Only requested permissions are used
   - No unnecessary data access
   - Clear audit trail of all operations

## Best Practices

1. **Before Using:**
   - Review and update config.yaml
   - Test operations on non-critical data first
   - Ensure sufficient drive space

2. **During Operations:**
   - Monitor audit.log for issues
   - Don't interrupt long-running operations
   - Keep credentials.json secure

3. **Maintenance:**
   - Regularly update dependencies
   - Review and clean up logs
   - Check for tool updates

## Troubleshooting

Common issues and solutions:

1. **Authentication Errors:**
   - Verify credentials.json is present and valid
   - Check API is enabled in Google Cloud Console
   - Ensure correct scopes are configured

2. **Rate Limit Errors:**
   - Adjust batch_size in config.yaml
   - Increase retry_delay for heavy operations
   - Split large operations into smaller batches

3. **Permission Errors:**
   - Verify file/folder access permissions
   - Check sharing settings on source files
   - Ensure sufficient drive quota

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Drive API Team
- Contributors to dependent packages
- Open source community

## Support

For issues and feature requests:
- Submit an issue on GitHub
- Check existing issues for solutions
- Include relevant logs and configuration

---

Remember to always backup important data before running batch operations and test new automation scripts on non-critical files first.