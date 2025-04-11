import os
import subprocess
import sys
import webbrowser
import time
import atexit

# Get the directory of the executable
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)  # When running as .exe
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))  # When running as script

os.chdir(base_dir)

# Correcting the path to `manage.exe`
manage_exe_path = os.path.join(base_dir, 'manage.exe')

# Debugging: Print the path to verify correctness
print(f"Starting Django server using: {manage_exe_path}")

# Check if manage.exe exists before running
if not os.path.exists(manage_exe_path):
    print(f"Error: {manage_exe_path} not found! Make sure it's inside the dist/ folder.")
    sys.exit(1)

# Start Django server with unbuffered output
server_process = subprocess.Popen(
    [manage_exe_path, 'runserver', '--noreload'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

print("Django server is starting...")

# Wait for the server to start
time.sleep(10)

# Open the browser only if the server is running
if server_process.poll() is None:
    webbrowser.open('http://127.0.0.1:8000/')
else:
    print("Error: Django server failed to start!")
    sys.exit(1)

# Ensure process is cleaned up on exit
def cleanup():
    if server_process.poll() is None:  # Check if process is still running
        server_process.terminate()
        print("\nServer terminated.")

atexit.register(cleanup)

# Read and print output in real-time
try:
    for line in server_process.stdout:
        print(line, end='', flush=True)
except KeyboardInterrupt:
    print("\nShutting down...")
    server_process.terminate()


