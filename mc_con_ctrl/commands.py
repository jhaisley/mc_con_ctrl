"""Command system implementation for Minecraft Command & Control."""

from typing import Dict, Any, Callable, Awaitable
from rich.console import Console
from .minecraft import MinecraftServer
from .config import Config


class CommandRegistry:
    def __init__(self, minecraft_server: MinecraftServer):
        self.console = Console()
        self.commands: Dict[str, dict[str, Any]] = {}
        self.minecraft_server = minecraft_server
        self.config = Config()
        self._register_builtin_commands()

    def _register_builtin_commands(self):
        """Register built-in commands."""
        self.register_command(
            "help",
            self.help_command,
            "Display help information about available commands",
        )
        self.register_command("exit", self.exit_command, "Exit the application")
        self.register_command(
            "sc", self.send_command, "Send a command to the Minecraft server"
        )
        self.register_command(
            "raw", self.raw_command, "Send raw input directly to the server"
        )
        self.register_command(
            "give",
            self.give_command,
            "Give items to a player (give playername block qty)",
        )
        self.register_command(
            "enchant",
            self.enchant_command,
            "Enchant a player's held item (enchant playername enchantment level)",
        )
        self.register_command(
            "effect",
            self.effect_command,
            "Apply effect to a player (effect player effect [seconds] [amplifier] [hideParticles])",
        )
        self.register_command(
            "effectclear",
            self.effectclear_command,
            "Clear all effects from a player (effectclear playername)",
        )

    def register_command(
        self, name: str, handler: Callable[[str], Awaitable[None]], help_text: str
    ):
        """Register a new command."""
        self.commands[name] = {"handler": handler, "help": help_text}

    async def help_command(self, _: str) -> None:
        """Display help information."""
        self.console.print("\nAvailable Commands:", style="bold green")
        for cmd_name, cmd_info in sorted(self.commands.items()):
            self.console.print(f"  {cmd_name}: {cmd_info['help']}")
        self.console.print()

    async def exit_command(self, _: str) -> None:
        """Exit the application."""
        self.console.print("\nGoodbye!", style="bold blue")
        raise SystemExit(0)

    async def send_command(self, cmd_line: str) -> None:
        """Send a command to the Minecraft server."""
        # Remove 'sc' from the beginning of the command
        _, *args = cmd_line.split()
        if not args:
            self.console.print("[yellow]Usage: sc <command>")
            return

        mc_command = " ".join(args)
        try:
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")
        except Exception as e:
            self.console.print(f"[red]Error sending command: {e}")

    async def raw_command(self, cmd_line: str) -> None:
        """Send raw input directly to the server."""
        # Remove 'raw' from the beginning of the command
        _, *args = cmd_line.split(maxsplit=1)
        if not args:
            self.console.print("[yellow]Usage: raw <text>")
            return

        raw_input = args[0]  # Take the rest of the line as is
        try:
            result = await self.minecraft_server.send_command(raw_input)
            self.console.print(f"[green]{result}")
        except Exception as e:
            self.console.print(f"[red]Error sending command: {e}")

    async def give_command(self, cmd_line: str) -> None:
        """Give items to a player."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print("[yellow]Usage: give <playername> <block> [quantity]")
            return

        _, player, block, *rest = parts
        quantity = rest[0] if rest else "1"

        try:
            # Verify block exists in resources
            if self.minecraft_server.resources_df is not None:
                # Case-insensitive resource location matching
                block_data = self.minecraft_server.resources_df[
                    (
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "block"
                    )
                    & (
                        self.minecraft_server.resources_df[
                            "Resource location"
                        ].str.lower()
                        == block.lower()
                    )
                ]

                if block_data.empty:
                    self.console.print(f"[red]Invalid block: {block}")
                    # Show similar block suggestions with resource locations
                    blocks_df = self.minecraft_server.resources_df[
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "block"
                    ][["Resource location", "Name"]]

                    suggestions = []
                    for _, row in blocks_df.iterrows():
                        if block.lower() in row["Resource location"].lower():
                            suggestions.append((row["Resource location"], row["Name"]))
                            if len(suggestions) >= 5:
                                break

                    if suggestions:
                        self.console.print("[yellow]Did you mean one of these?")
                        for resource_loc, name in suggestions:
                            self.console.print(f"  - {resource_loc} ({name})")
                    return

                # Use the correct case from the database
                block = block_data.iloc[0]["Resource location"]

            # Construct and send the give command
            mc_command = f"give {player} {block} {quantity}"
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error giving items: {e}")

    async def enchant_command(self, cmd_line: str) -> None:
        """Enchant a player's held item."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print(
                "[yellow]Usage: enchant <playername> <enchantment> [level]"
            )
            return

        _, player, enchantment, *rest = parts
        level = rest[0] if rest else "1"

        try:
            # Verify enchantment exists in resources
            if self.minecraft_server.resources_df is not None:
                # Case-insensitive resource location matching
                enchant_data = self.minecraft_server.resources_df[
                    (
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "enchantment"
                    )
                    & (
                        self.minecraft_server.resources_df[
                            "Resource location"
                        ].str.lower()
                        == enchantment.lower()
                    )
                ]

                if enchant_data.empty:
                    self.console.print(f"[red]Invalid enchantment: {enchantment}")
                    # Show similar enchantment suggestions with resource locations
                    enchants_df = self.minecraft_server.resources_df[
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "enchantment"
                    ][["Resource location", "Name", "enchantment_max_level"]]

                    suggestions = []
                    for _, row in enchants_df.iterrows():
                        if enchantment.lower() in row["Resource location"].lower():
                            max_level = row["enchantment_max_level"] or 1
                            suggestions.append(
                                (row["Resource location"], row["Name"], max_level)
                            )
                            if len(suggestions) >= 5:
                                break

                    if suggestions:
                        self.console.print("[yellow]Did you mean one of these?")
                        for resource_loc, name, max_level in suggestions:
                            self.console.print(
                                f"  - {resource_loc} ({name}, Max Level: {max_level})"
                            )
                    return

                # Use the correct case from the database
                enchantment = enchant_data.iloc[0]["Resource location"]
                max_level = enchant_data.iloc[0]["enchantment_max_level"] or 1

                # Validate level
                try:
                    level_num = int(level)
                    if level_num < 1 or level_num > max_level:
                        self.console.print(
                            f"[yellow]Warning: Level should be between 1 and {max_level}"
                        )
                        level = str(min(max(1, level_num), max_level))
                except ValueError:
                    self.console.print("[yellow]Invalid level, using 1")
                    level = "1"

            # Construct and send the enchant command
            mc_command = f"enchant {player} {enchantment} {level}"
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error applying enchantment: {e}")

    async def effect_command(self, cmd_line: str) -> None:
        """Apply an effect to a player."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print(
                "[yellow]Usage: effect <player> <effect> [seconds] [amplifier] [hideParticles]"
            )
            return

        _, player, effect, *rest = parts
        seconds = rest[0] if len(rest) > 0 else "30"  # Default 30 seconds
        amplifier = rest[1] if len(rest) > 1 else "0"  # Default level 1 (amplifier 0)
        hide_particles = rest[2] if len(rest) > 2 else "true"  # Default hide particles

        try:
            # Verify effect exists in resources
            if self.minecraft_server.resources_df is not None:
                # Case-insensitive resource location matching
                effect_data = self.minecraft_server.resources_df[
                    (
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "effect"
                    )
                    & (
                        self.minecraft_server.resources_df[
                            "Resource location"
                        ].str.lower()
                        == effect.lower()
                    )
                ]

                if effect_data.empty:
                    self.console.print(f"[red]Invalid effect: {effect}")
                    # Show similar effect suggestions with resource locations
                    effects_df = self.minecraft_server.resources_df[
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "effect"
                    ][["Resource location", "Name"]]

                    suggestions = []
                    for _, row in effects_df.iterrows():
                        if effect.lower() in row["Resource location"].lower():
                            suggestions.append((row["Resource location"], row["Name"]))
                            if len(suggestions) >= 5:
                                break

                    if suggestions:
                        self.console.print("[yellow]Did you mean one of these?")
                        for resource_loc, name in suggestions:
                            self.console.print(f"  - {resource_loc} ({name})")
                    return

                # Use the correct case from the database
                effect = effect_data.iloc[0]["Resource location"]

                # Validate seconds
                try:
                    seconds_num = int(seconds)
                    if seconds_num < 1:
                        self.console.print(
                            "[yellow]Warning: Duration must be at least 1 second"
                        )
                        seconds = "1"
                except ValueError:
                    self.console.print("[yellow]Invalid duration, using 30 seconds")
                    seconds = "30"

                # Validate amplifier
                try:
                    amp_num = int(amplifier)
                    if amp_num < 0 or amp_num > 255:
                        self.console.print(
                            "[yellow]Warning: Amplifier must be between 0 and 255"
                        )
                        amplifier = str(min(max(0, amp_num), 255))
                except ValueError:
                    self.console.print("[yellow]Invalid amplifier, using 0")
                    amplifier = "0"

            # Construct and send the effect command
            mc_command = (
                f"effect {player} {effect} {seconds} {amplifier} {hide_particles}"
            )
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error applying effect: {e}")

    async def effectclear_command(self, cmd_line: str) -> None:
        """Clear all effects from a player."""
        parts = cmd_line.split()
        if len(parts) < 2:
            self.console.print("[yellow]Usage: effectclear <playername>")
            return

        _, player = parts

        try:
            # Construct and send the effect clear command
            mc_command = f"effect clear {player}"
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error clearing effects: {e}")
