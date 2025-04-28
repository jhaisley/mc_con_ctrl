# Minecraft Console Control (MCC)

A powerful command-line tool for managing Minecraft servers with ease. MCC provides a modern, intuitive interface for server administration tasks.

## Features

- Interactive console control for Minecraft servers
- Real-time server monitoring and management
- Rich command-line interface with modern styling
- Automated server management capabilities
- Python 3.13+ with async support

## Installation

Ensure you have Python 3.13 or higher installed, then install using UV:

```shell
uv venv
uv pip install -e .
```

## Getting Started

### Prerequesite Step
0. Have minecraft bedrock server running under tmux, by default we look for a named session called minecraft, but you can change this in data.sqlite.

### Quick Start
1. Clone this repository
2. Install dependencies
3. Run the application:

```shell
python -m mc_console_ctrl
```

## Requirements

- Python 3.13 or higher
- Dependencies:
  - pandas>=2.2.3
  - ruff>=0.11.6
  - prompt-toolkit>=3.0.43
  - rich>=13.7.1
  - typer>=0.9.0
  - psutil>=7.0.0

## Development

To set up a development environment:

1. Clone the repository
2. Create a virtual environment:
```shell
uv venv
```
3. Install development dependencies:
```shell
uv pip install -e ".[dev]"
```

## License

[MIT License](./LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


