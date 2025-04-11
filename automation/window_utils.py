from django.shortcuts import render
import sys
import os
import time
import pyautogui
import subprocess
import json
import requests
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import cv2
import traceback
import pygetwindow as gw
import random
import pygetwindow as gw
import ctypes
import win32gui
import win32api
import win32con
import win32process
import sys
from .session_manager import user_sessions

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


def get_chrome_windows():
    """Get all Chrome windows currently open with additional metadata"""
    chrome_windows = []

    for w in gw.getAllWindows():
        # Better Chrome window detection - make sure it's actually Chrome
        if 'Chrome' in w.title and ('Claude' not in w.title or 'chrome' in w.title.lower()):
            window_info = {
                'window': w,
                'title': w.title,
                'pid': None,
                'hwnd': None,
                'isMaximized': w.isMaximized
            }

            # For Windows, get process ID and window handle
            if sys.platform == 'win32':
                try:
                    hwnd = w._hWnd
                    window_info['hwnd'] = hwnd

                    # Get process ID
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    window_info['pid'] = pid.value

                    # Add creation time to help differentiate windows
                    window_info['creation_time'] = time.time()
                except Exception as e:
                    print(f"[WARN] Failed to get window metadata: {e}")

            chrome_windows.append(window_info)

    return chrome_windows

def disable_focus_stealing_prevention():
    """Attempts to disable focus stealing prevention temporarily"""
    if sys.platform == 'win32':
        try:
            # Try to set foreground lock timeout to 0 (disable)
            result = user32.SystemParametersInfoW(
                SPI_SETFOREGROUNDLOCKTIMEOUT,
                0,
                ctypes.c_void_p(0),  # Setting to 0 means no timeout
                SPIF_SENDCHANGE
            )
            if result:
                print("[INFO] Successfully disabled focus stealing prevention")
                return True
            else:
                print("[WARN] Failed to disable focus stealing prevention")
                return False
        except Exception as e:
            print(f"[ERROR] Error disabling focus stealing prevention: {e}")
            return False
    return False


def enum_windows_proc(hwnd, results):
    """Callback for EnumWindows to find windows by PID"""
    try:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        # Check if window is visible
        if user32.IsWindowVisible(hwnd) and pid.value in results['target_pids']:
            # Get window title
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buffer = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buffer, length)
            title = buffer.value

            if title:
                results['windows'].append({
                    'hwnd': hwnd,
                    'title': title,
                    'pid': pid.value
                })
    except Exception as e:
        print(f"[WARN] Error in enum_windows_proc: {e}")
    return True


def find_chrome_windows_by_pid(pids):
    """Find Chrome windows by their process IDs"""
    if not sys.platform == 'win32':
        return []

    results = {'windows': [], 'target_pids': pids}
    enum_windows_proc_callback = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, ctypes.py_object
    )(enum_windows_proc)

    try:
        user32.EnumWindows(enum_windows_proc_callback, ctypes.py_object(results))
    except Exception as e:
        print(f"[ERROR] Failed to enumerate windows: {e}")

    return results['windows']


def bring_process_to_foreground(pid=None, hwnd=None):
    """Force a window to foreground using advanced techniques"""
    if not sys.platform == 'win32':
        return False

    if not (pid or hwnd):
        return False

    try:
        # If we have a handle, use it directly
        if hwnd:
            target_hwnd = hwnd
        # Otherwise, find windows by PID
        elif pid:
            windows = find_chrome_windows_by_pid([pid])
            if not windows:
                return False
            target_hwnd = windows[0]['hwnd']

        # Check if window exists and is visible
        if not (user32.IsWindow(target_hwnd) and user32.IsWindowVisible(target_hwnd)):
            return False

        # Try multiple techniques to bring window to foreground

        # 1. First technique: Simulate Alt+Tab behavior
        curr_thread = win32api.GetCurrentThreadId()
        fore_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)

        # Attach input if different threads
        if curr_thread != fore_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, True)

        # Show window if minimized
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)

        # Set foreground window
        result = user32.SetForegroundWindow(target_hwnd)

        # Set active window
        user32.SetActiveWindow(target_hwnd)

        # Give it focus
        user32.SetFocus(target_hwnd)

        # Detach threads if needed
        if curr_thread != fore_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, False)

        # 2. Second technique: Minimize and restore the window
        if not result:
            win32gui.ShowWindow(target_hwnd, win32con.SW_MINIMIZE)
            time.sleep(0.2)
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
            user32.SetForegroundWindow(target_hwnd)

        # 3. Third technique: Try BringWindowToTop
        if not result:
            user32.BringWindowToTop(target_hwnd)
            user32.SetForegroundWindow(target_hwnd)

        # Verify success
        time.sleep(0.5)
        active_hwnd = user32.GetForegroundWindow()
        if active_hwnd == target_hwnd:
            return True
        else:
            print(f"[WARN] Window activation failed. Current={active_hwnd}, Target={target_hwnd}")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to bring process to foreground: {e}")
        return False


