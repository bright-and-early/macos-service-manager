# macos-service-manager

## Description

This is a simple service manager for macOS that allows you to start, stop, and restart services. It is designed to be easy to use and provides a straightforward way to manage services on your macOS system.

## Screenshots

**Service categories**
![Service categories](./assets/categories.png)

**Running, Enabled, and Disabled Services**
![Service List](./assets/service-list.png)

**Service Details & Critical Services**
![Critical Services](./assets/critical.png)

## Features

- Start, stop, and restart services
- List loaded launchd jobs and saved launch overrides in system, GUI, and user domains
- Distinguish running processes, loaded idle jobs, and saved launch policy
- User-friendly TUI (Text User Interface)

## Requirements

- Python 3.x

## Installation

1. Leave **SIP (System Integrity Protection)** enabled. Browsing and managing unprotected services does not require disabling SIP; macOS can reject changes to protected jobs.
2. Clone the repository:

```bash
git clone https://github.com/bright-and-early/macos-service-manager.git
```

3. Navigate to the project directory:

```bash
cd macos-service-manager
```

4. Create a virtual environment and install the required dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

5. Run the service manager (it needs root to manage system services, so point `sudo` at the virtual environment's interpreter):

```bash
sudo .venv/bin/python3 manage-services.tui.py
```

## Applying changes

Select a service, press **Space** to toggle its pending enabled/disabled state,
then press **Enter** and confirm with **y**. Disabling first records the persistent
launchd override, then unloads the job from its discovered domain (`system`,
`gui/<uid>`, or `user/<uid>`). The manager verifies both results before reporting
success. Errors remain visible until you press a key; a rescan shows actual state.
Enabling removes the disabled override; it does not immediately load or start
an unloaded service. The service can load again at login/reboot or through its
normal launch mechanism.

The list contains services and overrides discovered on this Mac. The description
database supplies metadata and does not prove that a service is installed.
Services sharing a label across domains appear separately with their domains.

The list shows **running** when launchd reports a positive PID, **loaded** for
an idle loaded job, **disabled** for a disabled launch policy without a running
process, and **not loaded** for an enabled or unknown-policy override without a
loaded job. Launch policy is shown separately: saved overrides take precedence
over a matching plist's `Disabled` default. When the override query or matching
configuration is unavailable, policy remains **unknown** instead of assuming
enabled. A saved override can outlive an uninstalled app; the Details panel
identifies override-only entries and does not claim they are installed.

Use **Page Up/Page Down** to scroll long Details panels; selecting a different
service returns Details to the top.

Details include the domain, PID, and matching configuration/program when available.
Configuration lookup uses the plist's `Label`, not its filename. Plists are
supporting evidence, not extra list entries, and unrecognized or unreadable
configuration files are skipped. User-domain jobs without a matching verified
configuration retain unknown default policy.

Descriptions with checked sources show the source in Details. Other descriptions
are explicitly marked as historical local metadata that has not been independently
verified. All disabling impacts are estimates, not guarantees. The checked
corrections include Trial framework services, Dwell, Apple TV support, and UARP
helpers. Categories are a local organizational aid, not an Apple classification.
This is not an exhaustive inventory of every executable or bundled XPC service.
macOS can reject changes to protected services; the manager displays that error.

Run regression tests with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

An optional live smoke check creates a disposable user agent, disables/unloads it,
verifies enabling and reloading, then removes its job and temporary plist (an
enabled override for the test label remains):

```bash
.venv/bin/python tests/live_service_check.py
```

Recorded live verification: [launchctl smoke check](artifacts/launchctl-smoke-check.svg).

Read-only inventory and rendered TUI evidence: [inventory check](artifacts/service-inventory-check.txt), [Trial details](artifacts/service-details-trial.svg), [running service details](artifacts/service-details-running.svg).
