#!/usr/bin/env python3

import subprocess
import re
from collections import OrderedDict

def get_uid():
    return subprocess.run(['id', '-u'], capture_output=True, text=True, check=True).stdout.strip()

def main():
    uid = get_uid()
    
    # Get user services and their statuses
    print_user_raw = subprocess.run(['launchctl', 'print', f'user/{uid}'], capture_output=True, text=True, check=True).stdout
    
    # Parse running services
    agents_raw = subprocess.run(['launchctl', 'list'], capture_output=True, text=True, check=True).stdout
    running_services = set()
    for line in agents_raw.strip().split('\n')[1:]:
        parts = line.split()
        if len(parts) >= 3 and parts[0] != '-':
            running_services.add(parts[2])
    
    # Parse disabled services
    disabled_section_match = re.search(r'disabled services = {([^}]+)}', print_user_raw, re.DOTALL)
    disabled_services = {}
    if disabled_section_match:
        disabled_block = disabled_section_match.group(1)
        disabled_pattern = re.compile(r'"([^"]+)"\s*=>\s*(enabled|disabled)')
        for match in disabled_pattern.finditer(disabled_block):
            service_name, status = match.groups()
            disabled_services[service_name] = status
    
    print("=== Service Status Summary ===")
    print(f"Running services (with PID): {len(running_services)}")
    print(f"Services in disabled section: {len(disabled_services)}")
    
    # Count by actual status
    running_count = len(running_services)
    explicitly_disabled = len([s for s, status in disabled_services.items() if status == 'disabled'])
    explicitly_enabled = len([s for s, status in disabled_services.items() if status == 'enabled'])
    
    print(f"\\nActual status breakdown:")
    print(f"🟢 Running: {running_count}")
    print(f"🟡 Explicitly enabled (not running): {explicitly_enabled}")
    print(f"🔴 Explicitly disabled: {explicitly_disabled}")
    
    print(f"\\n=== Sample Disabled Services ===")
    disabled_only = [name for name, status in disabled_services.items() if status == 'disabled']
    for service in disabled_only[:10]:
        print(f"🔴 {service}")
    
    print(f"\\n=== Sample Running Services ===")
    for service in list(running_services)[:5]:
        print(f"🟢 {service}")

if __name__ == "__main__":
    main()
