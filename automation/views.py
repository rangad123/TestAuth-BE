from django.shortcuts import render
import sys
import os
import time
import pyautogui
import json
from django.http import JsonResponse,HttpRequest
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import traceback
import pygetwindow as gw
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import pyperclip
from .browser_manager import open_browser, update_window_title, is_chrome_bookmarks_bar_visible
from .screenshot_manager import take_screenshot, Run_test_screenshot
from .omniparser_client import send_to_omniparser
from .ui_action import perform_ui_action, Execute_ui_action
from .session_manager import user_sessions
from .window_utils import get_chrome_windows,activate_user_window,disable_focus_stealing_prevention
from api.models import TestSuite, TestCase, TestStep
from django.views.decorators.http import require_http_methods
import logging
from collections import defaultdict
import psutil


if sys.platform == 'win32':
    import win32gui
    import win32con
    import win32api
    import win32process
    import win32com.client
    import ctypes
    from ctypes import wintypes


# def react_app(request, path=''):
#     return render(request, 'index.html')


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


# Test Execution
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

        is_final_step = data.get("is_final_step", False)

        # Print the is_final_step value for debugging
        print(f"[DEBUG] is_final_step: {is_final_step}")

        # Validate required parameters
        if not command:
            return JsonResponse({"error": "No command provided"}, status=400)
        if not user_id:
            return JsonResponse({"error": "No user_id provided"}, status=400)

        print(f"[INFO] Received command: {command} from user: {user_id}")
        print(f"[INFO] Is final step: {is_final_step}")

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
                    time.sleep(1)

                    if user_id in user_sessions and 'current_window' in user_sessions[user_id]:
                        current_window_key = user_sessions[user_id]['current_window']
                        print(f"[DEBUG] After browser open - current window key: {current_window_key}")
                        update_window_title(user_id, current_window_key)

                    screenshot_path, screenshot_url = Run_test_screenshot(user_id, url, minimize_after=is_final_step)
                    print(f"[DEBUG] After screenshot - is_final_step: {is_final_step}, minimizing: {is_final_step}")

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

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "", is_final_step)
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

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, type_text,
                                                is_final_step)
            return JsonResponse(action_response, safe=False)

        # Handling "verify" command
        elif command.startswith("verify "):
            parts = command.split(" ", 1)
            if len(parts) < 2:
                return JsonResponse({"error": "Invalid verify command format"}, status=400)

            action, element_name = parts[0], parts[1]
            if not element_name:
                return JsonResponse({"error": "No element specified for verify"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "", is_final_step)
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

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "", is_final_step)
            return JsonResponse(action_response)

        elif command.startswith("scroll_up "):
            parts = command.split(" ", 1)

            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            if not element_name.strip():
                return JsonResponse({"error": "No element specified for get"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "", is_final_step)
            return JsonResponse(action_response)

        elif command.startswith("scroll_down "):
            parts = command.split(" ", 1)

            action = parts[0]
            element_name = parts[1]  # You can still receive a label for UI location

            if not element_name.strip():
                return JsonResponse({"error": "No element specified for get"}, status=400)

            action_response = Execute_ui_action(user_id, action, element_name, click_X, click_Y, "", is_final_step)
            return JsonResponse(action_response)

        return JsonResponse({"error": "Unknown command"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        traceback.print_exc()
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)


@csrf_exempt
def execute_test_case(request):
    """
    Execute a batch of test steps without minimizing the browser between steps
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        command = data.get("command")
        click_X = data.get("click_x")
        click_Y = data.get("click_y")
        type_text = data.get("text")
        user_id = data.get("user_id")
        is_final_step = data.get("is_final_step", False)

        step_request = type('StepRequest', (), {})()
        step_request.method = "POST"
        step_request.body = json.dumps({
            "command": command,
            "click_x": click_X,
            "click_y": click_Y,
            "text": type_text,
            "user_id": user_id,
            "is_final_step": is_final_step
        })

        response = Execute_command(step_request)

        # Return the response directly
        return response

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        print(f"[ERROR] Unexpected error in test case execution: {e}")
        traceback.print_exc()
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)



@csrf_exempt
def wait(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        condition = data.get("condition")
        timeout = data.get("timeout", 10000)  # in ms
        poll_interval = data.get("poll_interval", 500)  # in ms
        debug = data.get("debug", False)
        expected_text = data.get("text", "").lower()
        check_address_bar = data.get("check_address_bar", False)

        is_final_step = data.get("is_final_step", False)

        # Print the is_final_step value for debugging
        print(f"[DEBUG] is_final_step: {is_final_step}")

        if sys.platform == 'win32':
            disable_focus_stealing_prevention()

        activation_success = False
        for attempt in range(3):
            if activate_user_window(user_id):
                activation_success = True
                break
            else:
                print(f"[WARN] Window activation attempt {attempt + 1} failed, retrying...")
                time.sleep(1)

        if not activation_success:
            try:
                print("[INFO] Trying emergency Alt+Tab approach...")
                chrome_windows = [w for w in gw.getAllWindows() if 'Chrome' in w.title]
                if chrome_windows:
                    for window in chrome_windows:
                        try:
                            window.minimize()
                            time.sleep(0.2)
                        except Exception as e:
                            print(f"[WARN] Failed to minimize: {e}")

                    time.sleep(1)

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
            return JsonResponse({
                "error": "Failed to locate and activate the correct browser window after multiple attempts"
            }, status=500)

        if user_id in user_sessions:
            user_sessions[user_id]['last_active'] = time.time()
        else:
            user_sessions[user_id] = {'last_active': time.time(), 'windows': {}}
            time.sleep(2)

        if not condition:
            time.sleep(timeout / 1000.0)

            screenshot_path, screenshot_url = Run_test_screenshot(user_id, "wait", minimize_after=is_final_step)
            if not screenshot_path:
                return JsonResponse({
                    "status": "error",
                    "message": "Screenshot failed.",
                    "screenshot_url": screenshot_url
                }, status=500)

            return JsonResponse({
                "status": "success",
                "message": f"Waited for {timeout} ms (static wait).",
                "screenshot_url": screenshot_url
            })

        start_time = time.time()

        def get_address_bar_text():
            try:
                pyautogui.hotkey('alt', 'd')
                time.sleep(0.5)
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                url = pyperclip.paste()
                pyautogui.click(100, 100)
                print(f"[INFO] Address bar text: {url}")
                return url.lower()
            except Exception as e:
                print(f"[ERROR] Failed to get address bar text: {str(e)}")
                return ""

        def is_text_found():
            screenshot_url = None

            if check_address_bar:
                current_url = get_address_bar_text()
                if expected_text in current_url:
                    time.sleep(1)
                    screenshot_path, screenshot_url = Run_test_screenshot(user_id, "wait", minimize_after=is_final_step)
                    return True, [{"name": current_url, "type": "url"}], None, screenshot_url
                else:
                    screenshot_path, screenshot_url = Run_test_screenshot(user_id, "wait", minimize_after=is_final_step)
                    return False, [], None, screenshot_url


            time.sleep(2)
            screenshot_path, screenshot_url = Run_test_screenshot(user_id, "wait", minimize_after=is_final_step)
            time.sleep(1)
            if not screenshot_path:
                return False, [], None, screenshot_url

            omniparser_response = send_to_omniparser(screenshot_path)
            if not omniparser_response or "elements" not in omniparser_response:
                return False, [], omniparser_response, screenshot_url

            elements = omniparser_response["elements"]
            matched = [e for e in elements if expected_text in e.get("name", "").lower()]
            return bool(matched), matched, omniparser_response, screenshot_url

        while True:
            found, matched_elements, full_response, screenshot_url = is_text_found()

            if found:
                message = f"Text '{expected_text}' found."
                if check_address_bar:
                    message = f"URL containing '{expected_text}' found in address bar."
                return JsonResponse({
                    "status": "success",
                    "message": message,
                    "matched_elements": matched_elements if debug else None,
                    "screenshot_url": screenshot_url
                })

            elapsed = (time.time() - start_time) * 1000
            if elapsed > timeout:
                message = f"Text '{expected_text}' not found within timeout."
                if check_address_bar:
                    message = f"URL containing '{expected_text}' not found in address bar within timeout."
                return JsonResponse({
                    "status": "timeout",
                    "message": message,
                    "matched_elements": matched_elements if debug else None,
                    "screenshot_url": screenshot_url
                })

            time.sleep(poll_interval / 1000.0)

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

            total_cases = len(testcase_ids)
            steps = list(testcase.steps.all())
            total_steps = len(steps)

            for step_index, step in enumerate(testcase.steps.all()):  # Ordered by step_number due to Meta
                # Wait between steps (skip for the first step)
                if step_index > 0:
                    time.sleep(wait_between_steps / 1000)  # Convert to seconds

                command = step.step_description
                click_x = step.step_coordinates.get('click_x') if step.step_coordinates else None
                click_y = step.step_coordinates.get('click_y') if step.step_coordinates else None

                # Check if this is the last step of the last case
                is_final_step = (case_index == total_cases - 1) and (step_index == total_steps - 1)

                try:
                    response = Execute_command_internal(command, user_id, click_x, click_y, is_final_step=is_final_step)

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
def Execute_command_internal(command, user_id, click_x, click_y, is_final_step):
    request_data = {
        "command": command,
        "user_id": user_id,
        "click_x": click_x,
        "click_y": click_y,
        "is_final_step":is_final_step
    }

    # Simulate request object
    fake_request = HttpRequest()
    fake_request.method = "POST"
    fake_request._body = json.dumps(request_data).encode("utf-8")

    return json.loads(Execute_command(fake_request).content.decode())



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


#for write manually step screen


# Set up logging
logger = logging.getLogger(__name__)

# Constants
BROWSER_PROCESS_NAMES = {
    "chrome.exe": "Google Chrome",
    "firefox.exe": "Mozilla Firefox",
    "msedge.exe": "Microsoft Edge",
    "brave.exe": "Brave",
    "opera.exe": "Opera",
    "safari.exe": "Safari"
}

# Map browser identifiers to their process names
BROWSER_IDENTIFIERS = {
    "Google Chrome": ["chrome", "chrome.exe"],
    "Mozilla Firefox": ["firefox", "firefox.exe"],
    "Microsoft Edge": ["msedge", "edge", "msedge.exe"],
    "Safari": ["safari", "safari.exe"],
    "Opera": ["opera", "opera.exe"],
    "Brave": ["brave", "brave.exe"]
}


def get_process_windows():
    """Get all windows mapped to their process names for more accurate detection."""
    windows_by_process = defaultdict(list)

    try:
        def enum_windows_proc(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    title = win32gui.GetWindowText(hwnd)

                    # Store window information
                    if title.strip():  # Only consider windows with non-empty titles
                        try:
                            window = gw.Window(hwnd)
                            windows_by_process[process_name].append({
                                "title": title,
                                "x": window.left,
                                "y": window.top,
                                "width": window.width,
                                "height": window.height,
                                "active": window == gw.getActiveWindow(),
                                "hwnd": hwnd,
                                "pid": pid
                            })
                        except Exception as e:
                            logger.warning(f"Error getting window details: {e}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                return True
            return True

        win32gui.EnumWindows(enum_windows_proc, 0)
    except Exception as e:
        logger.error(f"Error enumerating windows: {e}")

    return windows_by_process


def get_browser_windows():
    """Get all browser windows with their titles, with improved detection."""
    browser_windows = []
    try:
        # Get all windows by process
        windows_by_process = get_process_windows()

        # First, try to find browser windows by process name (most reliable)
        for process_name, process_windows in windows_by_process.items():
            for browser_process, browser_name in BROWSER_PROCESS_NAMES.items():
                if browser_process.lower() in process_name:
                    browser_windows.extend(process_windows)

        # As a fallback, check window titles as well
        all_windows = gw.getAllWindows()
        for window in all_windows:
            if window.title and any(browser in window.title for browser in BROWSER_IDENTIFIERS.keys()):
                # Check if window is already in our list
                if not any(w.get('hwnd') == window._hWnd for w in browser_windows):
                    browser_windows.append({
                        "title": window.title,
                        "x": window.left,
                        "y": window.top,
                        "width": window.width,
                        "height": window.height,
                        "active": window.isActive,
                        "hwnd": window._hWnd
                    })
    except Exception as e:
        logger.error(f"Error getting browser windows: {e}")

    return browser_windows


def multi_approach_focus_window(hwnd):
    """Use multiple approaches to focus a window reliably across different browsers."""
    try:
        # Approach 1: Standard Win32 API approach
        if win32gui.IsIconic(hwnd):  # If minimized
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        win32gui.SetForegroundWindow(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

        # Give it a moment
        time.sleep(0.5)

        # Check if successful
        if win32gui.GetForegroundWindow() == hwnd:
            return True

        # Approach 2: Using FlashWindow
        win32gui.FlashWindow(hwnd, True)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)

        if win32gui.GetForegroundWindow() == hwnd:
            return True

        # Approach 3: Using Windows shell
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')  # Alt key to help with focus
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)

        if win32gui.GetForegroundWindow() == hwnd:
            return True

        # Approach 4: Using another Win32 API method
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.SwitchToThisWindow(hwnd, True)
        time.sleep(0.5)

        return win32gui.GetForegroundWindow() == hwnd
    except Exception as e:
        logger.error(f"Error focusing window (hwnd={hwnd}): {e}")
        return False


def multi_approach_minimize_window(hwnd):
    """Use multiple approaches to minimize a window reliably across different browsers."""
    try:
        # Track if any of our approaches worked
        minimized = False

        # Approach 1: Standard Win32 API approach
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            time.sleep(0.5)
            minimized = win32gui.IsIconic(hwnd)
        except Exception as e:
            logger.debug(f"First minimize approach failed: {e}")

        # Approach 2: Try using SendMessage
        if not minimized:
            try:
                win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MINIMIZE, 0)
                time.sleep(0.5)
                minimized = win32gui.IsIconic(hwnd)
            except Exception as e:
                logger.debug(f"Second minimize approach failed: {e}")

        # Approach 3: Try using PostMessage
        if not minimized:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MINIMIZE, 0)
                time.sleep(0.5)
                minimized = win32gui.IsIconic(hwnd)
            except Exception as e:
                logger.debug(f"Third minimize approach failed: {e}")

        # Approach 4: Try using pygetwindow directly if available
        if not minimized:
            try:
                window = gw.Window(hwnd)
                window.minimize()
                time.sleep(0.5)
                minimized = win32gui.IsIconic(hwnd)
            except Exception as e:
                logger.debug(f"Fourth minimize approach failed: {e}")

        # Approach 5: Try using user32.dll directly
        if not minimized:
            try:
                user32 = ctypes.WinDLL('user32', use_last_error=True)
                user32.CloseWindow(hwnd)  # CloseWindow actually minimizes the window
                time.sleep(0.5)
                minimized = win32gui.IsIconic(hwnd)
            except Exception as e:
                logger.debug(f"Fifth minimize approach failed: {e}")

        return minimized
    except Exception as e:
        logger.error(f"Error minimizing window (hwnd={hwnd}): {e}")
        return False


def focus_window_by_title(title):
    """Focus a window by its title using multiple approaches."""
    try:
        # Try with direct window object first
        windows = gw.getAllWindows()
        for window in windows:
            if title in window.title:
                return multi_approach_focus_window(window._hWnd)

        # Try with win32gui as a backup
        def callback(hwnd, strings):
            if win32gui.IsWindowVisible(hwnd) and title in win32gui.GetWindowText(hwnd):
                strings.append(hwnd)
            return True

        found_hwnds = []
        win32gui.EnumWindows(callback, found_hwnds)

        if found_hwnds:
            return multi_approach_focus_window(found_hwnds[0])

        return False
    except Exception as e:
        logger.error(f"Error focusing window by title '{title}': {e}")
        return False


def get_active_windows_by_pid(pid):
    """Get all windows belonging to a specific process ID."""
    windows = []

    def callback(hwnd, windows_list):
        if win32gui.IsWindowVisible(hwnd):
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid == pid and win32gui.GetWindowText(hwnd).strip():
                windows_list.append(hwnd)
        return True

    win32gui.EnumWindows(callback, windows)
    return windows


def focus_browser_process_main_window(browser_name):
    """Find and focus the main window of a browser process."""
    try:
        # Get potential process names for this browser
        process_names = []
        for browser, identifiers in BROWSER_IDENTIFIERS.items():
            if browser_name.lower() in browser.lower():
                process_names.extend(identifiers)

        if not process_names:
            logger.warning(f"No process names found for browser: {browser_name}")
            return False

        # Find processes matching these names
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process_name = proc.info['name'].lower()
                if any(name.lower() in process_name for name in process_names):
                    # Get all windows for this process
                    windows = get_active_windows_by_pid(proc.info['pid'])

                    # Try to focus each window until one succeeds
                    for hwnd in windows:
                        if multi_approach_focus_window(hwnd):
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                continue

        return False
    except Exception as e:
        logger.error(f"Error focusing browser main window for {browser_name}: {e}")
        return False


@require_http_methods(["GET"])
def get_browser_tabs(request):
    """API to get all open browser tabs."""
    try:
        browser_windows = get_browser_windows()

        # Enhance the response with browser identification
        for window in browser_windows:
            # Try to identify the browser type based on process or title
            if 'pid' in window:
                try:
                    process = psutil.Process(window['pid'])
                    process_name = process.name().lower()
                    for browser_name, process_identifiers in BROWSER_IDENTIFIERS.items():
                        if any(identifier.lower() in process_name for identifier in process_identifiers):
                            window['browser_name'] = browser_name
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # If we couldn't identify by process, try by title
            if 'browser_name' not in window and 'title' in window:
                for browser_name in BROWSER_IDENTIFIERS.keys():
                    if browser_name.lower() in window['title'].lower():
                        window['browser_name'] = browser_name
                        break

            # If still not identified, mark as unknown
            if 'browser_name' not in window:
                window['browser_name'] = "Unknown Browser"

        return JsonResponse({
            "status": "success",
            "browser_tabs": browser_windows
        })
    except Exception as e:
        logger.error(f"Error in get_browser_tabs: {e}")
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def process_browser_tab(request):
    """API to focus on a specific browser tab, take screenshot, and minimize browser window."""
    try:
        data = json.loads(request.body)
        tab_title = data.get('tab_title')
        hwnd = data.get('hwnd')  # Window handle if available
        browser_name = data.get('browser_name')  # Optional browser name for fallback
        user_id = data.get('user_id', 'default')
        active_hwnd = None  # Store the activated window handle for later minimization

        if not tab_title and not hwnd and not browser_name:
            return JsonResponse({
                "status": "error",
                "message": "Either tab_title, hwnd, or browser_name is required"
            }, status=400)

        # Try multiple approaches to focus the window
        focused = False

        # Approach 1: Try with window handle (most reliable)
        if hwnd and not focused:
            try:
                hwnd_int = int(hwnd)
                focused = multi_approach_focus_window(hwnd_int)
                if focused:
                    active_hwnd = hwnd_int
                logger.info(f"Focus by hwnd ({hwnd_int}): {'Success' if focused else 'Failed'}")
            except ValueError:
                logger.warning(f"Invalid hwnd value: {hwnd}")

        # Approach 2: Try with window title
        if tab_title and not focused:
            focused = focus_window_by_title(tab_title)
            if focused:
                # Get the handle of the focused window
                active_hwnd = win32gui.GetForegroundWindow()
            logger.info(f"Focus by title ({tab_title}): {'Success' if focused else 'Failed'}")

        # Approach 3: Try with browser process name as fallback
        if browser_name and not focused:
            focused = focus_browser_process_main_window(browser_name)
            if focused:
                # Get the handle of the focused window
                active_hwnd = win32gui.GetForegroundWindow()
            logger.info(f"Focus by browser name ({browser_name}): {'Success' if focused else 'Failed'}")

        if not focused:
            return JsonResponse({
                "status": "error",
                "message": f"Could not focus requested window. Please ensure the browser is running."
            }, status=404)

        # Extra delay to ensure window is fully focused
        time.sleep(2)

        # Detect bookmark bar and hide it if visible
        if active_hwnd and is_chrome_bookmarks_bar_visible(active_hwnd):
            print("Bookmarks bar is visible. Sending Ctrl+Shift+B to hide it.")
            pyautogui.hotkey('ctrl', 'shift', 'b')
            time.sleep(1)  # Give time for UI to update
        else:
            print("Bookmarks bar not visible or detection failed.")

        # Take screenshot - calling your existing function
        screenshot_path, screenshot_url = take_screenshot(user_id)

        if not screenshot_path:
            return JsonResponse({
                "status": "error",
                "message": "Failed to take screenshot"
            }, status=500)

        # Now minimize the browser window after screenshot is taken
        minimized = False
        if active_hwnd:
            minimized = multi_approach_minimize_window(active_hwnd)
            logger.info(f"Window minimization: {'Success' if minimized else 'Failed'}")

        # Send to omniparser - calling your existing function
        omniparser_response = send_to_omniparser(screenshot_path)

        return JsonResponse({
            "status": "success",
            "message": "Screenshot captured successfully" +
                       (", browser minimized" if minimized else ", browser minimization failed"),
            "screenshot": screenshot_url,
            "omniparser_data": omniparser_response,
            "browser_minimized": minimized
        })
    except Exception as e:
        logger.error(f"Error in process_browser_tab: {e}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
    

