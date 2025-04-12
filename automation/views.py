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
import re
import traceback
import replicate
import threading
import atexit
import pygetwindow as gw
import random
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .browser_manager import open_browser, update_window_title
from .screenshot_manager import take_screenshot
from .omniparser_client import send_to_omniparser
from .ui_action import perform_ui_action, Execute_ui_action
from .session_manager import user_sessions
from .window_utils import get_chrome_windows

if sys.platform == 'win32':
    import win32gui
    import win32con
    import win32api
    import win32process
    import ctypes
    from ctypes import wintypes

# # Windows path for Chrome - adjust based on typical installation path
# BROWSER_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# # For local testing, allow fallback to Windows path
# if not os.path.exists(BROWSER_PATH):
#     BROWSER_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
# # If still not found, try default path on macOS
# if not os.path.exists(BROWSER_PATH):
#     BROWSER_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# # Final fallback to Linux path
# if not os.path.exists(BROWSER_PATH):
#     BROWSER_PATH = "/usr/bin/google-chrome"

# MEDIA_DIR = os.path.join(settings.MEDIA_ROOT, "screenshots")
# os.makedirs(MEDIA_DIR, exist_ok=True)

# REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
# os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

# # Enhanced session tracking with window titles and process IDs
# user_sessions = {}  # {user_id: {'last_active': timestamp, 'windows': {url: {'title': window_title, 'hwnd': handle, 'pid': process_id}}}}
# SESSION_TIMEOUT = 600  # 10 minutes

# # Thread safety lock
# lock = threading.Lock()
# stop_event = threading.Event()  # Allows graceful stopping

# # Initialize user32 for Windows
# if sys.platform == 'win32':
#     user32 = ctypes.windll.user32

#     # Define required Windows constants and structures
#     PROCESS_SET_QUOTA = 0x0100
#     PROCESS_TERMINATE = 0x0001
#     PROCESS_QUERY_INFORMATION = 0x0400

#     # For Windows 10 focus assist override
#     SPIF_SENDCHANGE = 0x0002
#     SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001


def react_app(request, path=''):
    return render(request, 'index.html')


# def cleanup_inactive_sessions():
#     """Clean up inactive user sessions"""
#     current_time = time.time()
#     with lock:
#         for user_id, session_data in list(user_sessions.items()):
#             if current_time - session_data.get('last_active', 0) > SESSION_TIMEOUT:
#                 print(f"[INFO] Removing inactive session for user {user_id}")
#                 del user_sessions[user_id]


# def periodic_cleanup():
#     """Run cleanup periodically in the background"""
#     while not stop_event.is_set():
#         cleanup_inactive_sessions()
#         stop_event.wait(300)  # Wait 5 minutes between cleanups


# def stop_cleanup():
#     """Gracefully stop the cleanup thread"""
#     print("Stopping cleanup thread...")
#     stop_event.set()
#     cleanup_thread.join()


# # Start cleanup thread
# cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
# cleanup_thread.start()

# # Register cleanup function
# atexit.register(stop_cleanup)


# def get_chrome_windows():
#     """Get all Chrome windows currently open with additional metadata"""
#     chrome_windows = []

#     for w in gw.getAllWindows():
#         # Better Chrome window detection - make sure it's actually Chrome
#         if 'Chrome' in w.title and ('Claude' not in w.title or 'chrome' in w.title.lower()):
#             window_info = {
#                 'window': w,
#                 'title': w.title,
#                 'pid': None,
#                 'hwnd': None,
#                 'isMaximized': w.isMaximized
#             }

#             # For Windows, get process ID and window handle
#             if sys.platform == 'win32':
#                 try:
#                     hwnd = w._hWnd
#                     window_info['hwnd'] = hwnd

#                     # Get process ID
#                     pid = ctypes.c_ulong()
#                     user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
#                     window_info['pid'] = pid.value

#                     # Add creation time to help differentiate windows
#                     window_info['creation_time'] = time.time()
#                 except Exception as e:
#                     print(f"[WARN] Failed to get window metadata: {e}")

#             chrome_windows.append(window_info)

#     return chrome_windows


# def disable_focus_stealing_prevention():
#     """Attempts to disable focus stealing prevention temporarily"""
#     if sys.platform == 'win32':
#         try:
#             # Try to set foreground lock timeout to 0 (disable)
#             result = user32.SystemParametersInfoW(
#                 SPI_SETFOREGROUNDLOCKTIMEOUT,
#                 0,
#                 ctypes.c_void_p(0),  # Setting to 0 means no timeout
#                 SPIF_SENDCHANGE
#             )
#             if result:
#                 print("[INFO] Successfully disabled focus stealing prevention")
#                 return True
#             else:
#                 print("[WARN] Failed to disable focus stealing prevention")
#                 return False
#         except Exception as e:
#             print(f"[ERROR] Error disabling focus stealing prevention: {e}")
#             return False
#     return False


