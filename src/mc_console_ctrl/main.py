"""Minecraft Console Control - Main entry point."""

import asyncio
from mc_console_ctrl.console import MinecraftConsole
from mc_console_ctrl.commands import CommandRegistry
from mc_console_ctrl.minecraft import MinecraftServer
import logging
from mc_console_ctrl.logger import setup_logging
import tracemalloc

tracemalloc.start()

logger = logging.getLogger(__name__)
setup_logging()
logger.info("MCC started", extra={"version": "1.0.0"})


async def init_application():
    """Initialize the application components."""
    # Initialize Minecraft server connection with default tmux session
    # (will be updated from database during startup)
    server = MinecraftServer()

    # Run startup initialization
    if not await server.startup():
        raise RuntimeError("Failed to initialize Minecraft server connection")

    # Set up command system with minecraft server instance
    command_registry = CommandRegistry(server)
    console = MinecraftConsole(server)

    # Register commands from registry to console
    for cmd_name, cmd_info in command_registry.commands.items():
        console.register_command(cmd_name, cmd_info["handler"], cmd_info["help"])

    return console


async def main():
    """Main entry point."""
    try:
        console = await init_application()
        await console.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0


def run_app():
    """Entry point for the application when called as a script."""
    return asyncio.run(main())


if __name__ == "__main__":
    exit(run_app())
else:
    # When imported as a module (e.g. via pip install)
    __all__ = ["main", "run_app"]
