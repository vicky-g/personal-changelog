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
from app.exceptions import EntryNotEditable, EntryNotFound, NoEntriesFound, SummaryNotFound
from app.models import Entry, PeriodType, SummaryType
from app.schemas import EntryCreate, EntryUpdate, SummaryCreate
from app.services.entry_service import EntryService
from app.services.summary_service import SummaryService

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
        row_style = "on grey23" if entry.entry_type == "grow" else ""
        row = [entry.entry_type, str(entry.date), entry.content + lock, tags_str]
        if show_id:
            row.append(str(entry.id))
        table.add_row(*row, style=row_style)

    console.print(table)


# ── Commands ───────────────────────────────────────────────────────────────────

@app.command()
def add(
    content: str = typer.Argument(..., help="Entry content"),
    entry_type: str = typer.Option(..., "--type", "-T", help="Entry type: glow or grow"),
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
        f"[green]Added {entry.entry_type}[/green] [dim]{str(entry.id)[:8]}[/dim] for {entry.date}"
    )


@app.command()
def yesterday(
    entry_type: Optional[str] = typer.Option(None, "--type", "-T", help="Filter by type"),
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
    entry_type: Optional[str] = typer.Option(None, "--type", "-T", help="Filter by type"),
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
    entry_type: Optional[str] = typer.Option(None, "--type", "-T", help="Filter by type"),
    entry_date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Filter by date (YYYY-MM-DD)"
    ),
    tag: Optional[list[str]] = typer.Option(
        None, "--tag", "-t", help="Filter by tag (repeatable: -t foo -t bar)"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Max entries to show"),
    offset: int = typer.Option(0, "--offset", help="Number of entries to skip"),
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
                entry_type=entry_type, date=parsed_date, tags=tag or None, limit=limit, offset=offset
            )

    entries = _run(_list())
    _render_entries(entries, show_id=show_id)


@app.command()
def get(
    entry_id: str = typer.Argument(..., help="Entry ID"),
    show_id: bool = typer.Option(False, "--id", help="Show full entry ID"),
) -> None:
    """Fetch a single entry by ID."""
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        console.print(f"[red]'{entry_id}' is not a valid UUID.[/red]")
        raise typer.Exit(1)

    async def _get():
        async with get_session() as session:
            service = EntryService(session)
            return await service.get(eid)

    try:
        entry = _run(_get())
        _render_entries([entry], show_id=show_id)
    except EntryNotFound:
        console.print(f"[red]Entry '{entry_id}' not found.[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    entry_type: Optional[str] = typer.Option(None, "--type", "-T", help="Filter by type"),
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
    entry_type: Optional[str] = typer.Option(None, "--type", "-T", help="Change entry type"),
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
    entry_type: Optional[str] = typer.Option(None, "--type", "-T", help="Filter by type"),
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


@app.command()
def summarize(
    period_type: PeriodType = typer.Option(..., "--period", "-p", help="Period: weekly, monthly, quarterly"),
    summary_type: SummaryType = typer.Option(..., "--type", "-T", help="Type: reflection, perf_review, opportunities"),
    start_date: str = typer.Option(..., "--start", "-s", help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Option(..., "--end", "-e", help="End date (YYYY-MM-DD)"),
) -> None:
    """Generate an AI summary for a date range."""
    try:
        parsed_start = date.fromisoformat(start_date)
    except ValueError:
        console.print(f"[red]Invalid start date '{start_date}'. Use YYYY-MM-DD.[/red]")
        raise typer.Exit(1)
    try:
        parsed_end = date.fromisoformat(end_date)
    except ValueError:
        console.print(f"[red]Invalid end date '{end_date}'. Use YYYY-MM-DD.[/red]")
        raise typer.Exit(1)

    data = SummaryCreate(
        period_type=period_type,
        summary_type=summary_type,
        start_date=parsed_start,
        end_date=parsed_end,
    )

    async def _generate():
        async with get_session() as session:
            service = SummaryService(session)
            return await service.generate(
                period_type=data.period_type,
                start_date=data.start_date,
                end_date=data.end_date,
                summary_type=data.summary_type,
            )

    try:
        summary = _run(_generate())
    except NoEntriesFound as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]{summary.summary_type.value}[/bold cyan] · {summary.period_type.value} · {summary.start_date} → {summary.end_date}\n")
    console.print(summary.generated_text or "")
    console.print(f"\n[dim]Saved as {str(summary.id)[:8]}[/dim]")


@app.command(name="summaries")
def list_summaries(
    period_type: Optional[PeriodType] = typer.Option(None, "--period", "-p", help="Filter by period type"),
    summary_type: Optional[SummaryType] = typer.Option(None, "--type", "-T", help="Filter by summary type"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max summaries to show"),
    offset: int = typer.Option(0, "--offset", help="Number of summaries to skip"),
) -> None:
    """List generated summaries."""
    async def _list():
        async with get_session() as session:
            service = SummaryService(session)
            return await service.list_summaries(
                period_type=period_type,
                summary_type=summary_type,
                limit=limit,
                offset=offset,
            )

    items = _run(_list())

    if not items:
        console.print("[dim]No summaries found.[/dim]")
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=10)
    table.add_column("Type", style="magenta", width=14)
    table.add_column("Period", style="cyan", width=10)
    table.add_column("Range", width=24)
    table.add_column("Bullets", justify="right", width=7)

    for s in items:
        table.add_row(
            str(s.id)[:8],
            s.summary_type.value,
            s.period_type.value,
            f"{s.start_date} → {s.end_date}",
            str(len(s.raw_bullets)),
        )

    console.print(table)


@app.command(name="summary")
def get_summary(
    summary_id: str = typer.Argument(..., help="Summary ID"),
) -> None:
    """Show the full text of a generated summary."""
    try:
        sid = uuid.UUID(summary_id)
    except ValueError:
        console.print(f"[red]'{summary_id}' is not a valid UUID.[/red]")
        raise typer.Exit(1)

    async def _get():
        async with get_session() as session:
            service = SummaryService(session)
            return await service.get(sid)

    try:
        summary = _run(_get())
    except SummaryNotFound:
        console.print(f"[red]Summary '{summary_id}' not found.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]{summary.summary_type.value}[/bold cyan] · {summary.period_type.value} · {summary.start_date} → {summary.end_date}\n")
    console.print(summary.generated_text or "")


if __name__ == "__main__":
    app()
