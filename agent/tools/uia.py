"""See and drive windows by their accessibility tree (Windows UI Automation).

Why: screenshots + x,y clicks are slow (every step needs an image) and miss when the layout
shifts. Windows exposes every button, link, text box and menu item of most apps - including
Chrome and Edge web pages - with a name and a rectangle. Reading that tree is text-only and
fast, and clicking "the button named Apply now" does not depend on pixels.

Chrome/Edge are driven through the same tree instead of DevTools/CDP: since Chrome 136 remote
debugging is refused on the default profile, and the owner's logins live in the default profile.

Tools:
  ui_elements  - numbered list of the controls in a window (role, name, value, position)
  ui_click     - click a control by number (from the last ui_elements) or by name
  ui_type      - put text into an edit box by number or name (clears it first by default)
  read_page    - all visible text of a window / web page, no clipboard, no scrolling
"""

import re
import threading
import time

from . import tool

try:
    import uiautomation as auto
except Exception:  # noqa: BLE001
    auto = None

_LOCK = threading.Lock()
# Last listing, so the model can say "click 14" after ui_elements.
_LAST = {"hwnd": None, "items": []}

_INTERACTIVE = {
    "ButtonControl", "HyperlinkControl", "EditControl", "CheckBoxControl", "RadioButtonControl",
    "ComboBoxControl", "MenuItemControl", "TabItemControl", "ListItemControl", "TreeItemControl",
    "SplitButtonControl", "DocumentControl", "SliderControl", "SpinnerControl",
}
_TEXTY = {"TextControl", "HeaderControl", "HeaderItemControl", "DataItemControl", "ImageControl"}


_ZW = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)


def _clean(text):
    """Window/control names can hide zero-width spaces (Edge: 'Microsoft​ Edge')."""
    return (text or "").translate(_ZW)


def _need():
    if auto is None:
        raise RuntimeError("uiautomation is not installed: run .venv\\Scripts\\pip install uiautomation")


def _window(title=None):
    """Foreground window, or the first visible top-level window whose title contains `title`."""
    if not title:
        return auto.ControlFromHandle(auto.GetForegroundWindow())
    needle = _clean(title).lower()
    for win in auto.GetRootControl().GetChildren():
        try:
            if needle in _clean(win.Name).lower() and not win.IsOffscreen:
                return win
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError(f"No open window with '{title}' in its title. Use list_windows.")


def _web_doc(win):
    """The web page inside a window: Chrome/Edge tabs and WebView2 apps (new Outlook, Teams,
    WhatsApp) all expose it as a Document whose value is the page URL."""
    if win is None:
        return None
    best = None
    for doc in _walk(win, {"DocumentControl"}, 20, time.time() + 4, max_depth=30):
        if _value(doc).startswith(("http", "file:", "chrome", "edge", "about:")):
            best = doc
    return best


def _woken(win):
    """Chromium/WebView2 build their accessibility tree lazily on the first query, so a fresh
    window can show only its caption buttons. Touch it once and give it a moment."""
    if len(_walk(win, _INTERACTIVE, 8, time.time() + 3)) < 8:
        time.sleep(1.0)
    return win


def _role(ctrl):
    return ctrl.ControlTypeName.replace("Control", "").lower()


def _value(ctrl):
    try:
        pattern = ctrl.GetValuePattern()
        if pattern:
            return pattern.Value or ""
    except Exception:  # noqa: BLE001
        pass
    return ""


def _walk(root, want, limit, deadline, max_depth=40, offscreen=False):
    """Depth-first walk collecting controls; bounded by count, depth and time."""
    out = []
    stack = [(root, 0)]
    while stack and len(out) < limit and time.time() < deadline:
        ctrl, depth = stack.pop()
        try:
            kind = ctrl.ControlTypeName
            if depth and kind in want:
                rect = ctrl.BoundingRectangle
                if offscreen or (rect.width() > 1 and rect.height() > 1 and not ctrl.IsOffscreen):
                    out.append(ctrl)
            if depth < max_depth:
                kids = ctrl.GetChildren()
                stack.extend((k, depth + 1) for k in reversed(kids))
        except Exception:  # noqa: BLE001
            continue
    return out


