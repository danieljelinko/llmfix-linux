#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "litellm",
#     "pynput",
#     "pyperclip",
#     "pillow",
#     "mss",
#     "pystray",
# ]
# ///
# Fork of AnswerDotAI/llmfix — Linux adaptation under Apache-2.0.
import os, time, pyperclip, threading, base64, logging, argparse
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from pynput.keyboard import Key, Controller, Listener
from pynput.mouse import Controller as MouseController
from litellm import completion
from mss import mss

try:
    import pystray
    HAVE_PYSTRAY = True
except Exception:
    HAVE_PYSTRAY = False

log = logging.getLogger(__name__)
kb = Controller()
mouse = MouseController()

GATEWAY_BASE = os.environ.get("AI_GATEWAY_URL", "http://127.0.0.1:4001/v1")  # 127.0.0.1, never localhost
MODEL        = os.environ.get("LLMFIX_MODEL", "claude-sonnet")

def gateway_model(model_id: str) -> str:
    "litellm route for a gateway model id: `openai/` prefix = OpenAI-compatible endpoint."
    return model_id if model_id.startswith("openai/") else f"openai/{model_id}"

CODES = {
    "//C": "// Correct the spelling and grammar and punctuation, but do not change the meaning of the text, keep the words style and input language as they are",
    "//CC": "// edit to be clear and concise",
    "//FR": "// edit to be friendly and informal",
    "//FO": "// edit to be formal and polite",
    "//BLUF": "// edit to bring the bottom line upfront",
    "//DOH": "// edit to fix typo's and spelling mistakes",
    "//HH": "// edit to fix typo's and spelling mistakes, do not translate into English keep the original language Hungarian",
    "//MD": "// transform to markdown",
    "//FS": "// make fastai style. concise, short var names, as much on one line as possible, but no `;`. Dont add ``python codefence.",
    "//PC": "// edit to be polite and friendly and orthographically correct",
    "//SS": "",
}

def replace_all(txt, reps):
    for old, new in reps.items():
        txt = txt.replace(old, new)
    log.debug(f"Text after replacement: {txt[:100]}...")
    return txt

def resize_img(img, max_px=1_150_000):
    w, h = img.size
    px = w * h
    log.debug(f"Image size: {w}x{h} ({px} pixels)")
    if px <= max_px:
        log.debug("No resize needed")
        return img
    r = (max_px / px) ** 0.5
    nw, nh = int(w * r), int(h * r)
    log.debug(f"Resizing to: {nw}x{nh} (ratio: {r:.2f})")
    return img.resize((nw, nh), Image.LANCZOS)

def img_b64(img):
    buf = BytesIO()
    img.save(buf, format='PNG')
    enc = base64.b64encode(buf.getvalue()).decode('utf-8')
    log.debug(f"Encoded to base64 ({len(enc)} chars)")
    return enc

def get_mouse_pos():
    try:
        x, y = mouse.position
        return int(x), int(y)
    except Exception as e:
        log.warning(f"Mouse position unavailable: {e}")
        return None, None

def pick_monitor_for_pos(monitors, pos):
    if not monitors:
        return None
    mx, my = pos
    if mx is not None and my is not None:
        for m in monitors:
            if (m['left'] <= mx < m['left'] + m['width'] and
                m['top']  <= my < m['top'] + m['height']):
                return m
    return monitors[0]

def capture_screen():
    log.debug("Starting capture via mss")
    with mss() as sct:
        all_mon = sct.monitors
        mons = all_mon[1:] if len(all_mon) > 1 else all_mon
        mon = pick_monitor_for_pos(mons, get_mouse_pos())
        if mon is None:
            log.debug("No monitor found, defaulting to [0]")
            mon = all_mon[0]
        log.debug(f"Capturing monitor: {mon}")
        shot = sct.grab(mon)
        img = Image.frombytes('RGB', shot.size, shot.rgb)
        log.debug("Capture done")
        return img

