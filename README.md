# macos-service-manager

## Description

This is a simple service manager for macOS that allows you to start, stop, and restart services. It is designed to be easy to use and provides a straightforward way to manage services on your macOS system.

## Screenshots

![Service categories](./assets/categories.png)
![Service List](./assets/service-list.png)
![Critical Services](./assets/critical.png)

## Features

- Start, stop, and restart services
- List all available services
- Check the status of services
- User-friendly TUI (Text User Interface)

## Requirements

- Python 3.x

## Installation

1. Clone the repository:

```bash
git clone https://github.com/bright-and-early/macos-service-manager.git
```

2. Navigate to the project directory:

```bash
cd macos-service-manager
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

 4. Run the service manager:

```bash
sudo python3 manage-services.tui.py
```