def _offscreen(ctrl, view=None):
    """Off-screen = no size, or (for web pages) outside the visible page area. Chrome reports
    IsOffscreen=True for everything when the window is behind another one, so the page
    viewport rectangle is the better test there."""
    rect = ctrl.BoundingRectangle
    if rect.width() <= 1 or rect.height() <= 1:
        return True
    if view is not None:
        return rect.bottom <= view.top or rect.top >= view.bottom or rect.right <= view.left or rect.left >= view.right
    return bool(ctrl.IsOffscreen)


def _describe(i, ctrl, view=None):
    rect = ctrl.BoundingRectangle
    name = re.sub(r"\s+", " ", _clean(ctrl.Name)).strip()[:90]
    val = re.sub(r"\s+", " ", _value(ctrl)).strip()[:60]
    bits = [f"[{i}] {_role(ctrl)}", f'"{name}"' if name else "(no name)"]
    if val and val != name:
        bits.append(f"value={val!r}")
    if _offscreen(ctrl, view):
        bits.append("(off-screen: ui_click scrolls to it)")
    else:
        bits.append(f"@{(rect.left + rect.right) // 2},{(rect.top + rect.bottom) // 2}")
    return " ".join(bits)


@tool(
    "ui_elements",
    "List the buttons, links, text boxes, menu items etc. of a window WITHOUT a screenshot, as a "
    "numbered list (role, name, value, screen position). Works for normal apps and for web pages in "
    "Chrome/Edge. Then use ui_click / ui_type with the number or name. Much faster and more accurate "
    "than screenshot + x,y click - prefer it for forms, menus and web pages. Use a screenshot only "
    "when the list does not show what you need (canvas apps, images, games).",
    {
        "window": {"type": "string", "description": "Part of the window title. Omit for the foreground window."},
        "filter": {"type": "string", "description": "Only items whose name/value contains this text (case-insensitive)."},
        "include_text": {"type": "boolean", "description": "Also list plain text labels, not just controls. Default false."},
        "max_items": {"type": "integer", "description": "Default 120."},
        "scope": {"type": "string", "enum": ["auto", "window"],
                  "description": "auto (default) = for Chrome/Edge list only the web page (whole page, "
                                 "including parts below the fold); window = every control incl. browser toolbar."},
    },
)
def ui_elements(window=None, filter=None, include_text=False, max_items=120, scope="auto"):
    _need()
    with _LOCK, auto.UIAutomationInitializerInThread():
        win = _woken(_window(window))
        want = _INTERACTIVE | (_TEXTY if include_text else set())
        doc = _web_doc(win) if scope != "window" else None
        if doc is not None:
            found = _walk(doc, want - {"DocumentControl"}, 1500, time.time() + 12, offscreen=True)
        else:
            found = _walk(win, want, 1500, time.time() + 12)
        if filter:
            f = filter.lower()
            found = [c for c in found if f in (c.Name or "").lower() or f in _value(c).lower()]
        # A list item wrapping a link of the same name is one thing to the reader - keep the link.
        found = [c for i, c in enumerate(found)
                 if not (c.ControlTypeName == "ListItemControl" and i + 1 < len(found)
                         and found[i + 1].ControlTypeName == "HyperlinkControl"
                         and _clean(found[i + 1].Name) == _clean(c.Name))]
        found = found[: max(1, int(max_items))]
        _LAST["hwnd"] = win.NativeWindowHandle
        _LAST["items"] = found
        view = doc.BoundingRectangle if doc is not None else None
        _LAST["view"] = view
        lines = [_describe(i, c, view) for i, c in enumerate(found)]
    head = f'Window: "{_clean(win.Name)}"' + (" (web page only)" if doc is not None else "")
    head += f" - {len(lines)} items" + (f" matching {filter!r}" if filter else "")
    if not lines:
        head += ". Nothing found: the app may not expose its controls - use a screenshot instead."
    return {"text": head + "\n" + "\n".join(lines)}


