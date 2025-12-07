import sys
import os
import subprocess
import socket
import requests

def check_command(command, name):
    try:
        subprocess.run(command, capture_output=True, check=True)
        print(f"[+] {name}: INSTALLED ✅")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"[-] {name}: NOT FOUND or Error ❌")
        return False

def check_port(host, port, service_name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()
    if result == 0:
        print(f"[+] {service_name} (Port {port}): RUNNING ✅")
        return True
    else:
        print(f"[-] {service_name} (Port {port}): NOT DETECTED ❌")
        return False

print("--- FHIRGuard System Diagnostic ---")

# 1. Check Python
print(f"[*] Python: {sys.version.split()[0]}")

# 2. Check Java
check_command(["java", "-version"], "Java Runtime")

# 3. Check JAR File
jar_path = os.path.join("validator", "validator-wrapper.jar")
if os.path.exists(jar_path):
    print(f"[+] Validator JAR: FOUND ✅")
else:
    print(f"[-] Validator JAR: MISSING at {jar_path} ❌")

# 4. Check Redis (Required for Celery)
check_port("127.0.0.1", 6379, "Redis Server")

# 5. Check Java Validator Server (Is it running?)
try:
    # We try to hit the server just to see if it's up
    # Note: It might return 405 Method Not Allowed for GET, which is fine, it means it's up.
    r = requests.get("http://localhost:8082/", timeout=2)
    print("[+] Java Validator API: RESPONDING ✅")
except:
    print("[-] Java Validator API: NOT RESPONDING (Is Terminal 1 open?) ❌")

print("-----------------------------------")