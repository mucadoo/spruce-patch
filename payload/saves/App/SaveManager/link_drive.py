"""Link Google Drive from the handheld.

The handheld has no browser. This shows a code the phone can scan. After you
sign in, Google sends the phone to a page that does not load, and the login
code is left in the address bar. You type that code here. link-gdrive.bat
does the same link from a PC and can still be used.
"""

import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timedelta, timezone

# rclone's published installed-app client. The rclone binary on the card uses
# the same id, with the secret stored scrambled. This is that secret.
CLIENT_ID = "202264815644.apps.googleusercontent.com"
CLIENT_SECRET = "X4Z3ca8xfWDb1Voo-F9a7ZxJ"
REDIRECT = "http://127.0.0.1:53682/"
SCOPE = "https://www.googleapis.com/auth/drive.file"


def link():
    """Ask for the code from the phone. True when the link is saved."""
    url = _auth_url()
    png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "link-qr.png")
    try:
        _write_qr(url, png)
        if not _show_qr(png):
            return False
        from display.on_screen_keyboard import OnScreenKeyboard

        typed = OnScreenKeyboard().get_input("Code, then Start")
        if not typed:
            return False
        _message(["Checking the code..."])
        token, problem = exchange(_extract_code(typed))
        if problem:
            _message(problem)
            _wait()
            return False
        _write_conf(token)
        _message(["Google Drive is linked."])
        _wait()
        return True
    finally:
        if os.path.isfile(png):
            try:
                os.remove(png)
            except OSError:
                pass


def _auth_url():
    query = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": secrets.token_urlsafe(9),
    })
    return "https://accounts.google.com/o/oauth2/auth?" + query


def _extract_code(text):
    text = (text or "").strip()
    if "code=" not in text:
        return text
    query = urllib.parse.urlparse(text).query if "://" in text else text.lstrip("?")
    found = urllib.parse.parse_qs(query).get("code")
    return found[0] if found else text


def exchange(code):
    """Turn the typed code into a token. Returns (token, None) or (None, lines)."""
    if not code:
        return None, ["Type the code from the address bar."]
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
    }).encode()
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            token = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        if "invalid_grant" in detail:
            return None, ["That code was not accepted.", "Scan the code and try again."]
        return None, ["Google did not accept the code."]
    except OSError:
        return None, ["Could not reach Google.", "Check Wi-Fi and try again."]
    if not token.get("refresh_token"):
        return None, ["Google did not finish the link.", "Scan the code and try again."]
    return token, None


def _write_conf(token):
    expires = int(token.get("expires_in") or 3600)
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires)).strftime(
        "%Y-%m-%dT%H:%M:%S.000000000Z")
    payload = {
        "access_token": token.get("access_token") or "",
        "token_type": token.get("token_type") or "Bearer",
        "refresh_token": token["refresh_token"],
        "expiry": expiry,
    }
    text = "[gdrive]\ntype = drive\nscope = drive.file\ntoken = %s\n" % json.dumps(
        payload, separators=(",", ":"))
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rclone.conf")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _write_qr(url, path):
    from qrcodegen import QrCode

    qr = QrCode.encode_text(url, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    scale = 4
    border = 2
    dim = (size + border * 2) * scale
    raw = bytearray()
    for y in range(dim):
        raw.append(0)
        module_y = y // scale - border
        for x in range(dim):
            module_x = x // scale - border
            dark = (
                0 <= module_x < size
                and 0 <= module_y < size
                and qr.get_module(module_x, module_y)
            )
            raw.append(0 if dark else 255)

    def chunk(tag, data):
        return (
            len(data).to_bytes(4, "big")
            + tag
            + data
            + (zlib.crc32(tag + data) & 0xFFFFFFFF).to_bytes(4, "big")
        )

    ihdr = dim.to_bytes(4, "big") + dim.to_bytes(4, "big") + bytes([8, 0, 0, 0, 0])
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(png)


def _show_qr(path):
    from controller.controller import Controller
    from controller.controller_inputs import ControllerInput
    from devices.device import Device
    from display.display import Display
    from display.font_purpose import FontPurpose
    from display.render_mode import RenderMode
    from themes.theme import Theme

    lines = [
        "Scan this with your phone and sign in.",
        "The next page will not load.",
        "Copy the text after code=.",
        "A types it here. B goes back.",
    ]
    Controller.clear_input_queue()
    while True:
        Display.clear("Link Google Drive")
        color = Theme.text_color(FontPurpose.LIST)
        y = Display.get_top_bar_height() + 6
        for line in lines:
            _width, height = Display.render_text(
                text=line,
                x=12,
                y=y,
                purpose=FontPurpose.LIST,
                color=color,
                render_mode=RenderMode.TOP_LEFT_ALIGNED,
            )
            y += height + 2
        Display.render_image(
            image_path=path,
            x=Device.get_device().screen_width() // 2,
            y=y + 4,
            render_mode=RenderMode.TOP_CENTER_ALIGNED,
            target_width=200,
            target_height=200,
        )
        Display.present()
        if not Controller.get_input():
            continue
        pressed = Controller.last_input()
        Controller.clear_last_input()
        if pressed == ControllerInput.A:
            return True
        if pressed == ControllerInput.B:
            return False


def _message(lines):
    from display.display import Display

    Display.display_message_multiline(lines)


def _wait():
    from controller.controller import Controller

    Controller.get_input()
    Controller.clear_input_queue()
