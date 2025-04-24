"""Minecraft Command & Control - Main entry point."""

import asyncio
from mc_con_ctrl.config import Config
from mc_con_ctrl.console import MinecraftConsole
from mc_con_ctrl.commands import CommandRegistry
from mc_con_ctrl.minecraft import MinecraftServer


async def init_application():
    """Initialize the application components."""
    # Load configuration
    config = Config()
    settings = config.load()

    # Initialize Minecraft server connection
    server = MinecraftServer(tmux_session=settings["server"]["tmux_session"])

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


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
