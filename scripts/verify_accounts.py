"""Verify accounts script."""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

try:
    from .config import load_config
    from .api import Sub2APIClient, Sub2APIError, create_client, Account
except ImportError:
    from config import load_config
    from api import Sub2APIClient, Sub2APIError, create_client, Account

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
        name_match = re.search(r"\*\*全名\*\*:\s*(.+)", block)

        if email_match:
            email = email_match.group(1).strip()
            prefix = email.replace("@duck.com", "").strip()

            accounts.append(
                {
                    "email": email,
                    "prefix": prefix,
                    "full_name": name_match.group(1).strip() if name_match else None,
                    "block": block,
                }
            )

    return accounts


def find_accounts_file() -> Path | None:
    """Find the accounts markdown file."""
    locations = [
        Path.cwd() / "chatgpt-accounts.md",
        Path(__file__).parent.parent.parent / "chatgpt-accounts.md",
    ]

    for loc in locations:
        md_file = loc / "chatgpt-accounts.md"
        if md_file.exists():
            return md_file

    return None


def verify_account_status(client: Sub2APIClient, account: dict) -> dict:
    """Verify account status via API."""
    result = {
        "prefix": account["prefix"],
        "email": account["email"],
        "full_name": account.get("full_name"),
        "exists": False,
        "status": "unknown",
        "capacity": "-",
        "schedule": "-",
        "issues": [],
    }

    api_account = client.find_account_by_email(account["email"])

    if not api_account:
        result["issues"].append("Account not found in sub2api")
        return result

    result["exists"] = True
    result["status"] = api_account.status
    result["capacity"] = api_account.capacity
    result["schedule"] = api_account.schedule

    if api_account.status not in ("正常", "normal"):
        result["issues"].append(f"Status: {api_account.status}")

    if "关闭" in api_account.schedule or "disabled" in api_account.schedule.lower():
        result["issues"].append("Schedule disabled")

    return result


def get_overall_status(issues: list[str]) -> str:
    """Determine overall status based on issues."""
    if not issues:
        return "healthy"
    elif any("not found" in i.lower() for i in issues):
        return "missing"
    elif any("异常" in i or "error" in i.lower() for i in issues):
        return "unhealthy"
    else:
        return "warning"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify ChatGPT accounts")
    parser.add_argument("-n", "--name", type=str, help="Verify specific account by prefix")
    parser.add_argument(
        "-s",
        "--status",
        type=str,
        default="all",
        choices=["all", "normal", "limiting", "error"],
        help="Filter by status (default: all)",
    )
    parser.add_argument("--file", type=str, help="Path to accounts file")
    parser.add_argument("-o", "--output", type=str, help="Output report to file")

    args = parser.parse_args()

    console.print(f"\n[bold cyan]╔{'═' * 58}╗[/bold cyan]")
    console.print(
        f"[bold cyan]║              ChatGPT Account Verification Script        ║[/bold cyan]"
    )
    console.print(f"[bold cyan]║                       v5.0                          ║[/bold cyan]")
    console.print(f"[bold cyan]╚{'═' * 58}╝[/bold cyan]\n")

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

    console.print(f"[green]Found {len(accounts)} accounts, verifying...[/green]\n")

    if args.name:
        accounts = [a for a in accounts if args.name in a["prefix"]]
        if not accounts:
            console.print(f"[red]Account not found:[/red] {args.name}")
            sys.exit(1)

    results = []

    for account in accounts:
        result = verify_account_status(client, account)
        result["overall_status"] = get_overall_status(result["issues"])
        results.append(result)

        status_icon = {
            "healthy": "[green]✓[/green]",
            "warning": "[yellow]⚠[/yellow]",
            "unhealthy": "[red]✗[/red]",
            "missing": "[red]?[/red]",
        }

        icon = status_icon.get(result["overall_status"], "?")
        console.print(f"  {icon} {result['prefix']}: {result['status']}")

    table = Table(title="Verification Results")
    table.add_column("Status", style="cyan", width=10)
    table.add_column("Prefix", style="white")
    table.add_column("Email", style="white")
    table.add_column("Capacity", style="white")
    table.add_column("Issues", style="red")

    status_colors = {"healthy": "green", "warning": "yellow", "unhealthy": "red", "missing": "red"}

    for result in results:
        color = status_colors.get(result["overall_status"], "white")
        issues_text = "; ".join(result["issues"]) if result["issues"] else "-"
        table.add_row(
            f"[{color}]{result['overall_status'].upper()}[/{color}]",
            result["prefix"],
            result["email"],
            result["capacity"],
            issues_text,
        )

    console.print()
    console.print(table)

    summary_table = Table(title="Summary")
    summary_table.add_column("Status", style="cyan")
    summary_table.add_column("Count", style="white")
    summary_table.add_column("Percentage", style="white")

    total = len(results)
    status_counts = {}
    for r in results:
        status = r["overall_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    for status in ["healthy", "warning", "unhealthy", "missing"]:
        if status in status_counts:
            count = status_counts[status]
            pct = (count / total * 100) if total > 0 else 0
            summary_table.add_row(status.upper(), str(count), f"{pct:.1f}%")

    console.print()
    console.print(summary_table)

    if args.output:
        import json

        report = {
            "timestamp": Path(__file__).stat().st_mtime,
            "total": total,
            "summary": status_counts,
            "results": results,
        }
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        console.print(f"\n[green]Report saved to:[/green] {args.output}")

    issues_count = len([r for r in results if r["overall_status"] != "healthy"])
    sys.exit(0 if issues_count == 0 else 1)


if __name__ == "__main__":
    main()
