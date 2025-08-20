# Workflow Manager

A flexible workflow automation system that allows you to create and execute workflows using various components like formatters, webhooks, and Slack integration.

## Features

- **Component-based Architecture**: Modular components for different functionalities
- **DAG Execution**: Automatic dependency resolution and execution ordering
- **Context Management**: Thread-safe data sharing between workflow components
- **Third-party Integrations**: Support for Slack, webhooks, and more
- **Interactive CLI**: User-friendly command-line interface

## Installation

1. Clone or download the project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
# Method 1: Using the run script
python run.py

# Method 2: Using the module
python -m workflow_manager

# Method 3: Direct execution
cd workflow_manager
python __main__.py
```

### Available Components

1. **Formatter**: Text and number formatting operations
   - Text operations: URL encoding, string replacement, prefix stripping
   - Number operations: Currency formatting, random number generation

2. **Webhook**: HTTP request operations
   - GET requests with custom headers
   - POST requests with JSON or text data

3. **Slack**: Slack integration (requires setup)
   - Send messages to channels
   - Receive message events (mock implementation)

### Creating Workflows

1. Select "Create new workflow" from the main menu
2. Enter a unique workflow name
3. Add components one by one:
   - Choose component type
   - Configure component settings
   - Set up third-party integrations if needed
   - Define output keys for data sharing
4. The system automatically handles dependencies between components

### Executing Workflows

1. Select "Execute existing workflow" from the main menu
2. Choose from your available workflows
3. Review workflow details
4. Confirm execution
5. View results and context data

## Project Structure

```
workflow-manager/
├── configs/                    # Configuration files
│   ├── action_store.json      # Action definitions
│   ├── components_store.json  # Component definitions
│   └── event_store.json       # Event definitions
├── workflow_manager/           # Main application package
│   ├── cli/                   # Command-line interface
│   ├── components/            # Component implementations
│   ├── core/                  # Core logic and abstractions
│   └── __main__.py           # Application entry point
├── data/                      # User data (created at runtime)
├── logs/                      # Application logs (created at runtime)
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## Data Storage

The application stores data in the `data/` directory:
- `users/`: User profiles
- `workflows/`: Workflow definitions
- `setups/`: Third-party component configurations

## Configuration

Component and action definitions are stored in JSON files in the `configs/` directory. These files define:
- Available components and their setup requirements
- Available actions and their configuration parameters
- Available events and their output schemas

## Examples

### Simple Text Formatting Workflow
1. Add a Formatter component with text operation
2. Configure it to URL-encode user input
3. Execute to see the encoded result

### Webhook Integration Workflow
1. Add a Webhook component with GET operation
2. Configure it to fetch data from an API
3. Add a Formatter component to process the response
4. Use context placeholders to pass data between components

### Slack Notification Workflow
1. Set up Slack component with bot token
2. Add a Slack send message action
3. Configure message content (can use context data)
4. Execute to send message to Slack

## Development

The application follows a modular architecture:
- **Core**: Abstract base classes and core functionality
- **Components**: Concrete implementations of workflow components
- **CLI**: User interface and interaction logic
- **Factories**: Dynamic object creation and configuration loading

## Logging

Application logs are stored in the `logs/` directory. The logging level can be adjusted in the main application file.

## Error Handling

The application includes comprehensive error handling:
- Validation of user input
- Graceful handling of network errors
- Detailed error messages and logging
- Safe execution with rollback capabilities
