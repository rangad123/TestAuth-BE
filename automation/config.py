import os
import sys
from django.conf import settings

# Determine Chrome browser path based on platform
BROWSER_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(BROWSER_PATH):
    BROWSER_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not os.path.exists(BROWSER_PATH):
    BROWSER_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if not os.path.exists(BROWSER_PATH):
    BROWSER_PATH = "/usr/bin/google-chrome"

# Media folder for screenshots
MEDIA_DIR = os.path.join(settings.MEDIA_ROOT, "screenshots")
os.makedirs(MEDIA_DIR, exist_ok=True)
