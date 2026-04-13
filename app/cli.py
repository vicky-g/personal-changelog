"""
Typer CLI — thin wrapper over EntryService. No business logic here.
"""

import asyncio
import uuid
from datetime import date, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from app.database import get_session
from app.exceptions import EntryNotEditable, EntryNotFound
from app.models import Entry, EntryType
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


def _render_entries(entries: list[Entry], title: str = "", show_id: bool = False) -> None:
    if not entries:
        console.print("[dim]No entries found.[/dim]")
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        title=title or None,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Type", style="magenta", width=6)
    table.add_column("Date", style="cyan", no_wrap=True, width=12)
    table.add_column("Content")
    table.add_column("Tags", style="dim", width=20)
    if show_id:
        table.add_column("ID", style="dim")

    for entry in entries:
        tags_str = ", ".join(entry.tags) if entry.tags else ""
        lock = "" if entry.is_editable else " [dim]🔒[/dim]"
        row_style = "on grey23" if entry.entry_type == EntryType.grow else ""
        row = [entry.entry_type.value, str(entry.date), entry.content + lock, tags_str]
        if show_id:
            row.append(str(entry.id))
        table.add_row(*row, style=row_style)

    console.print(table)


# ── Commands ───────────────────────────────────────────────────────────────────

@app.command()
def add(
    content: str = typer.Argument(..., help="Entry content"),
    entry_type: EntryType = typer.Option(..., "--type", "-T", help="Entry type: glow or grow"),
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

    data = EntryCreate(entry_type=entry_type, content=content, date=parsed_date, tags=tag or [])

    async def _create():
        async with get_session() as session:
            service = EntryService(session)
            return await service.create(data)

    entry = _run(_create())
    console.print(
        f"[green]Added {entry.entry_type.value}[/green] [dim]{str(entry.id)[:8]}[/dim] for {entry.date}"
    )


@app.command()
def yesterday(
    entry_type: Optional[EntryType] = typer.Option(None, "--type", "-T", help="Filter by type"),
    show_id: bool = typer.Option(False, "--id", help="Show full entry ID"),
) -> None:
    """List all entries for yesterday."""
    yesterday_date = date.today() - timedelta(days=1)

    async def _list():
        async with get_session() as session:
            service = EntryService(session)
            return await service.list_entries(entry_type=entry_type, date=yesterday_date, limit=100)

    entries = _run(_list())
    _render_entries(entries, title=f"Entries for {yesterday_date}", show_id=show_id)


@app.command()
def today(
    entry_type: Optional[EntryType] = typer.Option(None, "--type", "-T", help="Filter by type"),
    show_id: bool = typer.Option(False, "--id", help="Show full entry ID"),
) -> None:
    """List all entries for today."""
    async def _list():
        async with get_session() as session:
            service = EntryService(session)
            return await service.list_entries(entry_type=entry_type, date=date.today(), limit=100)

    entries = _run(_list())
    _render_entries(entries, title=f"Entries for {date.today()}", show_id=show_id)


@app.command(name="list")
def list_entries(
    entry_type: Optional[EntryType] = typer.Option(None, "--type", "-T", help="Filter by type"),
    entry_date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Filter by date (YYYY-MM-DD)"
    ),
    tag: Optional[list[str]] = typer.Option(
        None, "--tag", "-t", help="Filter by tag (repeatable: -t foo -t bar)"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Max entries to show"),
    show_id: bool = typer.Option(False, "--id", help="Show full entry ID"),
) -> None:
    """List entries, optionally filtered by type, date, or tag."""
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
            return await service.list_entries(
                entry_type=entry_type, date=parsed_date, tags=tag or None, limit=limit
            )

    entries = _run(_list())
    _render_entries(entries, show_id=show_id)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    entry_type: Optional[EntryType] = typer.Option(None, "--type", "-T", help="Filter by type"),
    show_id: bool = typer.Option(False, "--id", help="Show full entry ID"),
) -> None:
    """Full-text search across entry content and tags."""
    async def _search():
        async with get_session() as session:
            service = EntryService(session)
            return await service.search(query, entry_type)

    entries = _run(_search())
    _render_entries(entries, title=f'Results for "{query}"', show_id=show_id)


@app.command()
def edit(
    entry_id: str = typer.Argument(..., help="Entry ID (or unique prefix)"),
    entry_type: Optional[EntryType] = typer.Option(None, "--type", "-T", help="Change entry type"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="New content"),
    tag: Optional[list[str]] = typer.Option(
        None, "--tag", "-t", help="Replace tags (repeatable)"
    ),
    entry_date: Optional[str] = typer.Option(
        None, "--date", "-d", help="New date as YYYY-MM-DD"
    ),
) -> None:
    """Edit an existing entry (only within 24 hours of creation)."""
    if not entry_type and not content and not tag and not entry_date:
        console.print("[yellow]Nothing to update. Use --type, --content, --tag, or --date.[/yellow]")
        raise typer.Exit(0)

    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        console.print(f"[red]'{entry_id}' is not a valid UUID.[/red]")
        raise typer.Exit(1)

    parsed_date: date | None = None
    if entry_date:
        try:
            parsed_date = date.fromisoformat(entry_date)
        except ValueError:
            console.print(f"[red]Invalid date '{entry_date}'. Use YYYY-MM-DD.[/red]")
            raise typer.Exit(1)

    data = EntryUpdate(entry_type=entry_type, content=content, tags=tag if tag is not None else None, date=parsed_date)

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


@app.command(name="add-tag")
def add_tag(
    entry_id: str = typer.Argument(..., help="Entry ID"),
    tag: list[str] = typer.Option(..., "--tag", "-t", help="Tag to append (repeatable: -t foo -t bar)"),
) -> None:
    """Append tags to an existing entry without removing current ones."""
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        console.print(f"[red]'{entry_id}' is not a valid UUID.[/red]")
        raise typer.Exit(1)

    async def _append():
        async with get_session() as session:
            service = EntryService(session)
            return await service.append_tags(eid, tag)

    try:
        entry = _run(_append())
        console.print(f"[green]Updated tags[/green] on [dim]{str(entry.id)[:8]}[/dim]: {', '.join(entry.tags)}")
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


@app.command(name="tags")
def list_tags(
    entry_type: Optional[EntryType] = typer.Option(None, "--type", "-T", help="Filter by type"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max tags to show"),
    offset: int = typer.Option(0, "--offset", help="Number of tags to skip"),
) -> None:
    """List all unique tags."""
    async def _list():
        async with get_session() as session:
            service = EntryService(session)
            return await service.list_tags(entry_type, limit=limit, offset=offset)

    items, total = _run(_list())

    if not items:
        console.print("[dim]No tags found.[/dim]")
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        title=f"Tags ({offset + 1}–{offset + len(items)} of {total})",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Tag", style="cyan")
    for tag in items:
        table.add_row(tag)
    console.print(table)


if __name__ == "__main__":
    app()