def _resolve(target, window, kinds=None):
    """Number from the last listing, or a name (exact match first, then contains)."""
    if isinstance(target, int) or (isinstance(target, str) and target.strip().isdigit()):
        idx = int(target)
        items = _LAST["items"]
        if not 0 <= idx < len(items):
            raise RuntimeError(f"No item [{idx}] in the last ui_elements list ({len(items)} items).")
        return items[idx]
    name = str(target).strip().lower()
    win = _woken(_window(window))
    kinds = kinds or (_INTERACTIVE | _TEXTY)
    pool = _walk(win, kinds, 2500, time.time() + 12)
    doc = _web_doc(win)
    if doc is not None:
        pool += _walk(doc, kinds, 2500, time.time() + 12, offscreen=True)
    # Prefer real controls (button/link/edit) over the list item or label wrapping them.
    rank = {"ButtonControl": 0, "HyperlinkControl": 0, "EditControl": 0, "MenuItemControl": 0,
            "CheckBoxControl": 0, "RadioButtonControl": 0, "TabItemControl": 0, "ComboBoxControl": 0}
    exact = [c for c in pool if _clean(c.Name).strip().lower() == name]
    if exact:
        return sorted(exact, key=lambda c: rank.get(c.ControlTypeName, 1))[0]
    part = sorted([c for c in pool if name in _clean(c.Name).lower()],
                  key=lambda c: rank.get(c.ControlTypeName, 1))
    if part:
        return part[0]
    raise RuntimeError(f"No control named like '{target}'. Run ui_elements to see what is there.")


def _prepare(ctrl):
    """Bring the control's window to the front and scroll the control into view."""
    top = ctrl.GetTopLevelControl()
    try:
        if top is not None and top.NativeWindowHandle != auto.GetForegroundWindow():
            top.SetActive()
            time.sleep(0.3)
    except Exception:  # noqa: BLE001
        pass
    doc = _web_doc(top) if top is not None else None
    view = doc.BoundingRectangle if doc is not None else None
    if _offscreen(ctrl, view):
        try:
            ctrl.GetScrollItemPattern().ScrollIntoView()
            time.sleep(0.5)
        except Exception:  # noqa: BLE001
            pass
    return view


@tool(
    "ui_click",
    "Click a control by its number from the last ui_elements list, or by its visible name "
    "(e.g. 'Apply now', 'Send', 'Save'). No screenshot or coordinates needed.",
    {
        "target": {"type": "string", "description": "Item number from ui_elements, or the control's name."},
        "window": {"type": "string", "description": "Part of the window title when using a name. Omit = foreground."},
        "double": {"type": "boolean", "description": "Double-click. Default false."},
        "then_wait": {"type": "number", "description": "Seconds to wait afterwards (max 30)."},
    },
    required=["target"],
)
def ui_click(target, window=None, double=False, then_wait=0):
    _need()
    with _LOCK, auto.UIAutomationInitializerInThread():
        ctrl = _resolve(target, window)
        view = _prepare(ctrl)
        label = _describe("*", ctrl, view)
        # A real mouse click behaves like a person (menus, React handlers); Invoke is the
        # fallback when the control still cannot be brought on screen.
        if not _offscreen(ctrl, view):
            ctrl.Click(simulateMove=False, waitTime=0.1) if not double else ctrl.DoubleClick(simulateMove=False, waitTime=0.1)
            how = "clicked"
        else:
            pattern = ctrl.GetInvokePattern()
            if not pattern:
                raise RuntimeError(f"{label} is off screen and cannot be invoked - scroll to it first.")
            pattern.Invoke()
            how = "invoked"
    if then_wait:
        time.sleep(min(float(then_wait), 30))
    return {"text": f"{how} {label}"}


