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
from .window_utils import find_chrome_windows_by_pid, update_window_title, get_chrome_windows, disable_focus_stealing_prevention
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


def open_browser(user_id, url):
    """Opens a new Chrome browser window and tracks its title and process ID."""
    print(f"[INFO] Opening URL {url} for user {user_id}")

    if user_id not in user_sessions:
        user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}
    else:
        user_sessions[user_id]['last_active'] = time.time()

    initial_windows = get_chrome_windows()

    try:
        # Create process with startupinfo to ensure it appears in foreground
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # startupinfo.wShowWindow = subprocess.SW_MAXIMIZE

            # Disable focus stealing prevention before starting Chrome
            disable_focus_stealing_prevention()

            # Launch Chrome with process priority
            process = subprocess.Popen([
                BROWSER_PATH,
                "--new-window",
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-infobars",
                "--disable-popup-blocking",
                "--disable-translate",
                "--disable-notifications",
                "--disable-sync",
                "--disable-component-update",
                "--guest",
                url
            ], startupinfo=startupinfo)
        else:
            # For non-Windows platforms
            process = subprocess.Popen([
                BROWSER_PATH,
                "--new-window",
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-infobars",
                "--disable-popup-blocking",
                "--disable-translate",
                "--disable-notifications",
                "--disable-sync",
                "--disable-component-update",
                "--guest",
                url
            ])

        # Wait longer for Chrome to launch (increased from 5 to 10 seconds)
        time.sleep(5)

        # Get new Chrome windows with detailed info
        all_new_windows = get_chrome_windows()

        # Log window information for debugging
        print(f"[DEBUG] Initial windows: {len(initial_windows)}")
        print(f"[DEBUG] All windows after launch: {len(all_new_windows)}")

        # More flexible window detection - consider both title and URL
        new_windows = []
        for window in all_new_windows:
            # Check if this window wasn't in the initial list
            is_new = not any(initial_w['title'] == window['title'] for initial_w in initial_windows)

            # Special case: sometimes Chrome reuses existing windows
            # Check if the URL domain is in the window title
            url_domain = url.split("//")[-1].split("/")[0]
            domain_parts = url_domain.split(".")
            base_domain = domain_parts[0] if len(domain_parts) > 0 else ""
            has_domain = base_domain.lower() in window['title'].lower()

            if is_new or has_domain:
                new_windows.append(window)
                print(f"[DEBUG] Found potential window match: {window['title']}")

        if not new_windows:
            # Enhanced fallback: Try to find window with URL domain in title
            url_domain = url.split("//")[-1].split("/")[0]
            domain_parts = url_domain.split(".")
            base_domain = domain_parts[0] if len(domain_parts) > 0 else ""

            # First, try to find Chrome windows with domain in title
            domain_windows = [w for w in all_new_windows
                              if 'Chrome' in w['title'] and base_domain.lower() in w['title'].lower()]

            # If domain windows found, use the most recently created one
            if domain_windows:
                print(f"[INFO] Found domain match window: {domain_windows[0]['title']}")
                new_window = domain_windows[0]
            else:
                # Look for any Chrome window that doesn't have "Claude" in the title
                chrome_windows = [w for w in all_new_windows
                                  if 'Chrome' in w['title'] and 'Claude' not in w['title']]

                if chrome_windows:
                    print(f"[INFO] Using Chrome window without domain match: {chrome_windows[0]['title']}")
                    new_window = chrome_windows[0]
                else:
                    # Last resort: use any Chrome window
                    chrome_windows = [w for w in all_new_windows if 'Chrome' in w['title']]
                    if chrome_windows:
                        print(f"[WARN] No better match found. Using fallback: {chrome_windows[0]['title']}")
                        new_window = chrome_windows[0]
                    else:
                        print("[ERROR] No Chrome window detected.")
                        return False

        else:
            new_window = new_windows[0]

        # Store detailed window information with more specifics
        window_key = f"{url}_{time.time()}"  # Using URL+timestamp as unique key
        print(f"[DEBUG] Generated unique window key: {window_key}")

        user_sessions[user_id]['windows'][window_key] = {
            'url': url,
            'title': new_window['title'],
            'exact_title': new_window['title'],  # Store the exact title
            'pid': new_window['pid'],
            'hwnd': new_window['hwnd'],
            'time_created': time.time(),
            'last_activated': time.time()
        }

        # Remember this as the current window
        user_sessions[user_id]['current_window'] = window_key
        print(f"[DEBUG] Set current_window to: {window_key}")

        print(f"[INFO] Stored window info: Title={new_window['title']}, PID={new_window['pid']} for URL {url}")

        # Try to set focus immediately after creation
        if sys.platform == 'win32' and new_window['hwnd']:
            try:
                # Try to activate window
                win32gui.SetForegroundWindow(new_window['hwnd'])

                # Check if activation was successful
                active_hwnd = user32.GetForegroundWindow()
                if active_hwnd == new_window['hwnd']:
                    print(f"[INFO] Successfully activated new window: {new_window['title']}")
                else:
                    print(f"[WARN] Failed to activate new window immediately")
            except Exception as e:
                print(f"[WARN] Failed to set focus on new window: {e}")

        return True
    except Exception as e:
        print(f"[ERROR] Failed to open Chrome: {e}")
        traceback.print_exc()
        return False



