import pyautogui
import pyperclip
import json
import requests
import os
import re
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
            

        elif action == 'scroll_up':
            try:
                pyautogui.scroll(500)
                time.sleep(1)
                print("[INFO] Scrolled Up success")
            except:
                print("[warn] Scroll_up failed")


        elif action == 'scroll_down':
            try:
                pyautogui.scroll(-500)
                time.sleep(1)
                print("[INFO] Scrolled Down success")
            except:
                print("[Warn] Scrolled Down failed")


        elif action == 'verify': 
            try:

                word_count = len(element_name.split())
                click_type = 3 if word_count > 1 else 2

                pyautogui.click(click_X, click_Y, clicks=click_type)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                copied_text = pyperclip.paste().strip()

                # Normalization functions
                def normalize(text):
                    return re.sub(r'\s+', ' ', text.strip().lower())

                def remove_spaces(text):
                    return re.sub(r'\s+', '', text.lower())

                normalized_element = normalize(element_name)
                normalized_copied = normalize(copied_text)
                no_space_element = remove_spaces(element_name)
                no_space_copied = remove_spaces(copied_text)

                passed = (normalized_copied == normalized_element or no_space_copied == no_space_element)

                if passed:
                    print(f"[success] Verified Successfully for: {element_name}, copied text is : {copied_text}")
                else:
                    print(f"[Warn] {element_name} Not found in the Screen")
            except:
                print(f"[warn] verify command failed")


        elif action == 'get':
            try:

                word_count = len(element_name.split())
                click_type = 3 if word_count > 1 else 2

                pyautogui.click(click_X, click_Y, clicks=click_type)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                copied_text = pyperclip.paste().strip()


                # Wait longer for any UI updates
                time.sleep(3)

                # Update the window title in our tracking
                print("[DEBUG] Updating window title after UI action")
                update_window_title(user_id)

                # Take screenshot and get coordinates
                screenshot_path, screenshot_url = take_screenshot(user_id, action)
                omniparser_response = send_to_omniparser(screenshot_path)

                return {
                    "status": "success",
                    "copied_text": copied_text,
                    "screenshot": screenshot_url,
                    "coordinates": omniparser_response
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Get command failed: {e}"
                }

        else:
            return {"error": "Invalid action"}

        # Wait longer for any UI updates
        time.sleep(5)

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



#Test Execution runtime

def Execute_ui_action(user_id, action, element_name, click_X, click_Y, text, is_final_step=False):
    """
    Performs UI actions directly on the local machine with enhanced window activation

    Parameters:
        user_id (str): The ID of the user
        action (str): The action to perform (click, type, etc.)
        element_name (str): The name of the element to interact with
        click_X (int): The X-coordinate to click
        click_Y (int): The Y-coordinate to click
        text (str): The text to type (if applicable)
        is_final_step (bool): Whether this is the final step in a test sequence
    """
    # Debugging Logs
    print("=" * 50)
    print(f"[DEBUG] Action Requested: {action}")
    print(f"[DEBUG] User ID: {user_id}")
    print(f"[DEBUG] Element Name: {element_name}")
    print(f"[DEBUG] Click Coordinates: ({click_X}, {click_Y})")
    print(f"[DEBUG] Is Final Step: {is_final_step}")
    print("=" * 50)

    # Ensure foreground lock timeout is disabled
    if sys.platform == 'win32':
        disable_focus_stealing_prevention()

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

        elif action == 'scroll_up':
            try:
                pyautogui.scroll(500)
                time.sleep(1)
                print("[INFO] Scrolled Up success")
            except:
                print("[warn] Scroll_up failed")

        elif action == 'scroll_down':
            try:
                pyautogui.scroll(-500)
                time.sleep(1)
                print("[INFO] Scrolled Down success")
            except:
                print("[Warn] Scrolled Down failed")

        elif action == 'verify':
            try:
                word_count = len(element_name.split())
                click_type = 3 if word_count > 1 else 2

                pyautogui.click(click_X, click_Y, clicks=click_type)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                copied_text = pyperclip.paste().strip()

                # Normalization functions
                def normalize(text):
                    return re.sub(r'\s+', ' ', text.strip().lower())

                def remove_spaces(text):
                    return re.sub(r'\s+', '', text.lower())

                normalized_element = normalize(element_name)
                normalized_copied = normalize(copied_text)
                no_space_element = remove_spaces(element_name)
                no_space_copied = remove_spaces(copied_text)

                passed = (normalized_copied == normalized_element or no_space_copied == no_space_element)

                if passed:
                    print(f"[success] Verified Successfully for: {element_name}, copied text is : {copied_text}")
                else:
                    print(f"[Warn] {element_name} Not found in the Screen")
            except:
                print(f"[warn] verify command failed")

        elif action == 'get':
            try:
                word_count = len(element_name.split())
                click_type = 3 if word_count > 1 else 2

                pyautogui.click(click_X, click_Y, clicks=click_type)
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                copied_text = pyperclip.paste().strip()

                # Wait longer for any UI updates
                time.sleep(3)

                # Update the window title in our tracking
                print("[DEBUG] Updating window title after UI action")
                update_window_title(user_id)

                # Take screenshot and get coordinates - only minimize on final step
                screenshot_path, screenshot_url = take_screenshot(user_id, action, minimize_after=is_final_step)
                print(f"[DEBUG] After screenshot - minimize_after was: {is_final_step}")
                return {
                    "status": "success",
                    "copied_text": copied_text,
                    "screenshot": screenshot_url
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Get command failed: {e}"
                }

        else:
            return {"error": "Invalid action"}

        # Wait longer for any UI updates
        time.sleep(5)

        # Update the window title in our tracking
        print("[DEBUG] Updating window title after UI action")
        update_window_title(user_id)

        # Take screenshot after action - only minimize on final step
        screenshot_path, screenshot_url = take_screenshot(user_id, action, minimize_after=is_final_step)

        if screenshot_path:
            return {
                "status": f"{action.capitalize()} performed on {element_name}",
                "screenshot": screenshot_url,
            }
        else:
            return {"error": "Failed to capture screenshot after action"}

    except Exception as e:
        print(f"[ERROR] Action failed: {e}")
        traceback.print_exc()
    return {"error": f"Action failed: {str(e)}"}