@tool(
    "ui_type",
    "Put text into an edit box / text area found by number (from ui_elements) or by name or "
    "placeholder. Replaces the current content unless append=true. Handles Urdu and long text.",
    {
        "target": {"type": "string", "description": "Item number from ui_elements, or the box's name."},
        "text": {"type": "string", "description": "Text to enter."},
        "window": {"type": "string", "description": "Part of the window title. Omit = foreground."},
        "append": {"type": "boolean", "description": "Add to the end instead of replacing. Default false."},
        "press_enter": {"type": "boolean", "description": "Press Enter afterwards. Default false."},
    },
    required=["target", "text"],
)
def ui_type(target, text, window=None, append=False, press_enter=False):
    _need()
    import pyperclip

    with _LOCK, auto.UIAutomationInitializerInThread():
        ctrl = _resolve(target, window, {"EditControl", "DocumentControl", "ComboBoxControl"})
        view = _prepare(ctrl)
        label = _describe("*", ctrl, view)
        done = False
        # ValuePattern is instant and exact, but rich web editors (React) ignore it, so it is
        # only trusted for plain single-line boxes; otherwise click + paste like a person.
        if not append and ctrl.ControlTypeName == "EditControl":
            try:
                pattern = ctrl.GetValuePattern()
                if pattern and not pattern.IsReadOnly and "\n" not in text:
                    pattern.SetValue(text)
                    done = _value(ctrl) == text
            except Exception:  # noqa: BLE001
                done = False
        if not done:
            ctrl.Click(simulateMove=False, waitTime=0.1)
            if not append:
                auto.SendKeys("{Ctrl}a", waitTime=0.05)
            else:
                auto.SendKeys("{Ctrl}{End}", waitTime=0.05)
            old = None
            try:
                old = pyperclip.paste()
            except Exception:  # noqa: BLE001
                pass
            pyperclip.copy(text)
            auto.SendKeys("{Ctrl}v", waitTime=0.2)
            if old is not None:
                try:
                    pyperclip.copy(old)
                except Exception:  # noqa: BLE001
                    pass
        if press_enter:
            auto.SendKeys("{Enter}", waitTime=0.1)
    return {"text": f"typed {len(text)} chars into {label}"}


@tool(
    "read_page",
    "Read all the text of a window or web page (Chrome/Edge page, document, app) as plain text "
    "without screenshots, scrolling or the clipboard. Use it to read job lists, emails, chats, "
    "search results, forms. Returns up to max_chars.",
    {
        "window": {"type": "string", "description": "Part of the window title. Omit = foreground."},
        "max_chars": {"type": "integer", "description": "Default 20000."},
    },
)
def read_page(window=None, max_chars=20000):
    _need()
    with _LOCK, auto.UIAutomationInitializerInThread():
        win = _woken(_window(window))
        text = ""
        # Web pages: the DocumentControl's TextPattern gives the whole page in reading order.
        doc = _web_doc(win)
        try:
            if doc is not None:
                pattern = doc.GetTextPattern()
                if pattern:
                    text = pattern.DocumentRange.GetText(-1) or ""
        except Exception:  # noqa: BLE001
            text = ""
        if not text.strip():
            parts = []
            root = doc if doc is not None else win
            for c in _walk(root, _INTERACTIVE | _TEXTY, 4000, time.time() + 15, offscreen=doc is not None):
                name = (c.Name or "").strip()
                if name and (not parts or parts[-1] != name):
                    parts.append(name)
            text = "\n".join(parts)
        title = _clean(win.Name)
    # U+FFFC marks images/embedded objects in web text - pure noise for reading.
    text = text.replace("\r", "").replace("￼", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    limit = max(500, int(max_chars))
    more = f"\n... [{len(text) - limit} more chars]" if len(text) > limit else ""
    return {"text": f'Window: "{title}" ({len(text)} chars)\n{text[:limit]}{more}'}
