# Workflow Manager

A flexible workflow automation system that allows you to create and execute workflows using various components like formatters, webhooks, and Slack integration.

## Features

- **Component-based Architecture**: Modular components for different functionalities
- **DAG Execution**: Automatic dependency resolution and execution ordering
- **Context Management**: Thread-safe data sharing between workflow components
- **Third-party Integrations**: Support for Slack, webhooks, and more
- **Interactive CLI**: User-friendly command-line interface
- **Event-Driven Architecture**: Persistent event listeners for real-time triggers
- **Multi-Account Support**: Multiple named configurations for third-party services

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
python -m src

# Method 3: Direct execution
cd src
python __main__.py

# Command-line usage
python -m src create                    # Create new workflow
python -m src execute                   # Choose workflow to execute
python -m src execute my_workflow       # Execute specific workflow
python -m src list                      # List all workflows
python -m src --help                    # Show help
```

### Available Components

1. **Formatter**: Text and number formatting operations
   - Text operations: URL encoding, string replacement, prefix stripping
   - Number operations: Currency formatting, random number generation

2. **Webhook**: HTTP request operations
   - GET requests with custom headers
   - POST requests with JSON or text data

3. **Slack**: Real-time Slack integration
   - Send messages to channels
   - Receive message events with persistent listeners
   - Socket Mode for real-time communication

### Creating Workflows

1. Select "Create new workflow" from the main menu
2. Enter a unique workflow name (or choose to overwrite existing)
3. **Add Event Trigger** (required first component):
   - Choose from available event triggers
   - Configure event settings and filters
4. **Add Action Components** (optional):
   - Choose component type
   - Configure component settings
   - Set up third-party integrations if needed
   - Define custom output key aliases for data sharing
5. The system automatically handles dependencies between components

### Executing Workflows

1. Select "Execute existing workflow" from the main menu
2. Choose from your available workflows
3. Review workflow details
4. Confirm execution
5. View results and context data

## Slack Integration

### Setup Requirements

To use Slack integration, you need to create a Slack app with the following:

1. **Create a Slack App**:
   - Go to [https://api.slack.com/apps](https://api.slack.com/apps)
   - Create a new app "From scratch"
   - Select your workspace

2. **Configure Bot Scopes** (OAuth & Permissions):
   - `chat:write` - Send messages
   - `channels:read` - Read public channel info
   - `groups:read` - Read private channel info (optional)

3. **Install App to Workspace**:
   - Install the app to your workspace
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

4. **Enable Socket Mode**:
   - Enable Socket Mode in app settings
   - Generate an App-Level Token with `connections:write` scope
   - Copy the "App-Level Token" (starts with `xapp-`)

5. **Subscribe to Events**:
   - Enable Event Subscriptions
   - Subscribe to bot events: `message.channels`, `message.groups`, `message.im`, `message.mpim`

6. **Get Signing Secret**:
   - Copy the Signing Secret from Basic Information

### Slack Component Configuration

When setting up the Slack component, you'll need:
- **Bot Token** (`xoxb-...`): For API calls and authentication
- **App Token** (`xapp-...`): For Socket Mode real-time connection
- **Signing Secret**: For request verification

### Slack Actions and Events

#### Send Message Action
```
Component: Slack
Action: Send Slack Message
Configuration:
- Message: "Hello from Workflow Manager!" (supports context placeholders)
- Channel: Selected from available channels or context placeholder
```

#### Receive Message Event (Persistent Listener)
```
Component: Slack
Event: Receive Slack Message
Configuration:
- Channel: Selected from available channels or context placeholder
- Keyword: "deploy" (optional - triggers on all messages if not specified)
- Timeout: -1 (default - persistent listening, or specify seconds for timeout)
```

### Event-Driven Architecture

The Slack Receive Message Event is designed as a **persistent listener**:

- **Default Behavior**: Runs continuously (`timeout = -1`)
- **Background Operation**: Runs in daemon thread, non-blocking
- **Real-time**: Uses WebSocket connection for instant message reception
- **Filtering**: Supports channel and keyword filtering
- **Persistent**: Continues listening after triggering workflow

### Example Workflows

#### Echo Bot (Persistent)
```
1. Event Trigger: Slack Receive Message
   - Channel: "#bot-test"
   - Timeout: -1 (persistent)

2. Action: Slack Send Message
   - Channel: "#bot-test"
   - Message: "Echo: {{message_text}}"
```

#### Deployment Trigger
```
1. Event Trigger: Slack Receive Message
   - Channel: "#deployments"
   - Keyword: "deploy"
   - Timeout: -1 (persistent)

2. Action: Webhook POST
   - URL: "https://api.example.com/deploy"
   - Data: {"user": "{{user_id}}", "message": "{{message_text}}"}

3. Action: Slack Send Message
   - Channel: "#deployments"
   - Message: "Deployment started by <@{{user_id}}>"
```

## Project Structure

```
workflow-manager/
├── configs/                    # Configuration files
│   ├── action_store.json      # Action definitions
│   ├── components_store.json  # Component definitions
│   └── event_store.json       # Event definitions
├── src/                        # Main application package
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
- `setups/`: Third-party component configurations (supports multiple named setups)

## Configuration

Component and action definitions are stored in JSON files in the `configs/` directory. These files define:
- Available components and their setup requirements
- Available actions and their configuration parameters
- Available events and their output schemas

## Advanced Features

### Multiple Named Setups
- Create multiple configurations for the same third-party service
- Example: Different Slack workspaces or accounts
- Choose or create setups during workflow creation

### Custom Output Aliases
- Rename output variables from actions/events
- Avoid naming conflicts between components
- Improve workflow readability

### Workflow Overwriting
- Choose to overwrite existing workflows
- No need to create new names for iterations

### Context Placeholders
- Use `{{variable_name}}` in configurations
- Reference outputs from previous components
- Dynamic content based on workflow execution

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
- Persistent listener cleanup and resource management

## Testing

Test the Slack integration:
```bash
python test_slack_persistent.py
```

This will verify:
- Slack SDK availability
- Component creation
- Event configuration
- Error handling
- Timeout configurations

## Troubleshooting

### Common Issues

1. **Slack SDK not available**:
   - Ensure dependencies are installed: `pip install -r requirements.txt`

2. **Slack authentication failed**:
   - Verify Bot Token starts with `xoxb-`
   - Ensure app is installed to workspace

3. **Socket Mode connection issues**:
   - Verify App Token starts with `xapp-`
   - Ensure Socket Mode is enabled in Slack app

4. **Persistent listener not working**:
   - Check timeout is set to -1 (default)
   - Verify bot is added to target channel
   - Check application logs for connection errors

### Security Notes

- Keep tokens secure and never commit to version control
- Use environment variables or secure configuration management
- Regularly rotate tokens
- Only grant necessary scopes to your bot
- Monitor bot activity in Slack audit logs