# def get_unique_profile_path(user_id):
#     """Generate a unique profile path for Chrome to prevent profile conflicts"""
#     random_suffix = str(random.randint(1000, 9999))
#     profile_dir = f"./chrome-user-{user_id}-{random_suffix}"
#     return profile_dir


# def open_browser(user_id, url):
#     """Opens a new Chrome browser window and tracks its title and process ID."""
#     print(f"[INFO] Opening URL {url} for user {user_id}")

#     if user_id not in user_sessions:
#         user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}
#     else:
#         user_sessions[user_id]['last_active'] = time.time()

#     initial_windows = get_chrome_windows()
#     profile_path = get_unique_profile_path(user_id)

#     try:
#         # Create process with startupinfo to ensure it appears in foreground
#         if sys.platform == 'win32':
#             startupinfo = subprocess.STARTUPINFO()
#             startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
#             # startupinfo.wShowWindow = subprocess.SW_MAXIMIZE

#             # Disable focus stealing prevention before starting Chrome
#             disable_focus_stealing_prevention()

#             # Launch Chrome with process priority
#             process = subprocess.Popen([
#                 BROWSER_PATH,
#                 f"--user-data-dir={profile_path}",
#                 "--new-window",
#                 "--start-maximized",
#                 "--disable-session-crashed-bubble",
#                 "--disable-infobars",
#                 url
#             ], startupinfo=startupinfo)
#         else:
#             # For non-Windows platforms
#             process = subprocess.Popen([
#                 BROWSER_PATH,
#                 f"--user-data-dir={profile_path}",
#                 "--new-window",
#                 "--start-maximized",
#                 "--disable-session-crashed-bubble",
#                 "--disable-infobars",
#                 url
#             ])

#         # Wait longer for Chrome to launch (increased from 5 to 10 seconds)
#         time.sleep(10)

#         # Get new Chrome windows with detailed info
#         all_new_windows = get_chrome_windows()

#         # Log window information for debugging
#         print(f"[DEBUG] Initial windows: {len(initial_windows)}")
#         print(f"[DEBUG] All windows after launch: {len(all_new_windows)}")

#         # More flexible window detection - consider both title and URL
#         new_windows = []
#         for window in all_new_windows:
#             # Check if this window wasn't in the initial list
#             is_new = not any(initial_w['title'] == window['title'] for initial_w in initial_windows)

#             # Special case: sometimes Chrome reuses existing windows
#             # Check if the URL domain is in the window title
#             url_domain = url.split("//")[-1].split("/")[0]
#             domain_parts = url_domain.split(".")
#             base_domain = domain_parts[0] if len(domain_parts) > 0 else ""
#             has_domain = base_domain.lower() in window['title'].lower()

#             if is_new or has_domain:
#                 new_windows.append(window)
#                 print(f"[DEBUG] Found potential window match: {window['title']}")

#         if not new_windows:
#             # Enhanced fallback: Try to find window with URL domain in title
#             url_domain = url.split("//")[-1].split("/")[0]
#             domain_parts = url_domain.split(".")
#             base_domain = domain_parts[0] if len(domain_parts) > 0 else ""

#             # First, try to find Chrome windows with domain in title
#             domain_windows = [w for w in all_new_windows
#                               if 'Chrome' in w['title'] and base_domain.lower() in w['title'].lower()]

#             # If domain windows found, use the most recently created one
#             if domain_windows:
#                 print(f"[INFO] Found domain match window: {domain_windows[0]['title']}")
#                 new_window = domain_windows[0]
#             else:
#                 # Look for any Chrome window that doesn't have "Claude" in the title
#                 chrome_windows = [w for w in all_new_windows
#                                   if 'Chrome' in w['title'] and 'Claude' not in w['title']]

#                 if chrome_windows:
#                     print(f"[INFO] Using Chrome window without domain match: {chrome_windows[0]['title']}")
#                     new_window = chrome_windows[0]
#                 else:
#                     # Last resort: use any Chrome window
#                     chrome_windows = [w for w in all_new_windows if 'Chrome' in w['title']]
#                     if chrome_windows:
#                         print(f"[WARN] No better match found. Using fallback: {chrome_windows[0]['title']}")
#                         new_window = chrome_windows[0]
#                     else:
#                         print("[ERROR] No Chrome window detected.")
#                         return False

#         else:
#             new_window = new_windows[0]

#         # Store detailed window information with more specifics
#         window_key = f"{url}_{time.time()}"  # Using URL+timestamp as unique key
#         print(f"[DEBUG] Generated unique window key: {window_key}")

