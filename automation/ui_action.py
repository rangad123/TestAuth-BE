import pyautogui
import json
import requests
import os
import time
import sys
import pygetwindow as gw
import subprocess
import traceback
from django.http import JsonResponse
from django.conf import settings
from .session_manager import user_sessions
from .omniparser_client import send_to_omniparser
from .screenshot_manager import take_screenshot
from .window_utils import disable_focus_stealing_prevention, activate_user_window, update_window_title


def perform_ui_action(user_id, action, element_name, click_X, click_Y, text):
    """Performs UI actions directly on the local machine with enhanced window activation"""
    # Debugging Logs
    print("=" * 50)
    print(f"[DEBUG] Action Requested: {action}")
    print(f"[DEBUG] User ID: {user_id}")
    print(f"[DEBUG] Element Name: {element_name}")
    print(f"[DEBUG] Click Coordinates: ({click_X}, {click_Y})")
    print("=" * 50)

    # Ensure foreground lock timeout is disabled
    if sys.platform == 'win32':
        disable_focus_stealing_prevention()

    # First, try to minimize all Chrome windows to handle fullscreen issues
    try:
        chrome_windows = gw.getWindowsWithTitle("Chrome")
        for window in chrome_windows:
            try:
                if window.isMaximized:
                    window.minimize()
                    time.sleep(0.2)
            except Exception as e:
                print(f"[WARN] Failed to minimize Chrome window: {e}")
    except Exception as e:
        print(f"[WARN] Failed to process Chrome windows: {e}")

    # Now activate the correct window with multiple attempts
    activation_success = False
    for attempt in range(3):  # Try up to 3 times
        if activate_user_window(user_id):
            activation_success = True
            break
        else:
            print(f"[WARN] Window activation attempt {attempt + 1} failed, retrying...")
            time.sleep(1)

    if not activation_success:
        # Emergency fallback: Try to use simulated Alt+Tab
        try:
            print("[INFO] Trying emergency Alt+Tab approach...")
            # Get all Chrome windows
            chrome_windows = [w for w in gw.getAllWindows() if 'Chrome' in w.title]
            if chrome_windows:
                # First minimize all to exit fullscreen
                for window in chrome_windows:
                    try:
                        window.minimize()
                        time.sleep(0.2)
                    except Exception as e:
                        print(f"[WARN] Failed to minimize: {e}")

                time.sleep(1)

                # Now try to restore and maximize the first Chrome window
                try:
                    chrome_windows[0].restore()
                    time.sleep(0.5)
                    chrome_windows[0].maximize()
                    time.sleep(0.5)
                    activation_success = True
                except Exception as e:
                    print(f"[ERROR] Failed to restore Chrome window: {e}")
        except Exception as e:
            print(f"[ERROR] Emergency activation failed: {e}")

    if not activation_success:
        return {"error": "Failed to locate and activate the correct browser window after multiple attempts"}

    # Update session activity
    if user_id in user_sessions:
        user_sessions[user_id]['last_active'] = time.time()
    else:
        user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}

    try:
        # Wait to ensure UI is stable - wait longer to ensure window is properly activated
        time.sleep(2)

        if action == 'click':
            # Try different clicking methods
            try:
                # First try standard click
                pyautogui.click(click_X, click_Y)
                time.sleep(1)
                print(f"[INFO] Clicked at position ({click_X}, {click_Y})")
            except Exception as e1:
                print(f"[WARN] Standard click failed: {e1}")


        elif action in ['type', 'enter']:
            # Try different clicking methods
            try:
                pyautogui.click(click_X, click_Y)
                time.sleep(0.5)
                pyautogui.write(text)
                print(f"[INFO] Typed '{text}' at position ({click_X}, {click_Y})")
            except Exception as e1:
                print(f"[WARN] Standard type failed: {e1}")

        else:
            return {"error": "Invalid action"}

        # Wait longer for any UI updates
        time.sleep(3)

        # Update the window title in our tracking
        print("[DEBUG] Updating window title after UI action")
        update_window_title(user_id)

        # Take screenshot after action
        screenshot_path, screenshot_url = take_screenshot(user_id, action)
        omniparser_response = send_to_omniparser(screenshot_path)

        if screenshot_path:
            return {
                "status": f"{action.capitalize()} performed on {element_name}",
                "screenshot": screenshot_url,
                "coordinates": omniparser_response
            }
        else:
            return {"error": "Failed to capture screenshot after action"}

    except Exception as e:
        print(f"[ERROR] Action failed: {e}")
        traceback.print_exc()
        return {"error": f"Action failed: {str(e)}"}