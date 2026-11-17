"""Mouse and keyboard control - the agent literally drives the laptop."""

import time

from . import tool


IMG = {"type": "boolean",
       "description": "true = x/y are read straight off the LAST screenshot image (scaled/cropped); "
                      "they are converted to real screen pixels for you. Recommended."}
AFTER = {
    "then_wait": {"type": "number", "description": "Seconds to wait after the action (max 30). "
                                                    "Saves a separate wait call."},
    "then_screenshot": {"type": "boolean", "description": "Take a screenshot after the action (and "
                                                          "after then_wait) and return it. Saves a "
                                                          "separate screenshot call."},
}


def _xy(x, y, image_coords):
    if image_coords:
        from .screen import to_screen
        return to_screen(x, y)
    return int(x), int(y)


def _after(result, then_wait=None, then_screenshot=False):
    """Optional follow-up so one tool call can do action + wait + look."""
    if then_wait:
        time.sleep(max(0.0, min(float(then_wait), 30.0)))
    if then_screenshot:
        from .screen import capture
        shot = capture()
        result["text"] = result["text"] + " " + shot["text"]
        result["images"] = shot["images"]
        result["captions"] = shot["captions"]
        result["show"] = False
    return result


def _pyautogui():
    import pyautogui

    pyautogui.FAILSAFE = False  # the laptop is unattended; a corner-mouse abort is useless remotely
    pyautogui.PAUSE = 0.02      # was 0.05 - adds up badly over hundreds of actions
    return pyautogui


@tool(
    "type_text",
    "Put text into whatever window currently has focus. Long text is pasted instantly via the "
    "clipboard instead of typed letter by letter, so use this for whole prompts and paragraphs "
    "- it takes the same time whether it is 10 characters or 5000. Focus the right window first.",
    {
        "text": {"type": "string", "description": "The text to enter."},
        "press_enter": {"type": "boolean", "description": "Press Enter afterwards. Default false."},
        "force_typing": {
            "type": "boolean",
            "description": "Type character by character instead of pasting. Only for fields that "
                           "reject paste. Slow - avoid unless needed.",
        },
        **AFTER,
    },
    required=["text"],
)
def type_text(text, press_enter=False, force_typing=False, interval=0.01, then_wait=None,
              then_screenshot=False):
    return _after(_type_text(text, press_enter, force_typing, interval), then_wait, then_screenshot)


def _type_text(text, press_enter=False, force_typing=False, interval=0.01):
    try:
        pyautogui = _pyautogui()
    except Exception as exc:
        return {"text": f"pyautogui unavailable: {exc}"}

    body = str(text)

    # Typing a 3000-character prompt at 10ms/char is 30 seconds. Pasting is instant.
    if not force_typing and len(body) > 120:
        try:
            import pyperclip

            saved = ""
            try:
                saved = pyperclip.paste() or ""
            except Exception:  # noqa: BLE001
                pass

            pyperclip.copy(body)
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.25)
            if press_enter:
                pyautogui.press("enter")
            if saved:                      # put the owner's clipboard back
                try:
                    time.sleep(0.1)
                    pyperclip.copy(saved)
                except Exception:  # noqa: BLE001
                    pass
            return {"text": f"Pasted {len(body)} characters"
                            + (" and pressed Enter." if press_enter else ".")}
        except Exception as exc:  # noqa: BLE001 - fall back to typing
            print(f"[input] paste failed ({exc}), typing instead")

    pyautogui.write(body, interval=float(interval or 0.01))
    if press_enter:
        pyautogui.press("enter")
    return {"text": f"Typed {len(body)} characters" + (" and pressed Enter." if press_enter else ".")}


@tool(
    "press_keys",
    "Press a key or a keyboard shortcut. Examples: 'enter', 'esc', 'f5', 'ctrl+s', "
    "'ctrl+shift+esc', 'win+d', 'alt+tab', 'win+l'. Combine with + for chords.",
    {
        "keys": {"type": "string", "description": "Key or chord, e.g. ctrl+s"},
        "repeat": {"type": "integer", "description": "How many times. Default 1."},
        **AFTER,
    },
    required=["keys"],
)
def press_keys(keys, repeat=1, then_wait=None, then_screenshot=False):
    return _after(_press_keys(keys, repeat), then_wait, then_screenshot)


def _press_keys(keys, repeat=1):
    try:
        pyautogui = _pyautogui()
    except Exception as exc:
        return {"text": f"pyautogui unavailable: {exc}"}

    combo = [part.strip().lower() for part in str(keys).replace(" ", "").split("+") if part.strip()]
    if not combo:
        return {"text": "No keys given."}
    times = max(1, min(int(repeat or 1), 100))
    for _ in range(times):
        if len(combo) == 1:
            pyautogui.press(combo[0])
        else:
            pyautogui.hotkey(*combo)
        time.sleep(0.06)
    return {"text": f"Pressed {'+'.join(combo)} x{times}."}