#         user_sessions[user_id]['windows'][window_key] = {
#             'url': url,
#             'title': new_window['title'],
#             'exact_title': new_window['title'],  # Store the exact title
#             'pid': new_window['pid'],
#             'hwnd': new_window['hwnd'],
#             'time_created': time.time(),
#             'last_activated': time.time()
#         }

#         # Remember this as the current window
#         user_sessions[user_id]['current_window'] = window_key
#         print(f"[DEBUG] Set current_window to: {window_key}")

#         print(f"[INFO] Stored window info: Title={new_window['title']}, PID={new_window['pid']} for URL {url}")

#         # Try to set focus immediately after creation
#         if sys.platform == 'win32' and new_window['hwnd']:
#             try:
#                 # Try to activate window
#                 win32gui.SetForegroundWindow(new_window['hwnd'])

#                 # Check if activation was successful
#                 active_hwnd = user32.GetForegroundWindow()
#                 if active_hwnd == new_window['hwnd']:
#                     print(f"[INFO] Successfully activated new window: {new_window['title']}")
#                 else:
#                     print(f"[WARN] Failed to activate new window immediately")
#             except Exception as e:
#                 print(f"[WARN] Failed to set focus on new window: {e}")

#         return True
#     except Exception as e:
#         print(f"[ERROR] Failed to open Chrome: {e}")
#         traceback.print_exc()
#         return False

# def enum_windows_proc(hwnd, results):
#     """Callback for EnumWindows to find windows by PID"""
#     try:
#         pid = ctypes.c_ulong()
#         user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

#         # Check if window is visible
#         if user32.IsWindowVisible(hwnd) and pid.value in results['target_pids']:
#             # Get window title
#             length = user32.GetWindowTextLengthW(hwnd) + 1
#             buffer = ctypes.create_unicode_buffer(length)
#             user32.GetWindowTextW(hwnd, buffer, length)
#             title = buffer.value

#             if title:
#                 results['windows'].append({
#                     'hwnd': hwnd,
#                     'title': title,
#                     'pid': pid.value
#                 })
#     except Exception as e:
#         print(f"[WARN] Error in enum_windows_proc: {e}")
#     return True


# def find_chrome_windows_by_pid(pids):
#     """Find Chrome windows by their process IDs"""
#     if not sys.platform == 'win32':
#         return []

#     results = {'windows': [], 'target_pids': pids}
#     enum_windows_proc_callback = ctypes.WINFUNCTYPE(
#         wintypes.BOOL, wintypes.HWND, ctypes.py_object
#     )(enum_windows_proc)

#     try:
#         user32.EnumWindows(enum_windows_proc_callback, ctypes.py_object(results))
#     except Exception as e:
#         print(f"[ERROR] Failed to enumerate windows: {e}")

#     return results['windows']


# def bring_process_to_foreground(pid=None, hwnd=None):
#     """Force a window to foreground using advanced techniques"""
#     if not sys.platform == 'win32':
#         return False

#     if not (pid or hwnd):
#         return False

#     try:
#         # If we have a handle, use it directly
#         if hwnd:
#             target_hwnd = hwnd
#         # Otherwise, find windows by PID
#         elif pid:
#             windows = find_chrome_windows_by_pid([pid])
#             if not windows:
#                 return False
#             target_hwnd = windows[0]['hwnd']

#         # Check if window exists and is visible
#         if not (user32.IsWindow(target_hwnd) and user32.IsWindowVisible(target_hwnd)):
#             return False

#         # Try multiple techniques to bring window to foreground

#         # 1. First technique: Simulate Alt+Tab behavior
#         curr_thread = win32api.GetCurrentThreadId()
#         fore_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)

#         # Attach input if different threads
#         if curr_thread != fore_thread:
#             user32.AttachThreadInput(curr_thread, fore_thread, True)

#         # Show window if minimized
#         win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)

#         # Set foreground window
#         result = user32.SetForegroundWindow(target_hwnd)

#         # Set active window
#         user32.SetActiveWindow(target_hwnd)

#         # Give it focus
#         user32.SetFocus(target_hwnd)

#         # Detach threads if needed
#         if curr_thread != fore_thread:
#             user32.AttachThreadInput(curr_thread, fore_thread, False)

#         # 2. Second technique: Minimize and restore the window
#         if not result:
#             win32gui.ShowWindow(target_hwnd, win32con.SW_MINIMIZE)
#             time.sleep(0.2)
#             win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
#             time.sleep(0.2)
#             user32.SetForegroundWindow(target_hwnd)

#         # 3. Third technique: Try BringWindowToTop
#         if not result:
#             user32.BringWindowToTop(target_hwnd)
#             user32.SetForegroundWindow(target_hwnd)

