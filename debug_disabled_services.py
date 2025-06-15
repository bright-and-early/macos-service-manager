#!/usr/bin/env python3

import subprocess
import re
from collections import OrderedDict
from typing import Dict, Set, Tuple, Optional

# Import the categorization map (simplified for testing)
test_services = ['com.apple.assistant_service', 'com.apple.cloudphotod', 'com.apple.homed']

# Simple test categorization
CATEGORIZATION_MAP = {
    "🗣️ Siri & Dictation": ["com.apple.assistant_service", "com.apple.assistantd"],
    "📷 Photos & Media": ["com.apple.cloudphotod", "com.apple.photoanalysisd"],
    "🏠 HomeKit": ["com.apple.homed"],
}

def get_uid():
    return subprocess.run(['id', '-u'], capture_output=True, text=True, check=True).stdout.strip()

def parse_launchctl_print_output(output: str) -> Tuple[Set[str], Dict[str, str]]:
    service_names = set()
    disabled_status = {}
    
    service_pattern = re.compile(r'^\s*[\d-]+\s+[\d-]+\s+([a-zA-Z0-9\._-]+)\s*$', re.MULTILINE)
    for match in service_pattern.finditer(output):
        service_names.add(match.group(1))
    
    disabled_section_match = re.search(r'disabled services = {([^}]+)}', output, re.DOTALL)
    if disabled_section_match:
        disabled_block = disabled_section_match.group(1)
        disabled_pattern = re.compile(r'"([^"]+)"\s*=>\s*(enabled|disabled)')
        for match in disabled_pattern.finditer(disabled_block):
            service_name, status = match.groups()
            disabled_status[service_name] = status
            service_names.add(service_name)
    
    return service_names, disabled_status

def get_service_details(service_name: str, service_type: str, statuses: Dict[str, str], pids: Dict[str, str]) -> Optional[Dict]:
    if service_name in pids:
        status = "running"
    elif service_name in statuses:
        if statuses[service_name] == "disabled":
            status = "disabled"
        else:
            status = "enabled"
    else:
        status = "enabled"
    
    return {
        "status": status,
        "description": f"Test description for {service_name}",
        "impact": f"Test impact for {service_name}",
        "type": service_type,
    }

def categorize_service(service_name: str) -> str:
    for category, service_list in CATEGORIZATION_MAP.items():
        if service_name in service_list:
            return category
    if "com.apple" not in service_name:
        return "🧩 Third-Party"
    return "❓ Undocumented"

def main():
    uid = get_uid()
    
    print("=== Testing disabled services pipeline ===")
    
    # Get user services
    try:
        print_user_raw = subprocess.run(['launchctl', 'print', f'user/{uid}'], capture_output=True, text=True, check=True).stdout
        user_names, user_statuses = parse_launchctl_print_output(print_user_raw)
        
        print(f"Total user services discovered: {len(user_names)}")
        print(f"User services with status info: {len(user_statuses)}")
        
        # Test specific services
        for test_service in test_services:
            print(f"\n--- Testing {test_service} ---")
            
            if test_service in user_names:
                print(f"✓ Found in discovered services")
            else:
                print(f"✗ NOT found in discovered services")
            
            if test_service in user_statuses:
                print(f"✓ Has status: {user_statuses[test_service]}")
            else:
                print(f"✗ No status information")
            
            # Test service details
            details = get_service_details(test_service, "agent", user_statuses, {})
            if details:
                print(f"✓ Service details: status={details['status']}")
                
                # Test categorization
                category = categorize_service(test_service)
                print(f"✓ Categorized as: {category}")
            else:
                print(f"✗ Failed to get service details")
        
        # Count disabled services by category
        print(f"\n=== Disabled services by category ===")
        categorized_disabled = {}
        
        for service_name in user_names:
            if service_name in user_statuses and user_statuses[service_name] == "disabled":
                category = categorize_service(service_name)
                if category not in categorized_disabled:
                    categorized_disabled[category] = []
                categorized_disabled[category].append(service_name)
        
        for category, services in categorized_disabled.items():
            print(f"{category}: {len(services)} disabled services")
            for service in services[:3]:  # Show first 3
                print(f"  - {service}")
            if len(services) > 3:
                print(f"  ... and {len(services) - 3} more")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
