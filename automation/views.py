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
from django.views.decorators.http import require_http_methods
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

def react_app(request, path=''):
    return render(request, 'index.html')


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
        
        # Handling "verify" command
        elif command.startswith("verify "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid verify command format"}, status=400)

            action, element_name = parts[0], parts[1]
            if not element_name:
                return JsonResponse({"error": "No element specified for verify"}, status=400)

            action_response = perform_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

        elif command.startswith("get "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid get command format"}, status=400)

            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            if not element_name.strip():
                return JsonResponse({"error": "No element specified for get"}, status=400)

            action_response = perform_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

        elif command.startswith("scroll_up "):
            parts = command.split(" ", 1)
            
            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            action_response = perform_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

        elif command.startswith("scroll_down "):
            parts = command.split(" ", 1)
            
            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            
            action_response = perform_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

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

        # Handling "verify" command
        elif command.startswith("verify "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid verify command format"}, status=400)

            action, element_name = parts[0], parts[1]
            if not element_name:
                return JsonResponse({"error": "No element specified for verify"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)


        # Handling "get" command
        elif command.startswith("get "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid get command format"}, status=400)

            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            if not element_name.strip():
                return JsonResponse({"error": "No element specified for get"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)
        
        elif command.startswith("scroll_up "):
            parts = command.split(" ", 1)
            
            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            if not element_name.strip():
                return JsonResponse({"error": "No element specified for get"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

        elif command.startswith("scroll_down "):
            parts = command.split(" ", 1)
            
            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            if not element_name.strip():
                return JsonResponse({"error": "No element specified for get"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "")
            return JsonResponse(action_response)

        return JsonResponse({"error": "Unknown command"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        traceback.print_exc()
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)



import time
import json
import traceback
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from api.models import TestSuite, TestCase, TestStep

@csrf_exempt
def wait(request):
    """API endpoint to implement a wait/delay"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        duration_ms = data.get("duration_ms", 1000)  # Default 1 second
        
        # Convert milliseconds to seconds and sleep
        time.sleep(duration_ms / 1000)
        
        return JsonResponse({
            "status": "success",
            "message": f"Waited for {duration_ms} milliseconds"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

@csrf_exempt
def run_testsuite(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        suite_id = data.get("testsuite_id")
        user_id = data.get("user_id")
        
        # Add wait parameters with defaults in milliseconds
        wait_between_steps = data.get("wait_between_steps", 1000)  # Default 1000ms (1 second)
        wait_between_cases = data.get("wait_between_cases", 3000)  # Default 3000ms (3 seconds)

        if not suite_id or not user_id:
            return JsonResponse({"error": "Missing testsuite_id or user_id"}, status=400)

        try:
            suite = TestSuite.objects.get(id=suite_id)
        except TestSuite.DoesNotExist:
            return JsonResponse({"error": "TestSuite not found"}, status=404)

        testcase_ids = suite.testcase  # This is a list of TestCase IDs (JSONField)
        results = {
            "testsuite_id": suite.id,
            "testsuite_title": suite.title,
            "user_id": user_id,
            "testcases": []
        }

        for case_index, case_id in enumerate(testcase_ids):
            # Wait between test cases (skip for the first case)
            if case_index > 0:
                time.sleep(wait_between_cases / 1000)  # Convert to seconds
                
            try:
                testcase = TestCase.objects.get(id=case_id)
            except TestCase.DoesNotExist:
                results["testcases"].append({
                    "testcase_id": case_id,
                    "status": "TestCase not found"
                })
                continue

            case_result = {
                "testcase_id": testcase.id,
                "testcase_name": testcase.name,
                "steps": []
            }

            for step_index, step in enumerate(testcase.steps.all()):  # Ordered by step_number due to Meta
                # Wait between steps (skip for the first step)
                if step_index > 0:
                    time.sleep(wait_between_steps / 1000)  # Convert to seconds
                    
                command = step.step_description
                click_x = step.step_coordinates.get('click_x') if step.step_coordinates else None
                click_y = step.step_coordinates.get('click_y') if step.step_coordinates else None

                try:
                    response = Execute_command_internal(command, user_id, click_x, click_y)
                    
                    # Fix: Check for success status with proper conditions
                    # The command execution appears successful when it returns certain status values
                    is_successful = (
                        response.get('status') == 'success' or
                        'browser opened' in str(response.get('status', '')) or
                        'Click performed' in str(response.get('status', '')) or
                        'Type performed' in str(response.get('status', '')) or
                        'Verify performed' in str(response.get('status', '')) or
                        'Get performed' in str(response.get('status', ''))
                    )
                    
                    step.teststep_result = 'passed' if is_successful else 'failed'
                    step.save()

                    case_result["steps"].append({
                        "step_number": step.step_number,
                        "command": command,
                        "result": step.teststep_result,
                        "response": response
                    })

                except Exception as e:
                    step.teststep_result = 'failed'
                    step.save()
                    case_result["steps"].append({
                        "step_number": step.step_number,
                        "command": command,
                        "result": "failed",
                        "error": str(e)
                    })

            # Calculate case result summary
            passed_steps = sum(1 for step in case_result["steps"] if step["result"] == "passed")
            total_steps = len(case_result["steps"])
            case_result["summary"] = {
                "total_steps": total_steps,
                "passed_steps": passed_steps,
                "status": "passed" if passed_steps == total_steps else "failed"
            }
            
            results["testcases"].append(case_result)

        # Calculate overall test suite results
        total_cases = len(results["testcases"])
        passed_cases = sum(1 for case in results["testcases"] if case.get("summary", {}).get("status") == "passed")
        results["summary"] = {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "status": "passed" if passed_cases == total_cases else "failed"
        }

        return JsonResponse(results)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

# This function simulates calling the Execute_command logic internally.
# You can adapt this if Execute_command is moved to another module.
def Execute_command_internal(command, user_id, click_x, click_y):
    request_data = {
        "command": command,
        "user_id": user_id,
        "click_x": click_x,
        "click_y": click_y
    }

    # Simulate request object
    fake_request = HttpRequest()
    fake_request.method = "POST"
    fake_request._body = json.dumps(request_data).encode("utf-8")

    return json.loads(Execute_command(fake_request).content.decode())





from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json, time
import pygetwindow as gw
import win32gui, win32con

@csrf_exempt
def insert_screen(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if not user_id:
            return JsonResponse({"error": "Missing user_id"}, status=400)

        # ✅ Maximize Chrome window before screenshot
        chrome_windows = [win for win in gw.getWindowsWithTitle("Google Chrome") if win is not None]
        if chrome_windows:
            hwnd = chrome_windows[0]._hWnd
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            print(f"[INFO] Maximized Chrome window: {chrome_windows[0].title}")
        else:
            print("[WARN] No Chrome window found to maximize")

        # ✅ Wait only 5 seconds 
        time.sleep(5)

        # Take screenshot
        screenshot_path, screenshot_url = take_screenshot(user_id)

        if screenshot_path:
            omniparser_response = send_to_omniparser(screenshot_path)
            return JsonResponse({
                "status": "Screenshot Captured Based on Screen",
                "screenshot": screenshot_url,
                "omniparser_data": omniparser_response
            })
        else:
            return JsonResponse({"error": "Failed to take screenshot"}, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




import json
import time
import pygetwindow as gw
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import win32gui
import win32con
import win32process
import psutil

def get_browser_windows():
    """Get all browser windows with their titles."""
    # Common browser window title identifiers
    browser_identifiers = [
        "Google Chrome",
        "Mozilla Firefox",
        "Edge",
        "Safari",
        "Opera",
        "Brave",
    ]
    
    browser_windows = []
    all_windows = gw.getAllWindows()
    
    for window in all_windows:
        if window.title and any(browser in window.title for browser in browser_identifiers):
            browser_windows.append({
                "title": window.title,
                "x": window.left,
                "y": window.top,
                "width": window.width,
                "height": window.height,
                "active": window.isActive,
                "hwnd": window._hWnd  # Store window handle for more reliable activation
            })
    
    return browser_windows

@require_http_methods(["GET"])
def get_browser_tabs(request):
    """API to get all open browser tabs."""
    try:
        browser_windows = get_browser_windows()
        return JsonResponse({
            "status": "success",
            "browser_tabs": browser_windows
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)

def focus_window_by_title(title):
    """Focus a window by its title using Win32 API for more reliable activation."""
    try:
        windows = gw.getAllWindows()
        for window in windows:
            if title in window.title:
                # Use the Win32 API to more reliably set focus
                hwnd = window._hWnd
                
                # Bring the window to the foreground
                if win32gui.IsIconic(hwnd):  # If minimized
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                
                # Set foreground window more reliably
                win32gui.SetForegroundWindow(hwnd)
                
                # Make sure the window is visible and maximized
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                
                # Give the window time to come into focus
                time.sleep(1.0)
                
                # Verify activation was successful
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
                else:
                    # Try alternative approach with window flashing
                    win32gui.FlashWindow(hwnd, True)
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.5)
                    return win32gui.GetForegroundWindow() == hwnd
        
        return False
    except Exception as e:
        print(f"Error focusing window: {str(e)}")
        return False

def focus_window_by_hwnd(hwnd):
    """Focus a window by its handle directly."""
    try:
        # Restore the window if it's minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # Bring window to foreground
        win32gui.SetForegroundWindow(hwnd)
        
        # Make sure it's visible and maximized
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        
        # Give the window time to come into focus
        time.sleep(1.0)
        
        return win32gui.GetForegroundWindow() == hwnd
    except Exception as e:
        print(f"Error focusing window by handle: {str(e)}")
        return False

@csrf_exempt
@require_http_methods(["POST"])
def process_browser_tab(request):
    """API to focus on a specific browser tab, take screenshot and process it."""
    try:
        data = json.loads(request.body)
        tab_title = data.get('tab_title')
        hwnd = data.get('hwnd')  # New: accept window handle directly if available
        user_id = data.get('user_id', 'default')
        
        if not tab_title and not hwnd:
            return JsonResponse({
                "status": "error",
                "message": "Either tab_title or hwnd is required"
            }, status=400)
        
        # Focus on the selected window
        focused = False
        
        # Try with hwnd first if provided (most reliable)
        if hwnd:
            focused = focus_window_by_hwnd(int(hwnd))
        
        # Fall back to title-based focus if hwnd not provided or failed
        if not focused and tab_title:
            focused = focus_window_by_title(tab_title)
        
        if not focused:
            return JsonResponse({
                "status": "error",
                "message": f"Could not find or focus window with title: {tab_title}"
            }, status=404)
        
        # Extra delay to ensure window is fully focused
        time.sleep(3)
        
        # Take screenshot - assuming this function exists elsewhere as mentioned
        screenshot_path, screenshot_url = take_screenshot(user_id)
        
        if not screenshot_path:
            return JsonResponse({
                "status": "error",
                "message": "Failed to take screenshot"
            }, status=500)
        
        # Send to omniparser - assuming this function exists elsewhere as mentioned
        omniparser_response = send_to_omniparser(screenshot_path)
        
        return JsonResponse({
            "status": "success",
            "message": "Screenshot captured based on screen",
            "screenshot": screenshot_url,
            "omniparser_data": omniparser_response
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)