#         # Verify success
#         time.sleep(0.5)
#         active_hwnd = user32.GetForegroundWindow()
#         if active_hwnd == target_hwnd:
#             return True
#         else:
#             print(f"[WARN] Window activation failed. Current={active_hwnd}, Target={target_hwnd}")
#             return False

#     except Exception as e:
#         print(f"[ERROR] Failed to bring process to foreground: {e}")
#         return False


# def activate_window(window_info):
#     """Activate a window using advanced techniques"""
#     if not window_info:
#         return False

#     # Extract necessary information
#     title = window_info.get('title')
#     hwnd = window_info.get('hwnd')
#     pid = window_info.get('pid')
#     window_obj = window_info.get('window')

#     print(f"[INFO] Attempting to activate window: {title}, PID: {pid}, Handle: {hwnd}")

#     # For Windows, use advanced techniques
#     if sys.platform == 'win32':
#         # Disable focus stealing prevention
#         disable_focus_stealing_prevention()

#         # Try using pygetwindow first as it handles fullscreen better
#         if window_obj:
#             try:
#                 # First minimize all Chrome windows to exit fullscreen
#                 chrome_windows = [w for w in gw.getWindowsWithTitle("Chrome") if w is not None]
#                 for window in chrome_windows:
#                     try:
#                         if window.isMaximized:
#                             print(f"[INFO] Minimizing window: {window.title}")
#                             window.minimize()
#                             time.sleep(0.5)
#                     except Exception as e:
#                         print(f"[WARN] Failed to minimize window: {e}")

#                 # Then minimize our target window just to be sure
#                 time.sleep(0.5)
#                 window_obj.minimize()
#                 time.sleep(0.5)

#                 # Now restore and maximize it
#                 window_obj.restore()
#                 time.sleep(0.5)
#                 window_obj.maximize()
#                 time.sleep(0.5)

#                 # Verify activation
#                 active_window = gw.getActiveWindow()
#                 if active_window and active_window.title == title:
#                     print(f"[INFO] Successfully activated window with pygetwindow: {title}")
#                     return True
#             except Exception as e:
#                 print(f"[ERROR] Failed to activate with pygetwindow: {e}")

#         # Try using the window handle as backup
#         if hwnd:
#             try:
#                 # First minimize the window
#                 win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
#                 time.sleep(0.5)

#                 # Then restore and maximize
#                 win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
#                 time.sleep(0.5)
#                 win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
#                 time.sleep(0.5)

#                 # Set as foreground window
#                 win32gui.SetForegroundWindow(hwnd)

#                 # Verify success
#                 active_hwnd = user32.GetForegroundWindow()
#                 if active_hwnd == hwnd:
#                     print(f"[INFO] Successfully activated window using hwnd: {title}")
#                     return True
#             except Exception as e:
#                 print(f"[ERROR] Failed to activate with hwnd: {e}")

#     # As a last resort, try alt-tab technique on Windows
#     if sys.platform == 'win32':
#         try:
#             # Simulate Alt+Tab press
#             print("[INFO] Trying Alt+Tab technique...")
#             pyautogui.keyDown('alt')
#             time.sleep(0.1)
#             pyautogui.press('tab')
#             time.sleep(0.5)
#             pyautogui.keyUp('alt')
#             time.sleep(0.5)

#             # Check if we got lucky
#             active_window = gw.getActiveWindow()
#             if active_window and (title in active_window.title):
#                 print(f"[INFO] Successfully activated with Alt+Tab: {active_window.title}")
#                 return True
#         except Exception as e:
#             print(f"[ERROR] Alt+Tab technique failed: {e}")

#     print(f"[ERROR] All activation techniques failed for window: {title}")
#     return False


# def update_window_title(user_id, window_key=None):
#     """Update stored window title after navigation actions"""
#     if user_id not in user_sessions:
#         print(f"[DEBUG] update_window_title: No session found for user {user_id}")
#         return False

#     session_data = user_sessions[user_id]

#     # If no specific window_key is provided, use current_window
#     if not window_key and 'current_window' in session_data:
#         window_key = session_data['current_window']

#     if not window_key or window_key not in session_data['windows']:
#         print(f"[DEBUG] update_window_title: No valid window key found. Key: {window_key}")
#         return False

#     print(f"[DEBUG] Updating title for window key: {window_key}")
#     print(f"[DEBUG] Original window title: {session_data['windows'][window_key]['exact_title']}")

#     # Get current active window
#     active_window = gw.getActiveWindow()
#     if not active_window:
#         print("[DEBUG] update_window_title: No active window found")
#         return False

#     # Update the stored title for this window
#     window_info = session_data['windows'][window_key]
#     window_info['exact_title'] = active_window.title
#     window_info['title'] = active_window.title  # Update both title fields
#     print(f"[DEBUG] Updated window title to: {active_window.title}")

#     return True