def activate_window(window_info):
    """Activate a window using advanced techniques"""
    if not window_info:
        return False

    # Extract necessary information
    title = window_info.get('title')
    hwnd = window_info.get('hwnd')
    pid = window_info.get('pid')
    window_obj = window_info.get('window')

    print(f"[INFO] Attempting to activate window: {title}, PID: {pid}, Handle: {hwnd}")

    # For Windows, use advanced techniques
    if sys.platform == 'win32':
        # Disable focus stealing prevention
        disable_focus_stealing_prevention()

        # Try using direct Windows API approach first (most reliable)
        if hwnd:
            try:
                # Get thread IDs
                foreground_hwnd = user32.GetForegroundWindow()
                curr_thread = win32api.GetCurrentThreadId()
                fore_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)

                # Attach thread input to bypass focus restrictions
                attached = False
                if curr_thread != fore_thread:
                    attached = user32.AttachThreadInput(curr_thread, fore_thread, True)
                    if attached:
                        print("[INFO] Successfully attached thread input")

                try:
                    # Step 1: Change window state to reset any fullscreen/maximized states
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.2)

                    # Step 2: Give window focus using multiple methods
                    user32.BringWindowToTop(hwnd)
                    result = user32.SetForegroundWindow(hwnd)
                    user32.SetActiveWindow(hwnd)
                    user32.SetFocus(hwnd)

                    # Step 3: If needed, use the LockSetForegroundWindow override
                    if not result:
                        user32.LockSetForegroundWindow(0)  # 0 = LSFW_UNLOCK
                        user32.SetForegroundWindow(hwnd)

                    # Step 4: Handle maximized state if it was maximized
                    if window_info.get('isMaximized'):
                        time.sleep(0.2)
                        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

                    # Verify success
                    time.sleep(0.5)
                    active_hwnd = user32.GetForegroundWindow()
                    if active_hwnd == hwnd:
                        print(f"[INFO] Successfully activated window using hwnd: {title}")
                        return True
                    else:
                        print(f"[WARN] Direct activation failed. Current={active_hwnd}, Target={hwnd}")
                finally:
                    # Always detach threads if attached
                    if attached:
                        user32.AttachThreadInput(curr_thread, fore_thread, False)
                        print("[INFO] Detached thread input")

                # Fallback: Try minimize-restore cycle only for the target window
                print("[INFO] Trying minimize-restore cycle...")
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                time.sleep(0.5)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.3)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)

                # Check if window is now active
                active_hwnd = user32.GetForegroundWindow()
                if active_hwnd == hwnd:
                    print(f"[INFO] Successfully activated window using minimize-restore: {title}")
                    return True

            except Exception as e:
                print(f"[ERROR] Failed to activate with hwnd: {e}")
                traceback.print_exc()

        # Try using pygetwindow as backup
        if window_obj:
            try:
                # Try direct activation first
                window_obj.activate()
                time.sleep(0.5)

                # Check if we succeeded
                active_window = gw.getActiveWindow()
                if active_window and active_window.title == title:
                    print(f"[INFO] Successfully activated window with direct pygetwindow: {title}")
                    return True

                # If not successful, try minimize-restore cycle only for this window
                print("[INFO] Direct pygetwindow activation failed, trying minimize-restore")
                window_obj.minimize()
                time.sleep(0.5)
                window_obj.restore()
                time.sleep(0.3)

                # If it was maximized, maximize it again
                if window_info.get('isMaximized'):
                    time.sleep(0.2)
                    window_obj.maximize()

                # Verify activation
                time.sleep(0.5)
                active_window = gw.getActiveWindow()
                if active_window and active_window.title == title:
                    print(f"[INFO] Successfully activated window with pygetwindow cycle: {title}")
                    return True
            except Exception as e:
                print(f"[ERROR] Failed to activate with pygetwindow: {e}")
                traceback.print_exc()

        # As a last resort, try simulated key presses
        try:
            # Simulate Alt+Tab press
            print("[INFO] Trying Alt+Tab technique...")
            pyautogui.keyDown('alt')
            time.sleep(0.1)
            pyautogui.press('tab')
            time.sleep(0.5)
            pyautogui.keyUp('alt')
            time.sleep(0.5)

            # Check if we got lucky
            active_window = gw.getActiveWindow()
            if active_window and (title in active_window.title):
                print(f"[INFO] Successfully activated with Alt+Tab: {active_window.title}")
                return True

            # One more extreme measure - try Windows+D to show desktop then Alt+Tab
            print("[INFO] Trying Windows+D then Alt+Tab...")
            pyautogui.hotkey('win', 'd')
            time.sleep(0.5)
            pyautogui.keyDown('alt')
            time.sleep(0.1)
            pyautogui.press('tab')
            time.sleep(0.5)
            pyautogui.keyUp('alt')
            time.sleep(0.5)

            # Check again
            active_window = gw.getActiveWindow()
            if active_window and (title in active_window.title):
                print(f"[INFO] Successfully activated with Windows+D and Alt+Tab: {active_window.title}")
                return True
        except Exception as e:
            print(f"[ERROR] Keypress techniques failed: {e}")
            traceback.print_exc()

    print(f"[ERROR] All activation techniques failed for window: {title}")
    return False


