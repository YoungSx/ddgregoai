"""Setup wizard for initial configuration."""

import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt, Confirm

try:
    from .config import Config, save_config, load_config
except ImportError:
    from config import Config, save_config, load_config

console = Console()


def is_configured() -> bool:
    """Check if configuration already exists."""
    try:
        load_config()
        return True
    except FileNotFoundError:
        return False


def run_setup() -> None:
    """Run the setup wizard."""
    console.print(f"\n[bold cyan]╔{'═' * 58}╗[/bold cyan]")
    console.print(
        f"[bold cyan]║       OpenAI DDG Account Registration Setup Wizard     ║[/bold cyan]"
    )
    console.print(
        f"[bold cyan]║                       v6.0                           ║[/bold cyan]"
    )
    console.print(f"[bold cyan]╚{'═' * 58}╝[/bold cyan]\n")

    if is_configured():
        overwrite = Confirm.ask(
            "[yellow]Configuration already exists. Overwrite?[/yellow]", default=False
        )
        if not overwrite:
            console.print("[cyan]Keeping existing configuration.[/cyan]")
            return

    console.print("[cyan]This wizard will help you configure the application.[/cyan]\n")

    config = Config()

    console.print("[bold]Sub2API Configuration[/bold]")
    console.print("-" * 40)

    config.sub2api.base_url = Prompt.ask(
        "[cyan]Sub2API Base URL[/cyan]", default="https://sub2api-sx.fly.dev"
    ).rstrip("/")

    config.sub2api.admin_api_key = Prompt.ask("[cyan]Admin API Key[/cyan]", password=True)

    console.print("\n[bold]Default Account Settings[/bold]")
    console.print("-" * 40)

    config.defaults.platform = Prompt.ask("[cyan]Platform[/cyan]", default="OpenAI")

    config.defaults.account_type = Prompt.ask(
        "[cyan]Account Type[/cyan]", default="OAuth ChatGPT OAuth"
    )

    config.defaults.group = Prompt.ask("[cyan]Group Name[/cyan]", default="OpenAI-Free")

    config.defaults.group_id = int(Prompt.ask("[cyan]Group ID[/cyan]", default="1"))

    config.defaults.password_pattern = Prompt.ask(
        "[cyan]Password Pattern (use {n} for number)[/cyan]", default="TestPass{n}!@#"
    )

    console.print("\n[bold]Advanced Settings[/bold]")
    console.print("-" * 40)

    config.advanced.max_retries = int(Prompt.ask("[cyan]Max Retries[/cyan]", default="3"))

    config.advanced.timeout_ms = int(Prompt.ask("[cyan]Timeout (ms)[/cyan]", default="60000"))

    console.print("\n[bold]Saving configuration...[/bold]")

    config_path = Path.cwd() / "openai-sub2api-config.json"
    save_config(config, config_path)

    console.print(f"\n[bold green]Configuration saved to:[/bold green] {config_path}")

    console.print("\n[bold]Next Steps[/bold]")
    console.print("-" * 40)
    console.print("1. Register accounts:")
    console.print(
        "   [cyan]python -m scripts.playwright_register -e 'a@duck.com' -p 'Pass1' -c 1[/cyan]"
    )
    console.print("")
    console.print("2. Verify accounts:")
    console.print("   [cyan]python -m scripts.verify_accounts[/cyan]")
    console.print("")
    console.print("3. Cleanup accounts:")
    console.print("   [cyan]python -m scripts.cleanup_accounts --status unhealthy[/cyan]")
    console.print("")


def main():
    """Main entry point."""
    try:
        run_setup()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