# import time

# def activate_user_window(user_id, url=None):
#     """Activate the correct window for a user's session based on window_key."""
#     if user_id not in user_sessions:
#         print(f"[WARN] No active sessions for user {user_id}")
#         return False

#     session_data = user_sessions[user_id]
#     windows = session_data.get('windows', {})
#     chrome_windows = get_chrome_windows()  # Fetch all active Chrome windows

#     print(f"[DEBUG] Available Chrome windows: {len(chrome_windows)}")
#     for cw in chrome_windows:
#         print(f"[DEBUG] Window: {cw.get('title', 'Unknown')}, PID: {cw.get('pid', 'Unknown')}")

#     # Track checked windows to avoid duplicates
#     checked_windows = set()

#     print(f"[DEBUG] activate_user_window - User: {user_id}, URL: {url}")
#     print(f"[DEBUG] All window keys for user: {list(windows.keys())}")

#     # **Step 1: Activate Current Window (If Available)**
#     if session_data.get('current_window') in windows:
#         current_key = session_data['current_window']
#         window_info = windows[current_key]

#         for chrome_window in chrome_windows:
#             if chrome_window.get('hwnd') == window_info.get('hwnd'):
#                 print(f"[INFO] Activating window using key: {current_key} -> {chrome_window.get('title')}")
#                 result = activate_window(chrome_window)
#                 if result:
#                     window_info['last_activated'] = time.time()  # Update last active time
#                     return True
#                 checked_windows.add(chrome_window.get('hwnd'))

#     # **Step 2: Find and Activate the Correct Window Based on URL**
#     if url:
#         matching_keys = [k for k in windows.keys() if k.startswith(f"{url}_")]
#         for key in sorted(matching_keys, key=lambda k: windows[k].get('last_activated', 0), reverse=True):
#             window_info = windows[key]

#             for chrome_window in chrome_windows:
#                 if chrome_window.get('hwnd') in checked_windows:
#                     continue

#                 if chrome_window.get('hwnd') == window_info.get('hwnd'):
#                     print(f"[INFO] Found exact match for URL {url}: {chrome_window.get('title')}")
#                     result = activate_window(chrome_window)
#                     if result:
#                         session_data['current_window'] = key
#                         window_info['last_activated'] = time.time()
#                         return True
#                     checked_windows.add(chrome_window.get('hwnd'))

#     # **Step 3: Try Activating the Most Recently Used Window**
#     sorted_keys = sorted(windows.keys(), key=lambda k: windows[k].get('last_activated', 0), reverse=True)
#     for key in sorted_keys:
#         window_info = windows[key]

#         for chrome_window in chrome_windows:
#             if chrome_window.get('hwnd') in checked_windows:
#                 continue

#             if chrome_window.get('hwnd') == window_info.get('hwnd'):
#                 print(f"[INFO] Fallback activation using window key: {key} -> {chrome_window.get('title')}")
#                 result = activate_window(chrome_window)
#                 if result:
#                     session_data['current_window'] = key
#                     window_info['last_activated'] = time.time()
#                     return True
#                 checked_windows.add(chrome_window.get('hwnd'))

#     # **Step 4: Last Resort - Activate the First Available Chrome Window**
#     for chrome_window in chrome_windows:
#         if chrome_window.get('hwnd') not in checked_windows:
#             print(f"[WARN] No exact match found, activating first available Chrome window: {chrome_window.get('title')}")
#             return activate_window(chrome_window)

#     print("[ERROR] No Chrome windows found for activation.")
#     return False


# def take_screenshot(user_id, context=""):
#     """Capture a screenshot on the local machine"""
#     try:
#         timestamp = int(time.time())
#         screenshot_filename = f"user_{user_id}_{timestamp}.png"
#         screenshot_path = os.path.join(MEDIA_DIR, screenshot_filename)

#         # Update session activity
#         if user_id in user_sessions:
#             user_sessions[user_id]['last_active'] = time.time()
#         else:
#             user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}

#         # Wait briefly to ensure UI is stable
#         time.sleep(3)

#         # Take screenshot
#         screenshot = pyautogui.screenshot()
#         screenshot.save(screenshot_path)

#         if not os.path.exists(screenshot_path):
#             raise FileNotFoundError("Screenshot not saved!")

#         # Create URL for the screenshot
#         screenshot_url = f"/media/screenshots/{screenshot_filename}?t={timestamp}"

#         print(f"[INFO] Screenshot saved to {screenshot_path}")

#         # Minimize the Chrome window after taking the screenshot
#         active_window = gw.getActiveWindow()
#         chrome_windows = [win for win in gw.getWindowsWithTitle("Google Chrome") if win is not None]

