"""Cleanup accounts script."""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

try:
    from .config import load_config
    from .api import Sub2APIClient, Sub2APIError, create_client
except ImportError:
    from config import load_config
    from api import Sub2APIClient, Sub2APIError, create_client

console = Console()


def parse_accounts_from_file(file_path: Path) -> list[dict]:
    """Parse accounts from markdown file."""
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")
    accounts = []

    account_blocks = re.split(r"## 账号 \d+", content)

    for block in account_blocks:
        if not block.strip():
            continue

        email_match = re.search(r"\*\*邮箱\*\*:\s*(.+)", block)
        password_match = re.search(r"\*\*密码\*\*:\s*(.+)", block)
        name_match = re.search(r"\*\*全名\*\*:\s*(.+)", block)
        birthday_match = re.search(r"\*\*生日\*\*:\s*(.+)", block)

        if email_match:
            email = email_match.group(1).strip()
            prefix = email.replace("@duck.com", "").strip()

            accounts.append(
                {
                    "email": email,
                    "prefix": prefix,
                    "password": password_match.group(1).strip() if password_match else None,
                    "full_name": name_match.group(1).strip() if name_match else None,
                    "birthday": birthday_match.group(1).strip() if birthday_match else None,
                    "block": block,
                }
            )

    return accounts


def find_accounts_file() -> Path | None:
    """Find the accounts markdown file."""
    locations = [
        Path.cwd() / "chatgpt-accounts.md",
        Path(__file__).parent.parent.parent / "chatgpt-accounts.md",
        Path.home(),
    ]

    for loc in locations:
        md_file = loc / "chatgpt-accounts.md"
        if md_file.exists():
            return md_file

    return None


def remove_account_from_file(file_path: Path, account: dict) -> bool:
    """Remove account block from markdown file."""
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")

    pattern = rf"## 账号 \d+\s*\n[\s\S]*?{re.escape(account['email'])}[\s\S]*?(?=## 账号 \d+|$)"
    new_content = re.sub(pattern, "", content, count=1)

    if new_content == content:
        return False

    new_content = re.sub(r"\n{3,}", "\n\n", new_content)
    file_path.write_text(new_content, encoding="utf-8")

    return True


def confirm_delete(account_prefix: str) -> bool:
    """Ask for delete confirmation."""
    while True:
        answer = console.input(f"[yellow]Delete account '{account_prefix}'? (y/N):[/yellow] ")
        if answer.lower() in ("y", "yes"):
            return True
        elif answer.lower() in ("n", "no", ""):
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Cleanup ChatGPT accounts")
    parser.add_argument("-n", "--name", type=str, help="Delete specific account by prefix")
    parser.add_argument(
        "-s",
        "--status",
        type=str,
        default="unhealthy",
        choices=["unhealthy", "disabled", "all"],
        help="Delete accounts by status (default: unhealthy)",
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Preview mode, don't actually delete"
    )
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--file", type=str, help="Path to accounts file")

    args = parser.parse_args()

    console.print(f"\n[bold cyan]╔{'═' * 58}╗[/bold cyan]")
    console.print(
        f"[bold cyan]║              ChatGPT Account Cleanup Script           ║[/bold cyan]"
    )
    console.print(f"[bold cyan]║                       v5.0                          ║[/bold cyan]")
    console.print(f"[bold cyan]╚{'═' * 58}╝[/bold cyan]\n")

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE - No accounts will be deleted[/yellow]\n")

    accounts_file = Path(args.file) if args.file else find_accounts_file()

    if not accounts_file:
        console.print("[red]Error: Could not find accounts file (chatgpt-accounts.md)[/red]")
        sys.exit(1)

    console.print(f"[cyan]Accounts file:[/cyan] {accounts_file}\n")

    try:
        config = load_config()
    except FileNotFoundError:
        console.print("[red]Error: Configuration file not found[/red]")
        console.print("[yellow]Please run 'python -m scripts.setup' first[/yellow]")
        sys.exit(1)

    client = create_client(config)

    try:
        if not client.test_connection():
            raise Sub2APIError("Connection test failed")
    except Sub2APIError as e:
        console.print(f"[red]Connection failed:[/red] {e}")
        sys.exit(1)

    accounts = parse_accounts_from_file(accounts_file)

    if not accounts:
        console.print("[yellow]No accounts found in file[/yellow]")
        sys.exit(0)

    console.print(f"[green]Found {len(accounts)} accounts[/green]\n")

    if args.name:
        accounts_to_delete = [a for a in accounts if args.name in a["prefix"]]
    else:
        console.print(f"[cyan]Filtering by status:[/cyan] {args.status}\n")

        if args.status == "all":
            accounts_to_delete = accounts
        else:
            api_accounts = client.get_accounts()
            api_email_set = {acc.email.lower() for acc in api_accounts}

            accounts_to_delete = []
            for account in accounts:
                if account["email"].lower() not in api_email_set:
                    accounts_to_delete.append(account)

    if not accounts_to_delete:
        console.print("[yellow]No accounts to delete[/yellow]")
        sys.exit(0)

    table = Table(title="Accounts to Delete")
    table.add_column("Prefix", style="cyan")
    table.add_column("Email", style="white")
    table.add_column("Name", style="white")

    for account in accounts_to_delete:
        table.add_row(account["prefix"], account["email"], account.get("full_name", "-"))

    console.print(table)

    if not args.yes and not args.dry_run:
        if not confirm_delete("all"):
            console.print("[yellow]Cancelled[/yellow]")
            sys.exit(0)

    deleted_count = 0
    failed_count = 0

    for account in accounts_to_delete:
        if args.dry_run:
            console.print(f"[cyan]Would delete:[/cyan] {account['prefix']}")
            deleted_count += 1
        else:
            try:
                api_account = client.find_account_by_email(account["email"])
                if api_account:
                    client.delete_account(api_account.id)
                    console.print(f"[green]Deleted from API:[/green] {account['prefix']}")

                if remove_account_from_file(accounts_file, account):
                    console.print(f"[green]Removed from file:[/green] {account['prefix']}")

                deleted_count += 1

            except Sub2APIError as e:
                console.print(f"[red]Failed to delete {account['prefix']}:[/red] {e}")
                failed_count += 1

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]Deleted:[/green] {deleted_count}")
    console.print(f"[red]Failed:[/red] {failed_count}")

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
