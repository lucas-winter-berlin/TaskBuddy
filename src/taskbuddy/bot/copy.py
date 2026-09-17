"""Einheitliche Texte: Apple-Reminders-Stimme, Deutsch, kurz."""

from __future__ import annotations

import html

from .. import icons as ic


def _esc(value: str | None) -> str:
    return html.escape(value or "")


def _ok(text: str) -> str:
    return f"{ic.html('ok')} {text}"


def _no(text: str) -> str:
    return f"{ic.html('no')} {text}"


def _warn(text: str) -> str:
    return f"{ic.html('warn')} {text}"


def warning(message: str) -> str:
    return _warn(_esc(message))


# --- Tastatur ---
KEYBOARD_TASKS = "Aufgaben"
KEYBOARD_BACKLOG = "Backlog"
KEYBOARD_SEARCH = "Suchen"
KEYBOARD_PLACEHOLDER = "Aufgabe schreiben"

BTN_SAVE = "Sichern"
BTN_CANCEL = "Abbrechen"
BTN_DONE = "Erledigt"
BTN_EDIT = "Bearbeiten"
BTN_DELETE = "Löschen"
BTN_CLOSE = "Fertig"
BTN_BACK = "Zurück"
BTN_NEXT = "Weiter"
BTN_ALL = "Alle"
BTN_CLEAR = "Alle löschen"
BTN_TITLE = "Titel"
BTN_NOTES = "Notizen"
BTN_PRIORITY = "Priorität"
BTN_PROJECT = "Projekt"
BTN_SUBTASK = "Checkliste"

# --- Statische Meldungen ---
HELP = """<b>TaskBuddy</b>

Schreib eine Aufgabe, um sie zu sichern.
Weitere Zeilen werden Notizen. Zeilen mit <code>-</code> werden zur Checkliste.

<code>#12</code> öffnet eine Aufgabe.
<code>done milch</code> · <code>erledigt milch</code> · <code>fertig #12</code>
<code>/undo</code> zeigt Erledigtes, <code>undo 12</code> stellt sie wieder her.
<code>edit milch</code> · <code>bearbeiten 12</code>

Unten: Aufgaben · Backlog · Suchen
A–D filtert die Liste.

Listen: Privat · Arbeit · Backlog
Backlog ist später — nicht dasselbe wie D.

A · Wichtig &amp; Dringend
B · Dringend &amp; Nicht wichtig
C · Wichtig &amp; Nicht dringend
D · Nicht wichtig &amp; Nicht dringend
"""

START = """<b>TaskBuddy</b>
Schreib eine Aufgabe, oder nutze die Tastatur."""

MENU_READY = "Tastatur ist da."
FALLBACK = "Schreib eine Aufgabe, oder tippe /help."
TASK_HINT = "Schreib eine Aufgabe."
SEARCH_PROMPT = "Wonach suchen?"
SEARCH_HINT = "Suchbegriff senden."

EMPTY_TASKS = "Keine Aufgaben"
EMPTY_DONE = "Nichts zum Wiederherstellen"
EMPTY_SEARCH = "Nichts gefunden"
EMPTY_CLEAR = "Keine offenen Aufgaben"

ASK_PROJECT = "<i>Projekt wählen</i>"
ASK_PRIORITY = "<i>Priorität wählen</i>"
ASK_CONFIRM = "<i>Sichern?</i>"
ASK_TITLE = "<i>Neuer Titel</i>"
ASK_NOTES = "<i>Neue Notizen</i>"
ASK_SUBTASK = "<i>Checklistenpunkt</i>"
ASK_WHICH_TASK = "<i>Welche Aufgabe?</i>"
ASK_WHICH_SUBTASK = "<i>Welcher Punkt?</i>"

DONE_HINT = f"{ASK_WHICH_TASK}\n<code>done milch</code>  oder  <code>done 12</code>"
EDIT_HINT = f"{ASK_WHICH_TASK}\n<code>edit milch</code>  oder  <code>#12</code>"

CANCELLED = _no("Abgebrochen")
CLOSED = _ok("Fertig")
SAVED_MISSING_PROJECT = _warn("Noch kein Projekt")
SAVED_MISSING_PRIORITY = _warn("Noch keine Priorität")
DRAFT_EXPIRED = _warn("Abgelaufen — nochmal senden")
NO_TEXT = _warn("Kein Text")
TITLE_MISSING = NO_TEXT
TEXT_MISSING = NO_TEXT
TITLE_TOO_LONG = _warn("Titel zu lang")
NOT_A_TASK = _warn("Nur Aufgaben lassen sich erledigen")
LIST_EXPIRED = _warn("Liste abgelaufen")
BACKLOG_MISSING = _warn("Backlog fehlt noch")
ERROR = _warn("Etwas ist schiefgegangen")
PRIVATE_LOCK = f"{ic.html('lock')} Dieser Bot ist privat."
TOAST_NOT_A_TASK = "Nur Aufgaben"
DONE_LIST_HEADER = "<b>Erledigt</b>"


def private_with_id(uid) -> str:
    return f"{PRIVATE_LOCK}\nDeine ID: <code>{_esc(str(uid))}</code>"


def settings_text(
    *,
    owner: str,
    backend: str,
    timezone: str,
    gemini: bool,
    environment: str,
) -> str:
    return (
        f"{ic.html('gear')} <b>Einstellungen</b>\n"
        f"Besitzer  <code>{_esc(owner)}</code>\n"
        f"Datenbank  {_esc(backend)}\n"
        f"Zeitzone  {_esc(timezone)}\n"
        f"Gemini  {'an' if gemini else 'aus'}\n"
        f"Umgebung  {_esc(environment)}"
    )


def search_empty(query: str) -> str:
    return f"{EMPTY_SEARCH} für „{_esc(query)}“"


def no_match(query: str) -> str:
    return _warn(f"Keine Aufgabe „{_esc(query)}“")


def project_missing(name: str) -> str:
    return _warn(f"Liste „{_esc(name)}“ gibt es nicht")


def not_found(item_id: int) -> str:
    return _warn(f"Keine Aufgabe <code>#{item_id}</code>")


def completed(item_id: int, title: str) -> str:
    return _ok(f"<code>#{item_id}</code>  {_esc(title)}")


def deleted(item_id: int, title: str) -> str:
    return _ok(f"<code>#{item_id}</code>  {_esc(title)} gelöscht")


def restored(item_id: int, title: str) -> str:
    return _ok(f"<code>#{item_id}</code>  {_esc(title)}")


def already_open(item_id: int, title: str) -> str:
    return (
        f"{ic.html('tip')} <code>#{item_id}</code>  {_esc(title)}  ist schon offen"
    )


def nothing_to_restore(item_id: int) -> str:
    return _warn(f"<code>#{item_id}</code>  nichts zum Wiederherstellen")


def subtask_done(title: str) -> str:
    return _ok(_esc(title))


def deleted_count(count: int) -> str:
    if count == 1:
        return _ok("1 Aufgabe gelöscht")
    return _ok(f"{count} Aufgaben gelöscht")


def confirm_clear(count: int) -> str:
    if count == 1:
        return _warn("Diese Aufgabe löschen?")
    return _warn(f"Alle {count} Aufgaben löschen?")