#         if chrome_windows:
#             hwnd = chrome_windows[0]._hWnd  # Get window handle
#             time.sleep(1)  # Short delay before minimizing
#             win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
#             print(f"[INFO] Minimized Chrome window: {chrome_windows[0].title}")
#         else:
#             print("[WARN] No active Chrome window found to minimize")

#         return screenshot_path, screenshot_url
#     except Exception as e:
#         print(f"[ERROR] Failed to take screenshot: {e}")
#         traceback.print_exc()
#         return None, None


# def send_to_omniparser(screenshot_path):
#     """Send screenshot to OmniParser API for UI element detection"""
#     if not REPLICATE_API_TOKEN:
#         print("[ERROR] Missing Replicate API Token")
#         return None

#     try:
#         # Read Image
#         img = cv2.imread(screenshot_path)

#         if img is None:
#             return {"error": "Invalid Image Path"}

#         # Get image dimensions
#         height, width, _ = img.shape

#         print(f"[INFO] Image Loaded: {screenshot_path}")
#         print(f"[INFO] Image Dimensions: {width}x{height}")

#         # Start Timer
#         start_time = time.time()

#         model = "microsoft/omniparser-v2:49cf3d41b8d3aca1360514e83be4c97131ce8f0d99abfc365526d8384caa88df"
#         input_data = {
#             "image": open(screenshot_path, "rb"),
#             "confidence": 0.5,
#         }

#         # Run Replicate API
#         output = replicate.run(model, input=input_data)

#         # End Timer
#         response_time = round(time.time() - start_time, 2)

#         # Validate output
#         if not isinstance(output, dict) or 'elements' not in output:
#             return {"error": "Invalid API response", "response": output}

#         elements_str = output['elements']

#         if not isinstance(elements_str, str):
#             return {"error": "Unexpected 'elements' format", "response": elements_str}

#         # Extract UI elements using regex
#         elements = []
#         pattern = r"icon (\d+): \{'type': '([^']+)', 'bbox': \[([^]]+)\], 'interactivity': ([^,]+), 'content': '([^']+)'\}"
#         matches = re.findall(pattern, elements_str)

#         for match in matches:
#             i = int(match[0])
#             element_type = match[1]
#             bbox_str = match[2]
#             interactivity = match[3] == "True"
#             content = match[4]

#             # Parse bbox coordinates
#             bbox = [float(coord.strip()) for coord in bbox_str.split(',')]

#             # Convert relative coordinates to absolute
#             abs_coords = [int(bbox[0] * width), int(bbox[1] * height),
#                           int(bbox[2] * width), int(bbox[3] * height)]

#             # Calculate center point for clicking
#             center_x = (abs_coords[0] + abs_coords[2]) // 2
#             center_y = (abs_coords[1] + abs_coords[3]) // 2

#             element = {
#                 "id": i,
#                 "name": content,
#                 "type": element_type,
#                 "interactivity": interactivity,
#                 "coordinates": abs_coords,
#                 "click_point": (center_x, center_y)
#             }

#             elements.append(element)

#         return {
#             "elements": elements,
#             "total_elements": len(elements),
#             "interactive_elements": sum(1 for e in elements if e["interactivity"]),
#             "response_time": response_time
#         }

#     except Exception as e:
#         print(f"[ERROR] OmniParser error: {e}")
#         traceback.print_exc()
#         return {"error": str(e)}


# def perform_ui_action(user_id, action, element_name, click_X, click_Y, text):
#     """Performs UI actions directly on the local machine with enhanced window activation"""
#     # Debugging Logs
#     print("=" * 50)
#     print(f"[DEBUG] Action Requested: {action}")
#     print(f"[DEBUG] User ID: {user_id}")
#     print(f"[DEBUG] Element Name: {element_name}")
#     print(f"[DEBUG] Click Coordinates: ({click_X}, {click_Y})")
#     print("=" * 50)

#     # Ensure foreground lock timeout is disabled
#     if sys.platform == 'win32':
#         disable_focus_stealing_prevention()

#     # First, try to minimize all Chrome windows to handle fullscreen issues
#     try:
#         chrome_windows = gw.getWindowsWithTitle("Chrome")
#         for window in chrome_windows:
#             try:
#                 if window.isMaximized:
#                     window.minimize()
#                     time.sleep(0.2)
#             except Exception as e:
#                 print(f"[WARN] Failed to minimize Chrome window: {e}")
#     except Exception as e:
#         print(f"[WARN] Failed to process Chrome windows: {e}")

#     # Now activate the correct window with multiple attempts
#     activation_success = False
#     for attempt in range(3):  # Try up to 3 times
#         if activate_user_window(user_id):
#             activation_success = True
#             break
#         else:
#             print(f"[WARN] Window activation attempt {attempt + 1} failed, retrying...")
#             time.sleep(1)

