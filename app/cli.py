"""
Typer CLI — thin wrapper over EntryService. No business logic here.
"""

import asyncio
import uuid
from datetime import date, datetime, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from app.database import get_session
from app.exceptions import EntryNotEditable, EntryNotFound
from app.models import Entry
from app.schemas import EntryCreate, EntryUpdate
from app.services.entry_service import EntryService

app = typer.Typer(
    name="changelog",
    help="Personal changelog — track what you did, generate summaries.",
    no_args_is_help=True,
)
console = Console()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _render_entries(entries: list[Entry], title: str = "") -> None:
    if not entries:
        console.print("[dim]No entries found.[/dim]")
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        title=title or None,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Date", style="cyan", no_wrap=True, width=12)
    table.add_column("Content")
    table.add_column("Tags", style="dim", width=20)
    table.add_column("ID", style="dim", width=10)

    for entry in entries:
        tags_str = ", ".join(entry.tags) if entry.tags else ""
        short_id = str(entry.id)[:8]
        lock = "" if entry.is_editable else " [dim]🔒[/dim]"
        table.add_row(
            str(entry.date),
            entry.content + lock,
            tags_str,
            short_id,
        )

    console.print(table)


# ── Commands ───────────────────────────────────────────────────────────────────

@app.command()
def add(
    content: str = typer.Argument(..., help="Entry content"),
    tag: Optional[list[str]] = typer.Option(
        None, "--tag", "-t", help="Tag (repeatable: -t foo -t bar)"
    ),
    entry_date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Date as YYYY-MM-DD (default: today)"
    ),
) -> None:
    """Add a new changelog entry."""
    parsed_date: date
    if entry_date:
        try:
            parsed_date = date.fromisoformat(entry_date)
        except ValueError:
            console.print(f"[red]Invalid date '{entry_date}'. Use YYYY-MM-DD.[/red]")
            raise typer.Exit(1)
    else:
        parsed_date = date.today()

    data = EntryCreate(content=content, date=parsed_date, tags=tag or [])

    async def _create():
        async with get_session() as session:
            service = EntryService(session)
            return await service.create(data)

    entry = _run(_create())
    console.print(f"[green]Added entry[/green] [dim]{str(entry.id)[:8]}[/dim] for {entry.date}")


@app.command()
def today() -> None:
    """List all entries for today."""
    async def _list():
        async with get_session() as session:
            service = EntryService(session)
            return await service.list_entries(date=date.today(), limit=100)

    entries = _run(_list())
    _render_entries(entries, title=f"Entries for {date.today()}")


@app.command(name="list")
def list_entries(
    entry_date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Filter by date (YYYY-MM-DD)"
    ),
    tag: Optional[list[str]] = typer.Option(
        None, "--tag", "-t", help="Filter by tag (repeatable: -t foo -t bar)"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Max entries to show"),
) -> None:
    """List entries, optionally filtered by date or tag."""
    parsed_date: date | None = None
    if entry_date:
        try:
            parsed_date = date.fromisoformat(entry_date)
        except ValueError:
            console.print(f"[red]Invalid date '{entry_date}'. Use YYYY-MM-DD.[/red]")
            raise typer.Exit(1)

    async def _list():
        async with get_session() as session:
            service = EntryService(session)
            return await service.list_entries(date=parsed_date, tags=tag or None, limit=limit)

    entries = _run(_list())
    _render_entries(entries)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
) -> None:
    """Full-text search across entry content and tags."""
    async def _search():
        async with get_session() as session:
            service = EntryService(session)
            return await service.search(query)

    entries = _run(_search())
    _render_entries(entries, title=f'Results for "{query}"')


@app.command()
def edit(
    entry_id: str = typer.Argument(..., help="Entry ID (or unique prefix)"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="New content"),
    tag: Optional[list[str]] = typer.Option(
        None, "--tag", "-t", help="Replace tags (repeatable)"
    ),
) -> None:
    """Edit an existing entry (only within 24 hours of creation)."""
    if not content and not tag:
        console.print("[yellow]Nothing to update. Use --content or --tag.[/yellow]")
        raise typer.Exit(0)

    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        console.print(f"[red]'{entry_id}' is not a valid UUID.[/red]")
        raise typer.Exit(1)

    data = EntryUpdate(content=content, tags=tag if tag is not None else None)

    async def _update():
        async with get_session() as session:
            service = EntryService(session)
            return await service.update(eid, data)

    try:
        entry = _run(_update())
        console.print(f"[green]Updated entry[/green] [dim]{str(entry.id)[:8]}[/dim]")
    except EntryNotFound:
        console.print(f"[red]Entry '{entry_id}' not found.[/red]")
        raise typer.Exit(1)
    except EntryNotEditable:
        console.print("[red]This entry is locked — it was created more than 24 hours ago.[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    entry_id: str = typer.Argument(..., help="Entry ID (or unique prefix)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete an entry."""
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        console.print(f"[red]'{entry_id}' is not a valid UUID.[/red]")
        raise typer.Exit(1)

    if not yes:
        confirmed = typer.confirm(f"Delete entry {entry_id[:8]}?")
        if not confirmed:
            raise typer.Exit(0)

    async def _delete():
        async with get_session() as session:
            service = EntryService(session)
            await service.delete(eid)

    try:
        _run(_delete())
        console.print(f"[green]Deleted entry[/green] [dim]{entry_id[:8]}[/dim]")
    except EntryNotFound:
        console.print(f"[red]Entry '{entry_id}' not found.[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
