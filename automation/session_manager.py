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

user_sessions = {}  # {user_id: {'last_active': timestamp, 'windows': {url: {'title': window_title, 'hwnd': handle, 'pid': process_id}}}}
SESSION_TIMEOUT = 600  # 10 minutes

# Thread safety lock
lock = threading.Lock()
stop_event = threading.Event()  # Allows graceful stopping


def cleanup_inactive_sessions():
    """Clean up inactive user sessions"""
    current_time = time.time()
    with lock:
        for user_id, session_data in list(user_sessions.items()):
            if current_time - session_data.get('last_active', 0) > SESSION_TIMEOUT:
                print(f"[INFO] Removing inactive session for user {user_id}")
                del user_sessions[user_id]


def periodic_cleanup():
    """Run cleanup periodically in the background"""
    while not stop_event.is_set():
        cleanup_inactive_sessions()
        stop_event.wait(300)  # Wait 5 minutes between cleanups


def stop_cleanup():
    """Gracefully stop the cleanup thread"""
    print("Stopping cleanup thread...")
    stop_event.set()
    cleanup_thread.join()


# Start cleanup thread
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

# Register cleanup function
atexit.register(stop_cleanup)