#     if not activation_success:
#         # Emergency fallback: Try to use simulated Alt+Tab
#         try:
#             print("[INFO] Trying emergency Alt+Tab approach...")
#             # Get all Chrome windows
#             chrome_windows = [w for w in gw.getAllWindows() if 'Chrome' in w.title]
#             if chrome_windows:
#                 # First minimize all to exit fullscreen
#                 for window in chrome_windows:
#                     try:
#                         window.minimize()
#                         time.sleep(0.2)
#                     except Exception as e:
#                         print(f"[WARN] Failed to minimize: {e}")

#                 time.sleep(1)

#                 # Now try to restore and maximize the first Chrome window
#                 try:
#                     chrome_windows[0].restore()
#                     time.sleep(0.5)
#                     chrome_windows[0].maximize()
#                     time.sleep(0.5)
#                     activation_success = True
#                 except Exception as e:
#                     print(f"[ERROR] Failed to restore Chrome window: {e}")
#         except Exception as e:
#             print(f"[ERROR] Emergency activation failed: {e}")

#     if not activation_success:
#         return {"error": "Failed to locate and activate the correct browser window after multiple attempts"}

#     # Update session activity
#     if user_id in user_sessions:
#         user_sessions[user_id]['last_active'] = time.time()
#     else:
#         user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}

#     try:
#         # Wait to ensure UI is stable - wait longer to ensure window is properly activated
#         time.sleep(2)

#         if action == 'click':
#             # Try different clicking methods
#             try:
#                 # First try standard click
#                 pyautogui.click(click_X, click_Y)
#                 time.sleep(1)
#                 print(f"[INFO] Clicked at position ({click_X}, {click_Y})")
#             except Exception as e1:
#                 print(f"[WARN] Standard click failed: {e1}")


#         elif action in ['type', 'enter']:
#             # Try different clicking methods
#             try:
#                 pyautogui.click(click_X, click_Y)
#                 time.sleep(0.5)
#                 pyautogui.write(text)
#                 print(f"[INFO] Typed '{text}' at position ({click_X}, {click_Y})")
#             except Exception as e1:
#                 print(f"[WARN] Standard type failed: {e1}")

#         else:
#             return {"error": "Invalid action"}

#         # Wait longer for any UI updates
#         time.sleep(3)

#         # Update the window title in our tracking
#         print("[DEBUG] Updating window title after UI action")
#         update_window_title(user_id)

#         # Take screenshot after action
#         screenshot_path, screenshot_url = take_screenshot(user_id, action)
#         omniparser_response = send_to_omniparser(screenshot_path)

#         if screenshot_path:
#             return {
#                 "status": f"{action.capitalize()} performed on {element_name}",
#                 "screenshot": screenshot_url,
#                 "coordinates": omniparser_response
#             }
#         else:
#             return {"error": "Failed to capture screenshot after action"}

#     except Exception as e:
#         print(f"[ERROR] Action failed: {e}")
#         traceback.print_exc()
#         return {"error": f"Action failed: {str(e)}"}


