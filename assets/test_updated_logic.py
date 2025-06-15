#!/usr/bin/env python3

import subprocess
import re
import sys
import os
from collections import OrderedDict
from typing import Dict, Set, Tuple, Optional

# Add the current directory to the path to import from the main script
sys.path.insert(0, '/Users/steven/Projects/disable-macos-bloatware')

def get_uid():
    """Gets the UID of the current user, accounting for sudo."""
    # When running with sudo, we want the original user's UID, not root's
    if 'SUDO_UID' in os.environ:
        return int(os.environ['SUDO_UID'])
    return os.getuid()

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

def main():
    uid = get_uid()
    
    print("=== Testing Updated Service Discovery Logic ===")
    
    # Get daemon and agent data
    all_daemon_names = set()
    all_agent_names = set()
    daemon_pids = {}
    agent_pids = {}
    disabled_daemons = {}
    disabled_agents = {}
    
    try:
        # Get daemon list
        daemons_raw = subprocess.run(["sudo", "launchctl", "list"], capture_output=True, text=True, check=True).stdout
        for line in daemons_raw.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 3:
                all_daemon_names.add(parts[2])
                if parts[0] != "-":
                    daemon_pids[parts[2]] = parts[0]
        
        # Get daemon disabled status
        print_system_raw = subprocess.run(["sudo", "launchctl", "print", "system/"], capture_output=True, text=True, check=True).stdout
        names, statuses = parse_launchctl_print_output(print_system_raw)
        all_daemon_names.update(names)
        disabled_daemons.update(statuses)
        
        # Get agent list
        agents_raw = subprocess.run(["launchctl", "list"], capture_output=True, text=True, check=True).stdout
        for line in agents_raw.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 3:
                all_agent_names.add(parts[2])
                if parts[0] != "-":
                    agent_pids[parts[2]] = parts[0]
        
        # Get agent disabled status
        print_user_raw = subprocess.run(["launchctl", "print", f"user/{uid}"], capture_output=True, text=True, check=True).stdout
        names, statuses = parse_launchctl_print_output(print_user_raw)
        all_agent_names.update(names)
        disabled_agents.update(statuses)
        
        print(f"Daemons discovered: {len(all_daemon_names)}")
        print(f"Agents discovered: {len(all_agent_names)}")
        print(f"Daemon statuses: {len(disabled_daemons)}")
        print(f"Agent statuses: {len(disabled_agents)}")
        
        # Test specific services that we know should be disabled
        test_services = ['com.apple.assistant_service', 'com.apple.cloudphotod', 'com.apple.homed']
        
        print(f"\n=== Testing Specific Services ===")
        for name in test_services:
            print(f"\n--- {name} ---")
            
            daemon_details = None
            agent_details = None
            
            if name in all_daemon_names:
                daemon_details = get_service_details(name, "daemon", disabled_daemons, daemon_pids)
                print(f"Daemon: {daemon_details['status']}")
            else:
                print(f"Daemon: not found")
            
            if name in all_agent_names:
                agent_details = get_service_details(name, "agent", disabled_agents, agent_pids)
                print(f"Agent: {agent_details['status']}")
            else:
                print(f"Agent: not found")
            
            # Apply the new logic
            details = None
            service_type = None
            
            if daemon_details and agent_details:
                # Priority: running (0) > disabled (1) > enabled (2)
                daemon_priority = 0 if daemon_details['status'] == 'running' else (1 if daemon_details['status'] == 'disabled' else 2)
                agent_priority = 0 if agent_details['status'] == 'running' else (1 if agent_details['status'] == 'disabled' else 2)
                
                print(f"Daemon priority: {daemon_priority}, Agent priority: {agent_priority}")
                
                if agent_priority <= daemon_priority:
                    details = agent_details
                    service_type = "agent"
                else:
                    details = daemon_details
                    service_type = "daemon"
            elif agent_details:
                details = agent_details
                service_type = "agent"
            elif daemon_details:
                details = daemon_details
                service_type = "daemon"
            
            if details:
                print(f"Final choice: {service_type} with status {details['status']}")
                icon = "🟢" if details['status'] == 'running' else ("🔴" if details['status'] == 'disabled' else "🟡")
                print(f"TUI display: {icon} {name}")
            else:
                print(f"No details found")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