def llm(inp: str):
    log.debug(f"LLM input ({len(inp)} chars): {inp[:100]}...")
    prompt = (
        "Below is the text a user copied to their clipboard along with a screenshot. "
        "It contains a mix of text and instructions for you to fix. "
        "Apply the fixes and return only the text that the user should see. "
        "It will be applied to their clipboard so they can paste it. "
        "If the user says something like // DO THIS you can be sure it's an instruction. "
        "RETURN ONLY THE OUTPUT, NO YAPPING. NO PREAMBLE NO SIGN OFF.\n"
        "<user text>\n"
        f"{replace_all(inp, CODES)}\n"
        "</user text>"
    ).strip()

    use_image = "//SS" in inp
    if use_image:
        log.info("Screenshot mode")
        ss = capture_screen()
        resized = resize_img(ss)
        content = [
            dict(type="text", text=prompt),
            dict(type="image_url", image_url=dict(url=f"data:image/png;base64,{img_b64(resized)}"))
        ]
        log.info(f"Using {MODEL} with screenshot")
    else:
        content = prompt
        log.debug(f"Using {MODEL}")

    try:
        log.debug(f"Sending to {GATEWAY_BASE}...")
        resp = completion(model=gateway_model(MODEL), messages=[dict(role="user", content=content)], api_base=GATEWAY_BASE, api_key="dummy")
        res = resp.choices[0].message.content
        log.debug(f"Response ({len(res)} chars): {res[:100]}...")
        return res
    except Exception as e:
        log.error(f"LLM failed: {e}")
        log.error(f"Is the ai-gateway up? Try: cd ../ai-gateway && just up   (or 'just heal-token' if the Claude token wedged)")
        raise

def copy_selection():
    with kb.pressed(Key.ctrl):
        kb.tap('c')
    time.sleep(0.1)

def paste_clipboard():
    with kb.pressed(Key.ctrl):
        kb.tap('v')
    time.sleep(0.1)

def check_clipboard_backend():
    try:
        old = pyperclip.paste()
        pyperclip.copy(old if old is not None else "")
        return True
    except pyperclip.PyperclipException as e:
        log.error(f"Clipboard backend not available: {e}")
        log.error("Install a clipboard helper: 'sudo apt install xclip' (X11) or 'sudo apt install wl-clipboard' (Wayland).")
        return False
    except Exception as e:
        log.error(f"Clipboard check failed: {e}")
        return False

