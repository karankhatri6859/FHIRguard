import sys
import os

print("--- Python Environment Diagnostic ---")
print(f"[*] Python Executable Being Used: {sys.executable}")
print("\n[*] Python is searching for modules in these paths (sys.path):")
for i, path in enumerate(sys.path):
    print(f"    {i}: {path}")

print("\n--- Analysis ---")
venv_site_packages = os.path.join(os.path.dirname(sys.executable), '..', 'Lib', 'site-packages')
site_packages_found = any(os.path.normcase(p) == os.path.normcase(venv_site_packages) for p in sys.path)

if 'venv' in sys.executable:
    print("[+] SUCCESS: The script is being run by a Python from your 'venv' folder.")
else:
    print("[-] PROBLEM: The script is being run by your GLOBAL Python, not the one in the 'venv'.")

if site_packages_found:
    print("[+] SUCCESS: The venv's 'site-packages' directory (where libraries are installed) is in the search path.")
else:
    print("[-] PROBLEM: The venv's 'site-packages' directory IS NOT in the search path.")
    print(f"    (It expected to find a path like: {venv_site_packages})")
    
print("-----------------------------------")