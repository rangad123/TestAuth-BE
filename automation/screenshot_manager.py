import os
import time
import pyautogui
from django.conf import settings
from .config import MEDIA_DIR
from .session_manager import user_sessions
import pygetwindow as gw
import traceback
import win32gui
import win32gui
import win32con
import win32api
import win32process
import ctypes
from ctypes import wintypes


def take_screenshot(user_id, context=""):
    """Capture a screenshot on the local machine"""
    try:
        timestamp = int(time.time())
        screenshot_filename = f"user_{user_id}_{timestamp}.png"
        screenshot_path = os.path.join(MEDIA_DIR, screenshot_filename)

        # Update session activity
        if user_id in user_sessions:
            user_sessions[user_id]['last_active'] = time.time()
        else:
            user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}

        # Wait briefly to ensure UI is stable
        time.sleep(5)

        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)

        time.sleep(2)

        if not os.path.exists(screenshot_path):
            raise FileNotFoundError("Screenshot not saved!")

        # Create URL for the screenshot
        screenshot_url = f"/media/screenshots/{screenshot_filename}?t={timestamp}"

        print(f"[INFO] Screenshot saved to {screenshot_path}")

        # Minimize the Chrome window after taking the screenshot
        active_window = gw.getActiveWindow()
        chrome_windows = [win for win in gw.getWindowsWithTitle("Google Chrome") if win is not None]

        if chrome_windows:
            hwnd = chrome_windows[0]._hWnd  # Get window handle
            time.sleep(1)  # Short delay before minimizing
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            print(f"[INFO] Minimized Chrome window: {chrome_windows[0].title}")
        else:
            print("[WARN] No active Chrome window found to minimize")

        return screenshot_path, screenshot_url
    except Exception as e:
        print(f"[ERROR] Failed to take screenshot: {e}")
        traceback.print_exc()
        return None, None


def Run_test_screenshot(user_id, context="", minimize_after=False):
    """
    Capture a screenshot on the local machine

    Parameters:
        user_id (str): The ID of the user
        context (str): Context information about the screenshot
        minimize_after (bool): Whether to minimize the window after taking the screenshot
    """
    try:
        timestamp = int(time.time())
        screenshot_filename = f"user_{user_id}_{timestamp}.png"
        screenshot_path = os.path.join(MEDIA_DIR, screenshot_filename)

        # Update session activity
        if user_id in user_sessions:
            user_sessions[user_id]['last_active'] = time.time()
        else:
            user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}

        # Wait briefly to ensure UI is stable
        time.sleep(5)

        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)

        time.sleep(2)

        if not os.path.exists(screenshot_path):
            raise FileNotFoundError("Screenshot not saved!")

        # Create URL for the screenshot
        screenshot_url = f"/media/screenshots/{screenshot_filename}?t={timestamp}"

        print(f"[INFO] Screenshot saved to {screenshot_path}")

        # In your take_screenshot() function:
        print(f"[DEBUG] Minimize after screenshot: {minimize_after}")

        if minimize_after:
            print("[INFO] This is the final step - will minimize window")
            time.sleep(1)  # Make sure screenshot is complete

            try:
                # Try multiple methods to minimize the window
                active_window = gw.getActiveWindow()
                if active_window:
                    print(f"[INFO] Minimizing active window: {active_window.title}")

                    # Method 1: Use pygetwindow
                    active_window.minimize()
                    time.sleep(0.5)

                    # Method 2: If that didn't work, try Win32 API directly
                    hwnd = active_window._hWnd
                    if hwnd:
                        print(f"[INFO] Using Win32 API to minimize window with handle: {hwnd}")
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                else:
                    print("[WARN] No active window found to minimize")

                    # Method 3: As last resort, try to minimize all Chrome windows
                    chrome_windows = [win for win in gw.getWindowsWithTitle("Chrome") if win is not None]
                    for win in chrome_windows:
                        print(f"[INFO] Minimizing Chrome window: {win.title}")
                        win.minimize()

            except Exception as e:
                print(f"[ERROR] Failed to minimize window: {e}")
                traceback.print_exc()

        return screenshot_path, screenshot_url
    except Exception as e:
        print(f"[ERROR] Failed to take screenshot: {e}")
        traceback.print_exc()
        return None, None