@csrf_exempt
def handle_command(request):
    """Handle API commands for automation"""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        command = data.get("command")
        click_X = data.get("click_x")
        click_Y = data.get("click_y")
        type_text = data.get("text")
        user_id = data.get("user_id")

        # Validate required parameters
        if not command:
            return JsonResponse({"error": "No command provided"}, status=400)
        if not user_id:
            return JsonResponse({"error": "No user_id provided"}, status=400)

        print(f"[INFO] Received command: {command} from user: {user_id}")

        # Handling "open" command
        if command.startswith("open "):
            url = command.split(" ", 1)[1]
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            try:
                if open_browser(user_id, url):
                    print("[INFO] Browser successfully opened")
                    # Wait additional time for page to load
                    time.sleep(5)

                    if user_id in user_sessions and 'current_window' in user_sessions[user_id]:
                        current_window_key = user_sessions[user_id]['current_window']
                        print(f"[DEBUG] After browser open - current window key: {current_window_key}")
                        update_window_title(user_id, current_window_key)

                    # Take screenshot
                    screenshot_path, screenshot_url = take_screenshot(user_id, url)

                    # Get active window details for debugging
                    active_window_title = "Unknown"
                    try:
                        active_window = gw.getActiveWindow()
                        if active_window:
                            active_window_title = active_window.title
                    except:
                        pass

                    if screenshot_path:
                        # Process screenshot with OmniParser
                        omniparser_response = send_to_omniparser(screenshot_path)

                        # List all chrome windows for debugging
                        chrome_windows = [w['title'] for w in get_chrome_windows()]

                        return JsonResponse({
                            "status": "browser opened",
                            "url": url,
                            "screenshot": screenshot_url,
                            "active_window": active_window_title,
                            "chrome_windows": chrome_windows,
                            "tracked_windows": {url: info['title'] for url, info in user_sessions[user_id][
                                'windows'].items()} if user_id in user_sessions else {},
                            "omniparser_data": omniparser_response
                        })
                    else:
                        return JsonResponse({
                            "error": "Failed to take screenshot",
                            "active_window": active_window_title
                        }, status=500)
                else:
                    return JsonResponse({"error": "Failed to open browser"}, status=500)

            except Exception as e:
                print(f"[ERROR] Error opening browser: {e}")
                traceback.print_exc()
                return JsonResponse({"error": f"Failed to open browser: {str(e)}"}, status=500)

        # Handling "click" command
        elif command.startswith("click "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid click command format"}, status=400)

            action, element_name = parts[0], parts[1]
            if not element_name:
                return JsonResponse({"error": "No element specified for clicking"}, status=400)

            action_response = perform_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

        # Handling "type" and "enter" commands
        elif command.startswith("type ") or command.startswith("enter "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid command format."}, status=400)

            action = parts[0]
            type_command = parts[1]

            in_index = type_command.find(" in ")
            if in_index == -1:
                return JsonResponse({"error": "Invalid format. Use: type <text> in <element>"}, status=400)

            type_text = type_command[:in_index]
            element_name = type_command[in_index + 4:]

            if not element_name:
                return JsonResponse({"error": "No target element specified for typing"}, status=400)

            action_response = perform_ui_action(user_id, action, element_name, click_X, click_Y, type_text)
            return JsonResponse(action_response, safe=False)

        return JsonResponse({"error": "Unknown command"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        traceback.print_exc()
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)


#Test Execution 
@csrf_exempt
def Execute_command(request):
    """Handle API commands for automation"""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        command = data.get("command")
        click_X = data.get("click_x")
        click_Y = data.get("click_y")
        type_text = data.get("text")
        user_id = data.get("user_id")

        # Validate required parameters
        if not command:
            return JsonResponse({"error": "No command provided"}, status=400)
        if not user_id:
            return JsonResponse({"error": "No user_id provided"}, status=400)

        print(f"[INFO] Received command: {command} from user: {user_id}")

        # Handling "open" command
        if command.startswith("open "):
            url = command.split(" ", 1)[1]
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            try:
                if open_browser(user_id, url):
                    print("[INFO] Browser successfully opened")
                    # Wait additional time for page to load
                    time.sleep(5)

                    if user_id in user_sessions and 'current_window' in user_sessions[user_id]:
                        current_window_key = user_sessions[user_id]['current_window']
                        print(f"[DEBUG] After browser open - current window key: {current_window_key}")
                        update_window_title(user_id, current_window_key)

                    # Take screenshot
                    screenshot_path, screenshot_url = take_screenshot(user_id, url)

                    # Get active window details for debugging
                    active_window_title = "Unknown"
                    try:
                        active_window = gw.getActiveWindow()
                        if active_window:
                            active_window_title = active_window.title
                    except:
                        pass

                    if screenshot_path:

                        # List all chrome windows for debugging
                        chrome_windows = [w['title'] for w in get_chrome_windows()]

                        return JsonResponse({
                            "status": "browser opened",
                            "url": url,
                            "screenshot": screenshot_url,
                            "active_window": active_window_title,
                            "chrome_windows": chrome_windows,
                            "tracked_windows": {url: info['title'] for url, info in user_sessions[user_id][
                                'windows'].items()} if user_id in user_sessions else {},
                        })
                    else:
                        return JsonResponse({
                            "error": "Failed to take screenshot",
                            "active_window": active_window_title
                        }, status=500)
                else:
                    return JsonResponse({"error": "Failed to open browser"}, status=500)

            except Exception as e:
                print(f"[ERROR] Error opening browser: {e}")
                traceback.print_exc()
                return JsonResponse({"error": f"Failed to open browser: {str(e)}"}, status=500)

        # Handling "click" command
        elif command.startswith("click "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid click command format"}, status=400)

            action, element_name = parts[0], parts[1]
            if not element_name:
                return JsonResponse({"error": "No element specified for clicking"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

        # Handling "type" and "enter" commands
        elif command.startswith("type ") or command.startswith("enter "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid command format."}, status=400)

            action = parts[0]
            type_command = parts[1]

            in_index = type_command.find(" in ")
            if in_index == -1:
                return JsonResponse({"error": "Invalid format. Use: type <text> in <element>"}, status=400)

            type_text = type_command[:in_index]
            element_name = type_command[in_index + 4:]

            if not element_name:
                return JsonResponse({"error": "No target element specified for typing"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, type_text)
            return JsonResponse(action_response, safe=False)

        return JsonResponse({"error": "Unknown command"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        traceback.print_exc()
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)






