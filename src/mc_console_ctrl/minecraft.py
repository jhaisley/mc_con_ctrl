"""Minecraft Bedrock server communication module using tmux."""

import asyncio
import platform
from subprocess import PIPE, run, CalledProcessError
from rich.console import Console
import psutil
import pandas as pd
import sqlite3
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MinecraftServer:
    def __init__(self, tmux_session: str = "minecraft"):
        self._default_tmux_session = tmux_session
        self.console = Console()
        self._connected = False
        self._process_id: Optional[int] = None
        self._is_windows = platform.system() == "Windows"
        self.commands_df: Optional[pd.DataFrame] = None
        self.resources_df: Optional[pd.DataFrame] = None
        self.settings_df: Optional[pd.DataFrame] = None
        self.tmux_session: str = (
            tmux_session  # Will be updated from settings if available
        )

    async def _load_database(self) -> bool:
        """Load commands and resources from SQLite database."""
        try:
            conn = sqlite3.connect("data.sqlite")
            self.commands_df = pd.read_sql_query("SELECT * FROM commands", conn)
            self.resources_df = pd.read_sql_query("SELECT * FROM resources", conn)
            self.settings_df = pd.read_sql_query("SELECT * FROM settings", conn)
            self.named_pos_df = pd.read_sql_query("SELECT * FROM named_pos", conn)
            conn.close()

            # Update tmux_session from settings if available
            if self.settings_df is not None and not self.settings_df.empty:
                tmux_setting = self.settings_df[
                    self.settings_df["setting"] == "tmux_session"
                ]
                if not tmux_setting.empty:
                    self.tmux_session = tmux_setting.iloc[0]["value"]
                    logger.info(f"Updated tmux session to: {self.tmux_session}")
                else:
                    self.tmux_session = self._default_tmux_session

            cmd_count = len(self.commands_df) if self.commands_df is not None else 0
            res_count = len(self.resources_df) if self.resources_df is not None else 0
            settings_count = (
                len(self.settings_df) if self.settings_df is not None else 0
            )
            named_pos_count = (
                len(self.named_pos_df) if self.named_pos_df is not None else 0
            )

            logger.info(
                f"Database loaded with: {cmd_count} commands, {res_count} resources, {settings_count} settings, {named_pos_count} named positions"
            )
            return True

        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            self.console.print(f"[yellow]Database warning: {e}")
            return False

    async def startup(self) -> bool:
        """Initialize and report Minecraft server status."""
        try:
            # Load database
            await self._load_database()

            # Find Bedrock server process
            pid, cmd = await self._find_minecraft_process()
            if pid:
                self._process_id = pid
                logger.info(f"Found Minecraft Bedrock server process (PID: {pid})")
                self.console.print(f"[dim]Command: {cmd}")
            else:
                logger.warning("No Minecraft Bedrock server process found")

            # Check tmux session if on Linux
            if not self._is_windows:
                tmux_exists = await self._verify_tmux_session()
                if tmux_exists:
                    logger.info(f"Found tmux session: {self.tmux_session}")
                    self._connected = True
                else:
                    logger.warning(f"Tmux session '{self.tmux_session}' not found")
            else:
                logger.info("Skipping tmux check on Windows")
                # On Windows we'll still allow operation for development
                self._connected = True

            return True  # Return true even if services aren't running

        except Exception as e:
            logger.warning(f"Startup warning: {e}")
            return True  # Still return true as we want to continue anyway

    async def _find_minecraft_process(self) -> Tuple[Optional[int], Optional[str]]:
        """Find the Minecraft Bedrock server process ID and command."""
        bedrock_process_names = ["bedrock_server", "bedrock_server.exe"]

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] in bedrock_process_names:
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    return proc.info["pid"], cmdline
                # Also check for common Bedrock server wrapper scripts
                elif proc.info["name"] in ["python.exe", "python", "bash", "sh"]:
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if any(
                        name in cmdline.lower() for name in ["bedrock", "minecraft"]
                    ):
                        return proc.info["pid"], cmdline
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None, None

    async def _verify_tmux_session(self) -> bool:
        """Verify if the tmux session exists."""
        if self._is_windows:
            return True
        try:
            result = run(
                ["tmux", "has-session", "-t", self.tmux_session],
                stdout=PIPE,
                stderr=PIPE,
                text=True,
            )
            return result.returncode == 0
        except (CalledProcessError, FileNotFoundError):
            return False

    async def connect(self) -> bool:
        """Connect to the Minecraft server session."""
        # Always return true as we want to allow operation even without connection
        self._connected = True
        return True

    async def disconnect(self):
        """Disconnect from the Minecraft server session."""
        self._connected = False
        self.console.print("[yellow]Disconnected from Minecraft session")

    async def send_command(self, command: str) -> str:
        """Send a command to the Minecraft server."""
        if not self._connected:
            raise ConnectionError("Not connected to Minecraft server")

        try:
            if self._is_windows:
                escaped_command = command + "\n"
                self.console.print(
                    f"[dim]Would send command on Linux: {escaped_command}"
                )
                return "Command logged (Windows development mode)"

            # Send command via tmux
            escaped_command = command + "\n"
            run(
                ["tmux", "send-keys", "-t", self.tmux_session, escaped_command],
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                check=True,
            )
            await asyncio.sleep(0.1)
            return "Command sent successfully"

        except Exception as e:
            self.console.print(f"[red]Failed to send command: {e}")
            raise
