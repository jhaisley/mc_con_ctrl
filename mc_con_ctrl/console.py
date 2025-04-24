"""Interactive console implementation for Minecraft Command & Control."""

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from rich.console import Console
from rich.panel import Panel
from typing import Iterable
from .minecraft import MinecraftServer
from .config import Config


class MinecraftCommandCompleter(Completer):
    def __init__(self, minecraft_server: MinecraftServer):
        self.minecraft_server = minecraft_server
        self.config = Config()

    def get_completions(self, document, complete_event) -> Iterable[Completion]:
        text = document.text
        words = text.split()

        if not words:
            return

        word_before_cursor = document.get_word_before_cursor()
        current_pos = len(words) if document.text.endswith(" ") else len(words) - 1

        # For base commands
        if len(words) == 1:
            commands = {
                "help": "Display help information",
                "exit": "Exit the application",
                "sc": "Send command to Minecraft server",
                "give": "Give items to a player",
                "raw": "Send raw input directly to the server",
                "enchant": "Enchant a player's held item",
                "effect": "Apply effect to a player",
                "effectclear": "Clear all effects from a player",
            }
            for cmd, desc in commands.items():
                if cmd.startswith(word_before_cursor):
                    yield Completion(
                        cmd, start_position=-len(word_before_cursor), display_meta=desc
                    )

        # For give command completions
        elif words[0] == "give":
            # First parameter: player name
            if current_pos == 1:
                settings = self.config.load()
                default_player = settings["server"].get("default_player", "")
                if default_player.lower().startswith(word_before_cursor.lower()):
                    yield Completion(
                        default_player,
                        start_position=-len(word_before_cursor),
                        display_meta="Default player",
                    )

            # Second parameter: block name with resource location
            elif current_pos == 2:
                if self.minecraft_server.resources_df is not None:
                    blocks_df = self.minecraft_server.resources_df[
                        (self.minecraft_server.resources_df["resource_type"] == "block")
                        & (
                            self.minecraft_server.resources_df[
                                "Resource location"
                            ].notna()
                        )
                        & (self.minecraft_server.resources_df["Name"].notna())
                    ][["Resource location", "Name"]]

                    for _, row in blocks_df.iterrows():
                        block_id = row["Resource location"]
                        block_name = row["Name"]
                        if block_id.lower().startswith(word_before_cursor.lower()):
                            yield Completion(
                                block_id,
                                start_position=-len(word_before_cursor),
                                display_meta=f"Block: {block_name}",
                            )

        # For enchant command completions
        elif words[0] == "enchant":
            # First parameter: player name
            if current_pos == 1:
                settings = self.config.load()
                default_player = settings["server"].get("default_player", "")
                if default_player.lower().startswith(word_before_cursor.lower()):
                    yield Completion(
                        default_player,
                        start_position=-len(word_before_cursor),
                        display_meta="Default player",
                    )

            # Second parameter: enchantment name with resource location
            elif current_pos == 2:
                if self.minecraft_server.resources_df is not None:
                    enchants_df = self.minecraft_server.resources_df[
                        (
                            self.minecraft_server.resources_df["resource_type"]
                            == "enchantment"
                        )
                        & (
                            self.minecraft_server.resources_df[
                                "Resource location"
                            ].notna()
                        )
                        & (self.minecraft_server.resources_df["Name"].notna())
                    ][["Resource location", "Name", "enchantment_max_level"]]

                    for _, row in enchants_df.iterrows():
                        enchant_id = row["Resource location"]
                        enchant_name = row["Name"]
                        max_level = int(float(row["enchantment_max_level"] or 1))

                        if enchant_id.lower().startswith(word_before_cursor.lower()):
                            yield Completion(
                                enchant_id,
                                start_position=-len(word_before_cursor),
                                display_meta=f"Enchantment: {enchant_name} (Max: {max_level})",
                            )

            # Third parameter: level suggestions based on enchantment
            elif current_pos == 3 and len(words) > 2:
                enchantment = words[2]
                if self.minecraft_server.resources_df is not None:
                    enchant_data = self.minecraft_server.resources_df[
                        (
                            self.minecraft_server.resources_df["resource_type"]
                            == "enchantment"
                        )
                        & (
                            self.minecraft_server.resources_df[
                                "Resource location"
                            ].str.lower()
                            == enchantment.lower()
                        )
                    ]

                    if not enchant_data.empty:
                        max_level = int(
                            float(enchant_data.iloc[0]["enchantment_max_level"] or 1)
                        )
                        for level in range(1, max_level + 1):
                            if str(level).startswith(word_before_cursor):
                                yield Completion(
                                    str(level),
                                    start_position=-len(word_before_cursor),
                                    display_meta=f"Level {level}/{max_level}",
                                )

        # For effect command completions
        elif words[0] == "effect":
            # First parameter: player name
            if current_pos == 1:
                settings = self.config.load()
                default_player = settings["server"].get("default_player", "")
                if default_player.lower().startswith(word_before_cursor.lower()):
                    yield Completion(
                        default_player,
                        start_position=-len(word_before_cursor),
                        display_meta="Default player",
                    )

            # Second parameter: effect name
            elif current_pos == 2:
                if self.minecraft_server.resources_df is not None:
                    effects_df = self.minecraft_server.resources_df[
                        (
                            self.minecraft_server.resources_df["resource_type"]
                            == "effect"
                        )
                        & (
                            self.minecraft_server.resources_df[
                                "Resource location"
                            ].notna()
                        )
                        & (self.minecraft_server.resources_df["Name"].notna())
                    ][["Resource location", "Name"]]

                    for _, row in effects_df.iterrows():
                        effect_id = row["Resource location"]
                        effect_name = row["Name"]
                        if effect_id.lower().startswith(word_before_cursor.lower()):
                            yield Completion(
                                effect_id,
                                start_position=-len(word_before_cursor),
                                display_meta=f"Effect: {effect_name}",
                            )

            # Third parameter: duration in seconds
            elif current_pos == 3:
                durations = [
                    ("30", "Default duration"),
                    ("60", "1 minute"),
                    ("300", "5 minutes"),
                    ("600", "10 minutes"),
                    ("1200", "20 minutes"),
                    ("3600", "1 hour"),
                ]
                for duration, desc in durations:
                    if duration.startswith(word_before_cursor):
                        yield Completion(
                            duration,
                            start_position=-len(word_before_cursor),
                            display_meta=desc,
                        )

            # Fourth parameter: amplifier
            elif current_pos == 4:
                amplifiers = [
                    ("0", "Level 1 (Normal)"),
                    ("1", "Level 2"),
                    ("2", "Level 3"),
                    ("4", "Level 5"),
                    ("9", "Level 10"),
                ]
                for amp, desc in amplifiers:
                    if amp.startswith(word_before_cursor):
                        yield Completion(
                            amp,
                            start_position=-len(word_before_cursor),
                            display_meta=desc,
                        )

        # For effectclear command completions
        elif words[0] == "effectclear":
            # First parameter: player name
            if current_pos == 1:
                settings = self.config.load()
                default_player = settings["server"].get("default_player", "")
                if default_player.lower().startswith(word_before_cursor.lower()):
                    yield Completion(
                        default_player,
                        start_position=-len(word_before_cursor),
                        display_meta="Default player",
                    )

        # For sc command completions
        elif words[0] == "sc":
            if self.minecraft_server.commands_df is not None:
                commands_data = self.minecraft_server.commands_df[
                    ["command", "description"]
                ].values
                for cmd, desc in commands_data:
                    if cmd and cmd.startswith(
                        word_before_cursor
                    ):  # Check for null values
                        yield Completion(
                            cmd,
                            start_position=-len(word_before_cursor),
                            display_meta=desc if desc else "Minecraft command",
                        )


class MinecraftConsole:
    def __init__(self, minecraft_server: MinecraftServer):
        self.console = Console()
        self.minecraft_server = minecraft_server
        self.session = PromptSession()
        self.commands = {}

    def register_command(self, name: str, func, help_text: str):
        """Register a new command."""
        self.commands[name] = {"func": func, "help": help_text}

    def get_completer(self):
        """Create command completer for both built-in and Minecraft commands."""
        return MinecraftCommandCompleter(self.minecraft_server)

    async def start(self):
        """Start the interactive console."""
        self.console.print(Panel("Minecraft Command & Control", style="bold green"))

        while True:
            try:
                command = await self.session.prompt_async(
                    "mc> ", completer=self.get_completer()
                )

                if not command:
                    continue

                cmd_name = command.split()[0]
                if cmd_name in self.commands:
                    await self.commands[cmd_name]["func"](command)
                else:
                    self.console.print(f"Unknown command: {cmd_name}", style="red")
            except (EOFError, KeyboardInterrupt):
                self.console.print("\nExiting console.", style="yellow")
                break
            except Exception as e:
                self.console.print(f"An error occurred: {e}", style="bold red")