def create_icon_image(size=64):
    img = Image.new('RGBA', (size, size), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)
    pad = 6
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=12, outline=(200, 200, 200, 255), width=2)
    try:
        font = ImageFont.load_default()
        text = "L"
        tw, th = draw.textsize(text, font=font)
        draw.text(((size - tw) // 2, (size - th) // 2), text, fill=(240, 240, 240, 255), font=font)
    except Exception:
        pass
    return img

class HotkeyListener:
    def __init__(self, cb, enable_caps_a: bool = True):
        self.cb, self.keys, self.listener = cb, set(), None
        self.enable_caps_a = enable_caps_a
        # Track Caps-as-prefix timing and state so we can treat "Caps then A" as a trigger
        self._caps_armed_until = 0.0
        self._caps_prev_state = False
        self._caps_state = False  # best-effort tracker; true means caps is logically on by our toggle count
        log.debug("HotkeyListener init")

    def start(self):
        log.debug("Starting listener")
        self.listener = Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

    def stop(self):
        log.debug("Stopping listener")
        if self.listener:
            self.listener.stop()

    def on_press(self, key):
        now = time.time()
        self.keys.add(key)

        # Built-in default hotkey: Ctrl+Alt+J
        if (Key.ctrl in self.keys and Key.alt in self.keys and
            hasattr(key, 'char') and key.char == 'j'):
            log.info("Hotkey detected! (Ctrl+Alt+J)")
            threading.Thread(target=self.cb, daemon=True).start()

        # Treat a quick "Caps then A" as a dedicated trigger without remapping
        if self.enable_caps_a:
            # Arm when Caps is pressed; use a short window where next 'a' triggers
            if key == Key.caps_lock:
                self._caps_prev_state = self._caps_state
                self._caps_state = not self._caps_state
                self._caps_armed_until = now + 0.5  # 500ms window
                log.debug("Caps pressed; arming Caps+A window")

            # If armed and next key is 'a' or 'A', trigger and clean up side-effects
            if (self._caps_armed_until and now <= self._caps_armed_until and
                hasattr(key, 'char') and key.char and key.char.lower() == 'a'):
                log.info("Hotkey detected! (Caps then A)")
                threading.Thread(target=self.cb, daemon=True).start()

                # Restore Caps state to what it was before the press, if it changed
                if self._caps_state != self._caps_prev_state:
                    try:
                        kb.tap(Key.caps_lock)
                        self._caps_state = self._caps_prev_state
                        log.debug("Restored CapsLock state")
                    except Exception:
                        pass

                # Best-effort: remove the typed 'a' from the focused app
                def _cleanup_typed_a():
                    try:
                        time.sleep(0.03)
                        kb.tap(Key.backspace)
                    except Exception:
                        pass

                threading.Thread(target=_cleanup_typed_a, daemon=True).start()
                self._caps_armed_until = 0.0

    def on_release(self, key):
        self.keys.discard(key)

class ToolbarApp:
    def __init__(self, use_tray=True, enable_caps_a=True):
        self.hotkey = HotkeyListener(self.fix, enable_caps_a=enable_caps_a)
        self._icon = None
        self.use_tray = use_tray and HAVE_PYSTRAY
        self._stop = threading.Event()
        if not HAVE_PYSTRAY and use_tray:
            log.warning("pystray not available; running hotkey-only mode")

    def _build_tray(self):
        if not self.use_tray:
            return None
        menu = pystray.Menu(
            pystray.MenuItem("Fix", self._on_tray_fix),
            pystray.MenuItem("Quit", self._on_tray_quit)
        )
        icon = pystray.Icon("llmfix", icon=create_icon_image(), title="LLMFix", menu=menu)
        return icon

    def _on_tray_fix(self, icon, item):
        self.fix()

    def _on_tray_quit(self, icon, item):
        log.info("Quit requested from tray")
        self._stop.set()
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def run(self):
        log.info("Starting app (Linux)")
        self.hotkey.start()
        try:
            if self.use_tray:
                self._icon = self._build_tray()
                t = threading.Thread(target=self._icon.run, daemon=True)
                t.start()
            while not self._stop.is_set():
                time.sleep(0.2)
        except KeyboardInterrupt:
            log.info("Keyboard interrupt, exiting")
        finally:
            self.hotkey.stop()
            if self._icon:
                try:
                    self._icon.stop()
                except Exception:
                    pass

    def fix(self, _=None):
        log.info("Fix called")
        old = pyperclip.paste() or ""
        log.debug(f"Saved clipboard ({len(old)} chars))")

        log.debug("Copying with Ctrl+C")
        copy_selection()

        inp = pyperclip.paste() or ""
        if not inp:
            log.warning("No input")
            pyperclip.copy(old)
            return

        log.debug(f"Got input ({len(inp)} chars): {inp[:100]}...")
        try:
            res = llm(inp)
        except Exception as e:
            log.error(f"Error: {e}; leaving selection untouched")
            pyperclip.copy(old)
            return

        log.debug("LLM done, copying result")
        pyperclip.copy(res)

        log.debug("Pasting with Ctrl+V")
        paste_clipboard()

        log.debug("Restoring clipboard")
        pyperclip.copy(old)
        log.info("Fix done")

def setup_logging(lvl):
    level = getattr(logging, lvl.upper())
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    log.setLevel(level)

def main():
    p = argparse.ArgumentParser(description='LLM Fix (Linux)')
    p.add_argument('--log-level', '-l', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    # Keep legacy --tray arg for compatibility, but add --no-tray to force-disable
    p.add_argument('--tray', action='store_true', help='Enable system tray (default if pystray available)', default=True)
    p.add_argument('--no-tray', action='store_true', help='Disable system tray entirely', default=False)
    p.add_argument('--disable-caps-a', action='store_true', help='Disable built-in Caps then A quick trigger', default=False)
    args = p.parse_args()

    setup_logging(args.log_level)
    if not check_clipboard_backend():
        log.warning("Clipboard backend not ready; operations may fail until you install xclip or wl-clipboard.")
    log.info("Starting llmfix (Linux)")
    use_tray = (not args.no_tray) and args.tray
    ToolbarApp(use_tray=use_tray, enable_caps_a=(not args.disable_caps_a)).run()

if __name__ == "__main__":
    main()
