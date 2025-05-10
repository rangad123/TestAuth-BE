import os
import subprocess
import time
import sys
import traceback
import pygetwindow as gw
from django.http import JsonResponse
from django.conf import settings
import pyautogui
import random
from pywinauto import Desktop
from .window_utils import find_chrome_windows_by_pid, update_window_title
from .window_utils import get_chrome_windows, disable_focus_stealing_prevention
from .session_manager import user_sessions
from .config import BROWSER_PATH

if sys.platform == 'win32':
    import win32gui
    import win32con
    import win32api
    import win32process
    import ctypes
    from ctypes import wintypes

if sys.platform == 'win32':
    user32 = ctypes.windll.user32

    # Define required Windows constants and structures
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_INFORMATION = 0x0400

    # For Windows 10 focus assist override
    SPIF_SENDCHANGE = 0x0002
    SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001


def is_chrome_bookmarks_bar_visible(hwnd):
    try:
        app = Desktop(backend="uia")
        win = app.window(handle=int(hwnd))
        toolbar = win.child_window(control_type="ToolBar", title_re=".*Bookmarks.*")
        return toolbar.exists() and toolbar.is_visible()
    except Exception as e:
        print(f"[WARN] Bookmark detection failed: {e}")
        return False

def open_browser(user_id, url):
    """Opens a new Chrome browser window and tracks its title and process ID."""
    print(f"[INFO] Opening URL {url} for user {user_id}")

    if user_id not in user_sessions:
        user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}
    else:
        user_sessions[user_id]['last_active'] = time.time()

    initial_windows = get_chrome_windows()

    try:
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            disable_focus_stealing_prevention()

            process = subprocess.Popen([
                BROWSER_PATH,
                "--new-window",
                "--start-maximized",
                "--disable-session-crashed-bubble",
                "--disable-infobars",
                url
            ], startupinfo=startupinfo)
        else:
            process = subprocess.Popen([
                BROWSER_PATH,
                "--new-window",
                "--start-maximized",
                "--disable-session-crashed-bubble",
                "--disable-infobars",
                url
            ])

        time.sleep(7)

        all_new_windows = get_chrome_windows()
        print(f"[DEBUG] Initial windows: {len(initial_windows)}")
        print(f"[DEBUG] All windows after launch: {len(all_new_windows)}")

        new_windows = []
        for window in all_new_windows:
            is_new = not any(w['title'] == window['title'] for w in initial_windows)
            url_domain = url.split("//")[-1].split("/")[0]
            base_domain = url_domain.split(".")[0]
            has_domain = base_domain.lower() in window['title'].lower()

            if is_new or has_domain:
                new_windows.append(window)
                print(f"[DEBUG] Found potential window match: {window['title']}")

        if not new_windows:
            domain_windows = [w for w in all_new_windows
                              if 'Chrome' in w['title'] and base_domain.lower() in w['title'].lower()]
            if domain_windows:
                new_window = domain_windows[0]
            else:
                chrome_windows = [w for w in all_new_windows if 'Chrome' in w['title']]
                if chrome_windows:
                    new_window = chrome_windows[0]
                else:
                    print("[ERROR] No Chrome window detected.")
                    return False
        else:
            new_window = new_windows[0]

        window_key = f"{url}_{time.time()}"
        user_sessions[user_id]['windows'][window_key] = {
            'url': url,
            'title': new_window['title'],
            'exact_title': new_window['title'],
            'pid': new_window['pid'],
            'hwnd': new_window['hwnd'],
            'time_created': time.time(),
            'last_activated': time.time()
        }

        user_sessions[user_id]['current_window'] = window_key
        print(f"[INFO] Stored window info: Title={new_window['title']}, PID={new_window['pid']}")

        if sys.platform == 'win32' and new_window['hwnd']:
            try:
                win32gui.SetForegroundWindow(new_window['hwnd'])
                active_hwnd = user32.GetForegroundWindow()

                if active_hwnd == new_window['hwnd']:
                    print(f"[INFO] Successfully activated new window: {new_window['title']}")
                else:
                    print(f"[WARN] Failed to activate new window")

                # ✅ Bookmark bar detection and hiding logic here
                if is_chrome_bookmarks_bar_visible(active_hwnd):
                    print("[INFO] Bookmarks bar is visible. Sending Ctrl+Shift+B to hide it.")
                    pyautogui.hotkey('ctrl', 'shift', 'b')
                    time.sleep(1)
                else:
                    print("[INFO] Bookmarks bar not visible or detection failed.")

            except Exception as e:
                print(f"[WARN] Failed to set focus or toggle bookmarks bar: {e}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to open Chrome: {e}")
        traceback.print_exc()
        return False