def update_window_title(user_id, window_key=None):
    """Update stored window title after navigation actions"""
    if user_id not in user_sessions:
        print(f"[DEBUG] update_window_title: No session found for user {user_id}")
        return False

    session_data = user_sessions[user_id]

    # If no specific window_key is provided, use current_window
    if not window_key and 'current_window' in session_data:
        window_key = session_data['current_window']

    if not window_key or window_key not in session_data['windows']:
        print(f"[DEBUG] update_window_title: No valid window key found. Key: {window_key}")
        return False

    print(f"[DEBUG] Updating title for window key: {window_key}")
    print(f"[DEBUG] Original window title: {session_data['windows'][window_key]['exact_title']}")

    # Get current active window
    active_window = gw.getActiveWindow()
    if not active_window:
        print("[DEBUG] update_window_title: No active window found")
        return False

    # Update the stored title for this window
    window_info = session_data['windows'][window_key]
    window_info['exact_title'] = active_window.title
    window_info['title'] = active_window.title  # Update both title fields
    print(f"[DEBUG] Updated window title to: {active_window.title}")

    return True


import time

def activate_user_window(user_id, url=None):
    """Activate the correct window for a user's session based on window_key."""
    if user_id not in user_sessions:
        print(f"[INFO] Creating new session for user {user_id}")
        user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}

    session_data = user_sessions[user_id]
    windows = session_data.get('windows', {})
    chrome_windows = get_chrome_windows()  # Fetch all active Chrome windows

    print(f"[DEBUG] Available Chrome windows: {len(chrome_windows)}")
    for cw in chrome_windows:
        print(f"[DEBUG] Window: {cw.get('title', 'Unknown')}, PID: {cw.get('pid', 'Unknown')}")

    # Track checked windows to avoid duplicates
    checked_windows = set()

    print(f"[DEBUG] activate_user_window - User: {user_id}, URL: {url}")
    print(f"[DEBUG] All window keys for user: {list(windows.keys())}")

    # **Step 1: Activate Current Window (If Available)**
    if session_data.get('current_window') in windows:
        current_key = session_data['current_window']
        window_info = windows[current_key]

        for chrome_window in chrome_windows:
            if chrome_window.get('hwnd') == window_info.get('hwnd'):
                print(f"[INFO] Activating window using key: {current_key} -> {chrome_window.get('title')}")
                result = activate_window(chrome_window)
                if result:
                    window_info['last_activated'] = time.time()  # Update last active time
                    return True
                checked_windows.add(chrome_window.get('hwnd'))

    # **Step 2: Find and Activate the Correct Window Based on URL**
    if url:
        matching_keys = [k for k in windows.keys() if k.startswith(f"{url}_")]
        for key in sorted(matching_keys, key=lambda k: windows[k].get('last_activated', 0), reverse=True):
            window_info = windows[key]

            for chrome_window in chrome_windows:
                if chrome_window.get('hwnd') in checked_windows:
                    continue

                if chrome_window.get('hwnd') == window_info.get('hwnd'):
                    print(f"[INFO] Found exact match for URL {url}: {chrome_window.get('title')}")
                    result = activate_window(chrome_window)
                    if result:
                        session_data['current_window'] = key
                        window_info['last_activated'] = time.time()
                        return True
                    checked_windows.add(chrome_window.get('hwnd'))

    # **Step 3: Try Activating the Most Recently Used Window**
    sorted_keys = sorted(windows.keys(), key=lambda k: windows[k].get('last_activated', 0), reverse=True)
    for key in sorted_keys:
        window_info = windows[key]

        for chrome_window in chrome_windows:
            if chrome_window.get('hwnd') in checked_windows:
                continue

            if chrome_window.get('hwnd') == window_info.get('hwnd'):
                print(f"[INFO] Fallback activation using window key: {key} -> {chrome_window.get('title')}")
                result = activate_window(chrome_window)
                if result:
                    session_data['current_window'] = key
                    window_info['last_activated'] = time.time()
                    return True
                checked_windows.add(chrome_window.get('hwnd'))

    # **Step 4: Last Resort - Activate the First Available Chrome Window**
    for chrome_window in chrome_windows:
        if chrome_window.get('hwnd') not in checked_windows:
            print(f"[WARN] No exact match found, activating first available Chrome window: {chrome_window.get('title')}")
            return activate_window(chrome_window)

    print("[ERROR] No Chrome windows found for activation.")
    return False
