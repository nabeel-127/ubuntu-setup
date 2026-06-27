from __future__ import annotations

import curses
from dataclasses import dataclass
from typing import Any

from runtime.catalog import SoftwareItem


class SelectionCancelled(Exception):
    """Raised when the user cancels the interactive selector."""


@dataclass(frozen=True)
class _Row:
    kind: str
    text: str
    item: SoftwareItem | None = None


def select_software(
    items: list[SoftwareItem],
    categories: dict[str, dict[str, Any]],
    *,
    title: str = "Select software to install",
    selected_by_default: bool = True,
    default_selected_ids: set[str] | None = None,
) -> list[str]:
    if not items:
        return []

    rows = _category_rows(items, categories)
    if default_selected_ids is None:
        selected = {item.id for item in items} if selected_by_default else set()
    else:
        visible_ids = {item.id for item in items}
        selected = set(default_selected_ids) & visible_ids

    try:
        return curses.wrapper(_run_selector, rows, selected, title)
    except curses.error as exc:
        raise RuntimeError(f"Unable to draw interactive selector: {exc}") from exc


def _run_selector(stdscr, rows: list[_Row], selected: set[str], title: str) -> list[str]:
    curses.cbreak()
    stdscr.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        curses.use_default_colors()
    except curses.error:
        pass

    cursor = _first_selectable(rows)
    scroll = 0

    while True:
        height, width = stdscr.getmaxyx()
        if height < 8 or width < 45:
            raise RuntimeError("Interactive selector needs a terminal at least 45 columns wide and 8 rows tall.")

        visible = height - 5
        scroll = _scroll_for_cursor(cursor, scroll, visible)
        _draw(stdscr, rows, selected, cursor, scroll, visible, title)

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            cursor = _move(rows, cursor, -1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = _move(rows, cursor, 1)
        elif key == ord(" "):
            item = rows[cursor].item
            if item is not None:
                if item.id in selected:
                    selected.remove(item.id)
                else:
                    selected.add(item.id)
        elif key == ord("a"):
            selected.update(row.item.id for row in rows if row.item is not None)
        elif key == ord("n"):
            selected.clear()
        elif key in (curses.KEY_ENTER, 10, 13):
            ordered_ids = [row.item.id for row in rows if row.item is not None and row.item.id in selected]
            return ordered_ids
        elif key in (27, ord("q")):
            raise SelectionCancelled


def _draw(
    stdscr,
    rows: list[_Row],
    selected: set[str],
    cursor: int,
    scroll: int,
    visible: int,
    title: str,
) -> None:
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    _add_line(stdscr, 0, width, title)
    _add_line(stdscr, 1, width, "Space toggles, Enter continues, a selects all, n selects none, q cancels")

    for offset, row in enumerate(rows[scroll : scroll + visible]):
        y = 3 + offset
        if row.kind == "heading":
            _add_line(stdscr, y, width, row.text)
            continue

        item = row.item
        if item is None:
            continue
        marker = "x" if item.id in selected else " "
        pointer = ">" if scroll + offset == cursor else " "
        line = f"{pointer} [{marker}] {row.text}"
        if scroll + offset == cursor:
            try:
                stdscr.attron(curses.A_REVERSE)
                _add_line(stdscr, y, width, line)
                stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                _add_line(stdscr, y, width, line)
        else:
            _add_line(stdscr, y, width, line)

    count = len(selected)
    total = sum(1 for row in rows if row.item is not None)
    if scroll > 0:
        _add_line(stdscr, 2, width, f"... {scroll} row(s) above")
    if scroll + visible < len(rows):
        remaining = len(rows) - (scroll + visible)
        _add_line(stdscr, height - 2, width, f"... {remaining} row(s) below")
    _add_line(stdscr, height - 1, width, f"Selected {count}/{total}")
    stdscr.refresh()


def _add_line(stdscr, y: int, width: int, text: str) -> None:
    if width <= 0:
        return
    stdscr.addstr(y, 0, _fit(text, width - 1))


def _fit(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return f"{text[:width - 3]}..."


def _category_rows(items: list[SoftwareItem], categories: dict[str, dict[str, Any]]) -> list[_Row]:
    category_order = list(categories)
    category_titles = {category: str(data.get("title", category)) for category, data in categories.items()}
    grouped: dict[str, list[SoftwareItem]] = {}

    for item in items:
        primary = item.categories[0] if item.categories else "_uncategorized"
        grouped.setdefault(primary, []).append(item)

    rows: list[_Row] = []
    ordered_categories = [category for category in category_order if category in grouped]
    ordered_categories.extend(sorted(set(grouped) - set(ordered_categories)))

    for category in ordered_categories:
        title = category_titles.get(category, "Uncategorized" if category == "_uncategorized" else category)
        rows.append(_Row("heading", title.upper()))
        for item in grouped[category]:
            extras = [category_titles.get(extra, extra) for extra in item.categories[1:]]
            text = f"{item.title} [{item.id}]"
            if extras:
                text = f"{text} ({', '.join(extras)})"
            rows.append(_Row("item", text, item))

    return rows


def _first_selectable(rows: list[_Row]) -> int:
    for index, row in enumerate(rows):
        if row.item is not None:
            return index
    return 0


def _move(rows: list[_Row], cursor: int, direction: int) -> int:
    index = cursor
    while True:
        next_index = index + direction
        if next_index < 0 or next_index >= len(rows):
            return cursor
        index = next_index
        if rows[index].item is not None:
            return index


def _scroll_for_cursor(cursor: int, scroll: int, visible: int) -> int:
    if cursor < scroll:
        return cursor
    if cursor >= scroll + visible:
        return cursor - visible + 1
    return scroll
