import platform
import psutil
import socket
import requests
import uuid
import json
import os
from screeninfo import get_monitors

# Backend API URL
BACKEND_URL = "https://api.testerally.ai/api/track-download/"

# File to store agent ID persistently
AGENT_FILE = "agent_id.txt"


def get_system_info():
    """Get full system details."""
    try:
        screen = get_monitors()[0]  # Get primary monitor resolution
        screen_resolution = f"{screen.width}x{screen.height}"
    except Exception as e:
        print(f"⚠️ Error getting screen resolution: {str(e)}")
        screen_resolution = "Unknown"

    system_info = {
        "os_name": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "cpu": platform.processor(),
        "ram": psutil.virtual_memory().total // (1024 ** 3),  # in GB
        "screen_resolution": screen_resolution,
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "mac_address": ":".join(
            ["{:02x}".format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 8)][::-1]),
    }

    return system_info


def get_user_id():
    """Retrieve the user ID from an environment variable or a local file."""
    user_id = os.getenv("USER_ID")

    if not user_id:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                try:
                    config = json.load(f)
                    user_id = config.get("user_id")
                    if user_id:  # Only return if it has a valid value
                        return user_id
                except json.JSONDecodeError:
                    print("⚠️ Warning: Invalid config.json file format.")

    return None  # Return None instead of "unknown"


def get_agent_id():
    """Retrieve or generate a unique agent ID."""
    if os.path.exists(AGENT_FILE):
        with open(AGENT_FILE, "r") as f:
            return f.read().strip()

    agent_id = str(uuid.uuid4())  # Generate new unique agent ID
    with open(AGENT_FILE, "w") as f:
        f.write(agent_id)  # Save it for future use

    return agent_id


def send_system_info():
    """Collect system info and send it to the backend."""
    user_id = get_user_id()
    agent_id = get_agent_id()

    system_info = get_system_info()
    # Only add user_id if it's not None
    if user_id is not None:
        system_info["user_id"] = user_id
    system_info["agent_id"] = agent_id

    print("📡 Sending System Info to Backend:")
    print(json.dumps(system_info, indent=4))  # Debugging output

    try:
        response = requests.post(BACKEND_URL, json=system_info, timeout=10)
        if response.status_code in [200, 201]:
            print("✅ System info sent successfully!")
        else:
            print(f"❌ Failed to send system info: {response.text}")
    except requests.RequestException as e:
        print(f"❌ Network error: {str(e)}")


if __name__ == "__main__":  # Fixed double underscore syntax
    send_system_info()