@tool(
    "click",
    "Click the mouse. Easiest: set image_coords=true and give x/y exactly as seen in the last "
    "screenshot image - they are converted to real screen pixels for you (screenshots are "
    "scaled down). Without it, x/y must be real screen pixels. Use then_wait/then_screenshot to "
    "check the result in the same call.",
    {
        "x": {"type": "integer", "description": "X (screen pixels, or image pixels with image_coords)."},
        "y": {"type": "integer", "description": "Y (screen pixels, or image pixels with image_coords)."},
        "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Default left."},
        "clicks": {"type": "integer", "description": "1 for single, 2 for double. Default 1."},
        "image_coords": IMG,
        **AFTER,
    },
    required=["x", "y"],
)
def click(x, y, button="left", clicks=1, image_coords=False, then_wait=None, then_screenshot=False):
    try:
        pyautogui = _pyautogui()
    except Exception as exc:
        return {"text": f"pyautogui unavailable: {exc}"}

    sx, sy = _xy(x, y, image_coords)
    pyautogui.click(x=sx, y=sy, button=button or "left", clicks=int(clicks or 1), interval=0.1)
    where = f"screen ({sx}, {sy})" + (f" from image ({x}, {y})" if image_coords else "")
    return _after({"text": f"{button or 'left'}-clicked {clicks or 1}x at {where}."},
                  then_wait, then_screenshot)


@tool(
    "move_mouse",
    "Move the mouse pointer without clicking - useful for hovering to reveal menus or tooltips.",
    {
        "x": {"type": "integer"},
        "y": {"type": "integer"},
        "duration": {"type": "number", "description": "Seconds for the movement. Default 0.2."},
        "image_coords": IMG,
    },
    required=["x", "y"],
)
def move_mouse(x, y, duration=0.2, image_coords=False):
    try:
        pyautogui = _pyautogui()
    except Exception as exc:
        return {"text": f"pyautogui unavailable: {exc}"}

    x, y = _xy(x, y, image_coords)
    pyautogui.moveTo(x, y, duration=float(duration or 0.2))
    return {"text": f"Mouse moved to ({x}, {y})."}


@tool(
    "scroll",
    "Scroll the mouse wheel. Positive amount scrolls up, negative scrolls down.",
    {
        "amount": {"type": "integer", "description": "Wheel clicks, e.g. -5 to scroll down."},
        "x": {"type": "integer", "description": "Optional: move here before scrolling."},
        "y": {"type": "integer", "description": "Optional: move here before scrolling."},
        "image_coords": IMG,
        **AFTER,
    },
    required=["amount"],
)
def scroll(amount, x=None, y=None, image_coords=False, then_wait=None, then_screenshot=False):
    try:
        pyautogui = _pyautogui()
    except Exception as exc:
        return {"text": f"pyautogui unavailable: {exc}"}

    if x is not None and y is not None:
        pyautogui.moveTo(*_xy(x, y, image_coords))
    pyautogui.scroll(int(amount) * 120)
    return _after({"text": f"Scrolled {amount} clicks."}, then_wait, then_screenshot)


@tool(
    "drag",
    "Drag the mouse from one point to another with the button held down.",
    {
        "from_x": {"type": "integer"},
        "from_y": {"type": "integer"},
        "to_x": {"type": "integer"},
        "to_y": {"type": "integer"},
        "duration": {"type": "number", "description": "Seconds. Default 0.5."},
        "image_coords": IMG,
    },
    required=["from_x", "from_y", "to_x", "to_y"],
)
def drag(from_x, from_y, to_x, to_y, duration=0.5, image_coords=False):
    try:
        pyautogui = _pyautogui()
    except Exception as exc:
        return {"text": f"pyautogui unavailable: {exc}"}

    from_x, from_y = _xy(from_x, from_y, image_coords)
    to_x, to_y = _xy(to_x, to_y, image_coords)
    pyautogui.moveTo(from_x, from_y)
    pyautogui.dragTo(to_x, to_y, duration=float(duration or 0.5), button="left")
    return {"text": f"Dragged ({from_x}, {from_y}) -> ({to_x}, {to_y})."}


@tool(
    "wait",
    "Pause before the next action - for example while an app loads or a download finishes.",
    {"seconds": {"type": "number", "description": "How long to wait. Max 120."}},
    required=["seconds"],
)
def wait(seconds):
    duration = max(0.0, min(float(seconds), 120.0))
    time.sleep(duration)
    return {"text": f"Waited {duration:g}s."}
