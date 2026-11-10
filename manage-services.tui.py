#!/usr/bin/env python3
# pylint: disable=line-too-long

import os
import plistlib
import pwd
from pathlib import Path
from xml.parsers.expat import ExpatError
import re
import subprocess
import sys
import termios
import time
import tty
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple
import threading

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table
from rich.text import Text

# --- Service Details Database ---
# Historical descriptions are not independently verified unless a source is listed below.
SERVICE_DATABASE = {
  # Accessibility
  "com.apple.accessibility.MotionTrackingAgent": {
    "description": "Related to accessibility features that involve motion tracking, such as Head Pointer.",
    "impact": "Disabling will prevent the use of accessibility features that rely on tracking user motion.",
  },
  "com.apple.accessibility.axassetsd": {
    "description": "Manages accessibility assets and resources used by various accessibility features.",
    "impact": "Accessibility features may function incorrectly or fail to load necessary resources.",
  },
  "com.apple.universalaccessd": {
    "description": "A core daemon for Universal Access, providing features for users with disabilities.",
    "impact": "Will likely break most accessibility features, such as VoiceOver, Zoom, and Switch Control.",
  },
  "com.apple.voicebankingd": {
    "description": "Manages the creation and use of personal voices for accessibility features like Personal Voice.",
    "impact": "You will not be able to create or use a Personal Voice for text-to-speech.",
  },
  "com.apple.AXMediaUtilitiesService": {
    "description": "Provides accessibility services for media content, such as descriptions for the visually impaired.",
    "impact": "Media-related accessibility features may not function correctly.",
  },
  "com.apple.accessibility.mediaaccessibilityd": {
    "description": "Daemon for Media Accessibility, providing features like subtitles, captions, and audio descriptions.",
    "impact": "Subtitles, closed captions, and other media-related accessibility features may not work.",
  },
  "com.apple.accessibility.heard": {
    "description": "Part of the 'Sound Recognition' accessibility feature, which listens for specific sounds and notifies the user.",
    "impact": "The 'Sound Recognition' feature will not function.",
  },
  "com.apple.universalaccessAuthWarn": {
    "description": "Shows an authentication warning related to Universal Access features.",
    "impact": "System warnings for accessibility features may not appear.",
  },
  "com.apple.accessibility.LiveTranscriptionAgent": {
    "description": "Manages the Live Transcription feature for audio.",
    "impact": "Live Transcription for audio content will not function.",
  },
  "com.apple.accessibility.AXVisualSupportAgent": {
    "description": "Provides visual support services for various accessibility features.",
    "impact": "Visual accessibility aids may not function correctly.",
  },
  "com.apple.universalaccesscontrol": {
    "description": "Daemon for managing Universal Access controls.",
    "impact": "Core accessibility control features will be disabled.",
  },
  "com.apple.AccessibilityUIServer": {
    "description": "User interface server for accessibility features.",
    "impact": "The UI components of accessibility features like VoiceOver or Zoom may not display correctly.",
  },
  "com.apple.DwellControl": {
    "description": 'Supports Dwell actions, which perform a click or another action when the pointer stays still for a configured time.',
    "impact": 'Disabling may prevent Dwell actions used with the Accessibility Keyboard.',
  },
  "com.apple.VoiceOver": {
    "description": "The core screen reader service for macOS.",
    "impact": "The VoiceOver screen reader will be completely disabled.",
  },
  "com.apple.ScreenReaderUIServer": {
    "description": "User interface server for the screen reader (VoiceOver).",
    "impact": "The visual interface for VoiceOver will not function.",
  },
  "com.apple.AssistiveControl": {
    "description": "Service for the Assistive Control feature, allowing use of adaptive accessories.",
    "impact": "Will disable the ability to use switch controls and other assistive devices.",
  },
  "com.apple.KeyboardAccessAgent": {
    "description": "Agent for Keyboard Access features, allowing full control of the UI from the keyboard.",
    "impact": "Full Keyboard Access and other keyboard-related accessibility features will not work.",
  },
  "com.apple.accessibility.dfrhud": {
    "description": "Manages the accessibility Heads-Up Display (HUD) for the Touch Bar (DFR).",
    "impact": "Accessibility features related to the Touch Bar will not work.",
  },
  # Advertising & Analytics
  "com.apple.ap.adprivacyd": {
    "description": "Part of Apple's advertising framework; manages ad privacy and tracking settings.",
    "impact": "May interfere with the system's ability to respect your ad tracking preferences.",
  },
  "com.apple.ap.promotedcontentd": {
    "description": "Fetches and displays promoted content within Apple's applications like the App Store.",
    "impact": "Will likely prevent the display of promoted or featured content in various Apple apps.",
  },
  "com.apple.adid": {
    "description": "Manages the advertising identifier (IDFA) used for tracking in apps.",
    "impact": "May affect ad tracking and personalization in apps.",
  },
  "com.apple.parsec-fbf": {
    "description": "Responsible for periodic flushing and uploading of Siri Search analytics data.",
    "impact": "Disabling this will stop the system from sending Siri Search analytics to Apple.",
  },
  "com.apple.analyticsd": {
    "description": "The main daemon for capturing and reporting diagnostic and usage data to Apple.",
    "impact": "No diagnostic or usage data will be sent to Apple. This may be desirable for privacy.",
  },
  "com.apple.osanalytics.osanalyticshelper": {
    "description": "A helper for the OS analytics daemon (analyticsd). It gathers system logs and diagnostics that feed Apple's analytics reporting.",
    "impact": "May prevent certain system-level diagnostic data from being collected.",
  },
  "com.apple.symptomsd": {
    "description": "Related to network diagnostics and analytics.",
    "impact": "May affect the system's ability to diagnose network issues.",
  },
  "com.apple.wifianalyticsd": {
    "description": "Daemon for collecting Wi-Fi diagnostics and analytics.",
    "impact": "No Wi-Fi analytics will be sent to Apple.",
  },
  "com.apple.audioanalyticsd": {
    "description": "Daemon for collecting audio system diagnostics and analytics.",
    "impact": "No audio-related analytics will be sent to Apple.",
  },
  "com.apple.ecosystemanalyticsd": {
    "description": "Analyzes interactions within the Apple device ecosystem for diagnostic purposes.",
    "impact": "No ecosystem-related analytics will be sent to Apple.",
  },
  "com.apple.perfpowermetricd": {
    "description": "Collects performance and power metrics for analytics.",
    "impact": "No performance and power analytics will be sent to Apple.",
  },
  "com.apple.metrickitd": {
    "description": "Gathers and reports aggregated performance and usage metrics from apps for developers.",
    "impact": "Developers will not receive MetricKit reports for their apps from your device.",
  },
  "com.apple.analyticsagent": {
    "description": "User-level agent for collecting and reporting diagnostic and usage data.",
    "impact": "No diagnostic or usage data from the user session will be sent to Apple.",
  },
  "com.apple.dprivacyd": {
    "description": "Daemon related to Differential Privacy, a technique for collecting anonymized usage data.",
    "impact": "The system will not contribute to Apple's differential privacy data sets.",
  },
  "com.apple.PerfPowerTelemetryClientRegistrationService": {
    "description": "A service for registering clients to receive performance and power telemetry data.",
    "impact": "The system and applications will not be able to collect performance and power usage data for analytics.",
  },
  "com.apple.memoryanalyticsd": {
    "description": "A daemon that collects analytics on memory usage.",
    "impact": "The system will not collect memory usage data for diagnostics and analytics.",
  },
  # App & Store Related
  "com.apple.appstoreagent": {
    "description": "An agent that supports the App Store, handling downloads, installations, and updates initiated by the user.",
    "impact": "The App Store may not be able to download, install, or update applications correctly.",
  },
  "com.apple.appstored": {
    "description": "The main daemon for the Mac App Store, handling background tasks related to app updates and licensing.",
    "impact": "Automatic app updates will not work, and there may be issues with purchased app validation.",
  },
  "com.apple.commerce": {
    "description": "A core agent for handling App Store transactions, in-app purchases, and license validation.",
    "impact": "CRITICAL: The App Store will not function. You will not be able to purchase, update, or restore apps.",
  },
  "com.apple.passd": {
    "description": "A daemon that manages passes in Wallet and handles Apple Pay functionality.",
    "impact": "Apple Pay and Wallet functionality will not work.",
  },
  "com.apple.financed": {
    "description": "A background daemon for Apple Pay and Wallet services.",
    "impact": "Apple Pay and Wallet functionality, including managing cards and passes, will not work.",
  },
  "com.apple.watchlistd": {
    "description": 'Provides support for the Apple TV app.',
    "impact": 'Disabling may affect Apple TV app functionality. The manual does not specify all affected features.',
  },
  "com.apple.triald.system": {
    "description": 'System service for Apple’s Trial framework, launched as triald_system.',
    "impact": 'Disabling may interfere with system Trial tasks. The installed launch configuration does not document the full effects.',
  },
  "com.apple.newsd": {
    "description": "Daemon for the Apple News service.",
    "impact": "Apple News content and widgets will not update.",
  },
  "com.apple.appinstalld": {
    "description": "Handles requests for app installation.",
    "impact": "Apps may fail to install correctly.",
  },
  "com.apple.assetsubscriptiond": {
    "description": "Manages subscriptions to content assets.",
    "impact": "Content subscriptions in apps like News or TV may not work.",
  },
  "com.apple.bookassetd": {
    "description": "Manages assets for the Books app.",
    "impact": "Books and audiobooks may not download or display correctly.",
  },
  "com.apple.storeaccountd": {
    "description": "Manages App Store account information.",
    "impact": "You may have issues signing into or managing your App Store account.",
  },
  "com.apple.storeuid": {
    "description": "Provides user interface elements for the App Store.",
    "impact": "App Store dialogs and notifications may not appear.",
  },
  "com.apple.storedownloadd": {
    "description": "Manages downloads from the App Store.",
    "impact": "App downloads and updates may fail.",
  },
  "com.apple.appsleep": {
    "description": "Part of the system's app lifecycle and power management. It tracks app sleep state so inactive apps can be suspended efficiently (related to App Nap).",
    "impact": "Inactive apps may not be suspended as efficiently, which can increase power usage.",
  },
  "com.apple.storekitagent": {
    "description": "Agent for StoreKit, handling in-app purchases and interactions with the App Store.",
    "impact": "In-app purchases will not work.",
  },
  "com.apple.appplaceholdersyncd": {
    "description": "Syncs app placeholder records so apps can be restored or re-downloaded on a new device or after a reinstall.",
    "impact": "Setting up a new Mac from a backup might not correctly show all installing apps.",
  },
  "com.apple.askpermissiond": {
    "description": "Manages 'Ask to Buy' requests for Family Sharing.",
    "impact": "'Ask to Buy' notifications and purchase approvals will not function.",
  },
  "com.apple.amsondevicestoraged": {
    "description": "Apple Media Services on-device storage management.",
    "impact": "May affect how media and App Store data is stored and managed.",
  },
  "com.apple.amsaccountsd": {
    "description": "Manages accounts for Apple Media Services (App Store, Music, TV).",
    "impact": "Account-related features in media apps may fail.",
  },
  "com.apple.amsengagementd": {
    "description": "Handles user engagement features for Apple Media Services.",
    "impact": "Promotional content or user engagement prompts in media apps may not work.",
  },
  "com.apple.AppStoreDaemon.StorePrivilegedODRService": {
    "description": "Handles On-Demand Resources (ODR) for App Store applications, allowing apps to download content as needed.",
    "impact": "Apps that use On-Demand Resources may fail to download additional content, leading to incomplete functionality."
  },
  "com.apple.AppStoreDaemon.StorePrivilegedTaskService": {
    "description": "Performs privileged tasks for the App Store daemon, such as installations and updates that require higher permissions.",
    "impact": "The App Store may fail to install or update applications, particularly those requiring system-level changes."
  },
  "com.apple.eligibilityd": {
    "description": "A daemon that determines if the device is eligible for certain services or features.",
    "impact": "You may not be able to access certain Apple services if your device cannot be verified as eligible."
  },
  "com.apple.fairplayd": {
    "description": "The daemon for FairPlay, Apple's digital rights management (DRM) technology.",
    "impact": "You will not be able to play DRM-protected content from the iTunes Store or Apple Music."
  },
  "com.apple.fairplaydeviceidentityd": {
    "description": "A daemon that manages the device's identity for FairPlay DRM.",
    "impact": "Similar to `fairplayd`, this is critical for playing DRM-protected content."
  },
  "com.apple.storereceiptinstaller": {
    "description": "A tool that installs receipts for App Store purchases.",
    "impact": "The system may not correctly record the receipts for your purchased applications, potentially causing licensing issues."
  },
  # Backup & Time Machine
  "com.apple.backupd": {
    "description": "The primary daemon for Time Machine, responsible for coordinating and executing backups.",
    "impact": "Disabling this will prevent Time Machine from running automatically. Manual backups may also fail. Your system will not be backed up.",
  },
  "com.apple.backupd-helper": {
    "description": "A helper daemon for Time Machine that assists with various pre-backup and post-backup tasks.",
    "impact": "Disabling this may cause Time Machine backups to fail or not complete successfully. It is a required component for Time Machine to function.",
  },
  "com.apple.TMHelperAgent": {
    "description": "A menu-bar helper for Time Machine. It shows backup status and lets you start or stop backups.",
    "impact": "Time Machine backups may not run automatically or may encounter errors. Status updates may not be shown.",
  },
  "com.apple.mbsystemadministration": {
    "description": "Handles system administration tasks related to Mobile Backup (mb), a component of the Time Machine backup system.",
    "impact": "Disabling this could interfere with Time Machine's ability to properly manage backup sets.",
  },
  "com.apple.mbfloagent": {
    "description": "A Mobile Backup flow agent. It coordinates backup data transfer between this Mac and connected iOS devices.",
    "impact": "Time Machine backups may fail or become corrupted.",
  },
  "com.apple.mbbackgrounduseragent": {
    "description": "A user agent for running Time Machine tasks in the background.",
    "impact": "Automatic Time Machine backups are likely to fail.",
  },
  "com.apple.mbuseragent": {
    "description": "A user agent for Mobile Backup (Time Machine) operations.",
    "impact": "Time Machine may not function correctly, especially manual backups.",
  },
  "com.apple.vsdbutil": {
    "description": "The Volume Status Database utility. It maintains /var/db/volinfo.database, which records per-volume ownership and mount behavior (for example ignoring ownership on external disks).",
    "impact": "Changes to volume ownership/permission handling may not persist. It is safe to leave enabled."
  },
  "com.apple.mbusertrampoline": {
    "description": "The Mobile Backup user trampoline. It launches the per-user backup agent with the correct identity and environment.",
    "impact": "Time Machine backups may fail."
  },
  # Calendar & Reminders
  "com.apple.calaccessd": {
    "description": "Provides other processes with access to the Calendar database.",
    "impact": "Widgets and other apps will not be able to display calendar information.",
  },
  "com.apple.remindd": {
    "description": "The main daemon for the Reminders app, managing all reminder data and notifications.",
    "impact": "The Reminders app and its widgets will not function or sync.",
  },
  "com.apple.CallHistoryPluginHelper": {
    "description": "A helper for accessing the call history from your iPhone.",
    "impact": "Recent calls from your iPhone will not appear on your Mac.",
  },
  "com.apple.dataaccess.dataaccessd": {
    "description": "A daemon that syncs calendar and contacts data with various non-iCloud servers (like Google or Exchange).",
    "impact": "Calendar and contact syncing for non-iCloud accounts will stop working.",
  },
  "com.apple.followupd": {
    "description": "A daemon for the 'Follow Up' feature in Mail and other apps.",
    "impact": "Follow Up suggestions in Mail will not be created.",
  },
  "com.apple.callhistoryd": {
    "description": "The main daemon for managing the call history database.",
    "impact": "The system will not be able to save or retrieve call history.",
  },
  "com.apple.CallHistorySyncHelper": {
    "description": "Helper for syncing call history across devices via iCloud.",
    "impact": "Call history will not sync between your Apple devices.",
  },
  "com.apple.exchange.exchangesyncd": {
    "description": "Handles syncing of data with Microsoft Exchange servers.",
    "impact": "Mail, Calendar, and Contacts syncing with Exchange accounts will fail.",
  },
  "com.apple.notes.exchangenotesd": {
    "description": "Specifically handles syncing Notes with Microsoft Exchange servers.",
    "impact": "Notes will not sync with Exchange accounts.",
  },
  # Device Communication
  "com.apple.bluetoothd": {
    "description": "The core system daemon that manages all Bluetooth connections and services.",
    "impact": "All Bluetooth functionality will cease. Keyboards, mice, trackpads, headphones, and other Bluetooth devices will not work.",
  },
  "com.apple.nearbyd": {
    "description": "Manages discovery of and communication with nearby devices for features like AirDrop, Handoff, and AirPlay.",
    "impact": "Will break most Continuity features. AirDrop, Handoff, and connecting to nearby devices will fail.",
  },
  "com.apple.rapportd": {
    "description": "Core daemon for the 'Continuity' framework. Manages communication between nearby Apple devices.",
    "impact": "Breaks Handoff, AirDrop, Universal Clipboard, and taking iPhone calls/SMS on your Mac.",
  },
  "com.apple.sidecar-relay": {
    "description": "The main relay service for Sidecar, which allows you to use your iPad as a second display.",
    "impact": "The Sidecar feature will not work.",
  },
  "com.apple.usbmuxd": {
    "description": "Daemon for multiplexing connections over USB to iOS devices. Essential for syncing, updating, and debugging iPhones/iPads with Finder/Xcode.",
    "impact": "CRITICAL: You will not be able to connect and manage iOS devices via USB.",
  },
  "com.apple.CommCenter-osx": {
    "description": "Part of the CoreTelephony framework, responsible for handling cellular-related features like making calls through your iPhone.",
    "impact": "iPhone Cellular Calls, SMS relay, and Instant Hotspot features will not work.",
  },
  "com.apple.imagent": {
    "description": "The core agent for the iMessage and FaceTime services.",
    "impact": "You will not be able to sign into or use iMessage and FaceTime.",
  },
  "com.apple.imtransferagent": {
    "description": "Handles file transfers for the iMessage service.",
    "impact": "You will not be able to send or receive files, photos, or videos in iMessage.",
  },
  "com.apple.telephonyutilities.callservicesd": {
    "description": "The system daemon responsible for maintaining the state of phone calls (including FaceTime and iPhone Handoff calls).",
    "impact": "The ability to make and receive calls on the Mac will be broken.",
  },
  "com.apple.imcore.imtransferagent": {
    "description": "A core process for iMessage file transfers.",
    "impact": "You will not be able to send or receive files, photos, or videos in iMessage.",
  },
  "com.apple.syncservices.uihandler": {
    "description": "Handles the user interface for the legacy Sync Services framework.",
    "impact": "Legacy sync features, if any apps still use them, will not work.",
  },
  "com.apple.AddressBook.SourceSync": {
    "description": "A legacy agent for syncing contacts.",
    "impact": "May affect contact syncing for older or third-party account types.",
  },
  "com.apple.bluetoothuserd": {
    "description": "User-level daemon for managing Bluetooth services and connections.",
    "impact": "Bluetooth functionality, especially pairing and device management, may be impaired.",
  },
  "com.apple.bluetoothUIServer": {
    "description": "Provides user interface elements for Bluetooth, such as pairing requests.",
    "impact": "You may not see pairing requests or other Bluetooth-related dialogs.",
  },
  "com.apple.CommCenter": {
    "description": "Core process for telephony and cellular communication features.",
    "impact": "iPhone Cellular Calls, SMS relay, and Instant Hotspot features will not work.",
  },
  "com.apple.BTServer.cloudpairing": {
    "description": "Manages Bluetooth device pairing information synced via iCloud.",
    "impact": "Pairing information for devices like AirPods may not sync across your Apple devices.",
  },
  "com.apple.BTServer.le.agent": {
    "description": "Agent for managing Bluetooth Low Energy (LE) connections.",
    "impact": "Many modern Bluetooth accessories that use LE may fail to connect or function properly.",
  },
  "com.apple.companiond": {
    "description": "Daemon for managing communication with companion devices like the Apple Watch.",
    "impact": "Features that link your Mac and Apple Watch, like Auto Unlock, will not work.",
  },
  "com.apple.RapportUIAgent": {
    "description": "User interface agent for the Rapport framework, showing prompts for nearby device interactions.",
    "impact": "UI prompts for Handoff and other continuity features may not appear.",
  },
  "com.apple.identityservicesd": {
    "description": "Core daemon for Identity Services, which underlies iMessage, FaceTime, and iCloud.",
    "impact": "Signing into and using iMessage, FaceTime, and other Apple services will fail.",
  },
  "com.apple.sidecar-display-agent": {
    "description": "Agent that manages the display aspects of a Sidecar connection.",
    "impact": "The Sidecar feature will not work.",
  },
  "com.apple.BTServer.le": {
    "description": "A server component for Bluetooth Low Energy (LE) functionalities.",
    "impact": "Many modern Bluetooth peripherals that rely on LE may not connect or function correctly."
  },
  "com.apple.BlueTool": {
    "description": "A command-line utility and background service for interacting with Bluetooth devices.",
    "impact": "May cause issues with Bluetooth device management and diagnostics."
  },
  "com.apple.BluetoothUIService": {
    "description": "Provides user interface elements for Bluetooth interactions, such as pairing requests.",
    "impact": "Bluetooth pairing and other UI-related Bluetooth functions may fail."
  },
  "com.apple.ecosystemd": {
    "description": "A daemon for managing interactions within the Apple device ecosystem.",
    "impact": "May cause issues with continuity features and interactions between your Apple devices."
  },
  "com.apple.remoted": {
    "description": "The Remote Service Discovery daemon. It discovers and advertises Apple devices connected over USB or the local network, and is used by Xcode, Apple Configurator, Finder device sync, and developer tools.",
    "impact": "Tools like Xcode and Apple Configurator will not be able to discover, pair with, or debug connected Apple devices."
  },
  # Diagnostics & Logging
  "com.apple.logd": {
    "description": "The central daemon for managing the Unified Logging System. It collects and stores log messages from all system processes.",
    "impact": "System-wide logging will cease. This will make troubleshooting issues extremely difficult. Console.app will be empty.",
  },
  "com.apple.syslogd": {
    "description": "A legacy logging daemon. While modern macOS uses `logd`, this may still handle certain log types or provide compatibility.",
    "impact": "May break logging for older applications or specific system components. Disabling `logd` is more impactful.",
  },
  "com.apple.spindump": {
    "description": "Collects diagnostic information about hung or unresponsive applications ('spinning beachball').",
    "impact": "You will not get diagnostic reports when an application hangs, making it harder to debug.",
  },
  "com.apple.ReportCrash": {
    "description": "The agent responsible for generating crash reports when an application quits unexpectedly.",
    "impact": "Crash logs will not be created, hindering troubleshooting for both users and developers.",
  },
  "com.apple.SubmitDiagInfo": {
    "description": "Daemon that submits diagnostic information and crash reports to Apple.",
    "impact": "No diagnostic data or crash reports will be sent to Apple. May be desirable for privacy.",
  },
  "com.apple.tailspind": {
    "description": "A helper for `spindump` that can be triggered to collect system-wide responsiveness data over a period of time.",
    "impact": "May affect the ability to generate comprehensive system diagnostic reports for performance issues.",
  },
  "com.apple.coresymbolicationd": {
    "description": "Resolves symbolic information in crash logs and other diagnostics, turning memory addresses into human-readable function names.",
    "impact": "Crash reports will be much harder to interpret, as they will lack function names.",
  },
  "com.apple.enhancedloggingd": {
    "description": "Daemon for enhanced diagnostic logging.",
    "impact": "Certain detailed or verbose diagnostic logs will not be collected.",
  },
  "com.apple.diagnosticextensionsd": {
    "description": "Manages diagnostic extensions that can collect data for troubleshooting.",
    "impact": "The system will be unable to run specialized diagnostic tests.",
  },
  "com.apple.sysdiagnose_agent": {
    "description": "User agent for triggering a `sysdiagnose`, which collects comprehensive system information for debugging.",
    "impact": "You will not be able to trigger a `sysdiagnose` from the user session.",
  },
  "com.apple.diagnostics_agent": {
    "description": "General agent for handling diagnostic requests.",
    "impact": "Various diagnostic functionalities may fail.",
  },
  "com.apple.spindump_agent": {
    "description": "User agent for `spindump`, helping to collect reports on hung applications.",
    "impact": "Collecting diagnostic reports for unresponsive apps may fail.",
  },
  "com.apple.systemprofiler": {
    "description": "The backend for the System Information app.",
    "impact": "The System Information app will not be able to gather or display hardware and software details.",
  },
  "com.apple.CrashReporterSupportHelper": {
    "description": "A helper process that supports the main crash reporting system.",
    "impact": "Crash reports may not be generated or saved correctly, hindering troubleshooting."
  },
  "com.apple.DumpGPURestart": {
    "description": "A diagnostic tool that logs information when the GPU restarts unexpectedly.",
    "impact": "The system will not collect diagnostic data on GPU crashes, making it harder to troubleshoot graphics issues."
  },
  "com.apple.DumpPanic": {
    "description": "A service that saves a panic log when the system experiences a kernel panic.",
    "impact": "Kernel panic logs will not be saved, making it very difficult to diagnose the cause of system crashes."
  },
  "com.apple.DumpPanic.Accessory": {
    "description": "A helper service for `DumpPanic`, potentially for handling panics related to accessories.",
    "impact": "Panic logs related to connected accessories may not be saved correctly."
  },
  "com.apple.ReportCrash.Root": {
    "description": "A version of `ReportCrash` that runs as the root user to capture crashes of system-level processes.",
    "impact": "Crashes of system daemons and other root processes will not be logged."
  },
  "com.apple.ReportMemoryException": {
    "description": "A service that generates reports for memory-related exceptions.",
    "impact": "The system will not create diagnostic logs for memory issues, making them harder to troubleshoot."
  },
  "com.apple.ReportSystemMemory": {
    "description": "A service that reports on the system's memory usage for diagnostic purposes.",
    "impact": "The system will not be able to generate detailed memory usage reports."
  },
  "com.apple.aslmanager": {
    "description": "Apple System Log manager, a legacy logging daemon.",
    "impact": "Some legacy applications may not be able to log messages correctly."
  },
  "com.apple.bosreporter": {
    "description": "The BridgeOS install reporter. It reports the status of BridgeOS firmware installs and updates to the update system and to Apple.",
    "impact": "BridgeOS firmware update progress and failures may not be reported, making update troubleshooting harder."
  },
  "com.apple.boswatcher": {
    "description": "The BridgeOS install watcher. It monitors BridgeOS firmware installation progress and helps coordinate the update state.",
    "impact": "BridgeOS firmware updates may stall or fail to complete cleanly."
  },
  "com.apple.corecaptured": {
    "description": "A daemon for capturing core dumps for diagnostic purposes.",
    "impact": "The system will not be able to save detailed diagnostic information when a process crashes."
  },
  "com.apple.diagnosticd": {
    "description": "A daemon for running diagnostic tests.",
    "impact": "The system will be unable to run various diagnostic tests for troubleshooting."
  },
  "com.apple.diagnosticextensions.osx.spotlight.helper": {
    "description": "A helper for a diagnostic extension for Spotlight.",
    "impact": "The system will not be able to run diagnostics on Spotlight."
  },
  "com.apple.diagnosticextensions.osx.timemachine.helper": {
    "description": "A helper for a diagnostic extension for Time Machine.",
    "impact": "The system will not be able to run diagnostics on Time Machine."
  },
  "com.apple.diagnosticservicesd": {
    "description": "A daemon that provides diagnostic services to applications.",
    "impact": "Applications will not be able to access system diagnostic services."
  },
  "com.apple.logd_helper": {
    "description": "A helper for the main logging daemon.",
    "impact": "System logging may be impaired."
  },
  "com.apple.logd_reporter": {
    "description": "A service that reports on the status of the logging system.",
    "impact": "The system will not be able to generate diagnostics about the logging system itself."
  },
  "com.apple.logkextloadsd": {
    "description": "A daemon that logs the loading of kernel extensions.",
    "impact": "The system will not keep a record of which kernel extensions have been loaded, hindering security audits and troubleshooting."
  },
  "com.apple.newsyslog": {
    "description": "A tool that rotates log files.",
    "impact": "Log files may grow indefinitely, consuming disk space."
  },
  "com.apple.powerdatad": {
    "description": "A daemon that collects power usage data.",
    "impact": "The system will not be able to collect detailed power usage data for diagnostics."
  },
  "com.apple.powerlogHelperd": {
    "description": "A helper for logging power-related events.",
    "impact": "The system will not be able to create detailed logs of power usage and events."
  },
  "com.apple.rtcreportingd": {
    "description": "A daemon for Real-Time Clock (RTC) reporting and diagnostics.",
    "impact": "The system will not be able to report on the status of its real-time clock."
  },
  "com.apple.seld": {
    "description": "The Secure Element daemon. It manages the Secure Element/NFC hardware and handles NFC reader-mode sessions and security evaluations used by Apple Pay and related features.",
    "impact": "NFC and Secure Element features may stop working; reader-mode NFC sessions and some Apple Pay/SE operations will fail."
  },
  "com.apple.signpost.signpost_reporter": {
    "description": "A service that reports on 'signpost' diagnostic data from applications.",
    "impact": "The system will not be able to collect detailed performance data from applications that use the signpost framework."
  },
  "com.apple.symptomsd-diag": {
    "description": "A diagnostic tool for the 'Symptoms' framework, which analyzes network issues.",
    "impact": "You will not be able to run diagnostics on the network symptom analysis framework."
  },
  "com.apple.sysdiagnose": {
    "description": "The main tool for generating a `sysdiagnose` report.",
    "impact": "You will not be able to generate a `sysdiagnose` report for troubleshooting."
  },
  "com.apple.sysdiagnose_helper": {
    "description": "A helper for `sysdiagnose`.",
    "impact": "`sysdiagnose` may fail to collect all necessary information."
  },
  "com.apple.systemstats.analysis": {
    "description": "A tool that analyzes system statistics.",
    "impact": "The system will not be able to perform analysis of its collected performance data."
  },
  "com.apple.systemstats.daily": {
    "description": "A tool that performs daily collection of system statistics.",
    "impact": "The system will not collect its daily performance statistics."
  },
  "com.apple.systemstats.microstackshot_periodic": {
    "description": "A tool that periodically takes 'microstackshots' for performance analysis.",
    "impact": "The system will not collect detailed, periodic snapshots of process activity for performance analysis."
  },
  "com.apple.usbctelemetryd": {
    "description": "A daemon that collects telemetry data about USB-C ports.",
    "impact": "The system will not collect diagnostic data on USB-C port usage and health."
  },
  # Family & ScreenTime
  "com.apple.familycontrols.useragent": {
    "description": "The user agent for parental controls and Screen Time features.",
    "impact": "You will not be able to manage or enforce parental controls or Screen Time settings.",
  },
  "com.apple.familycircled": {
    "description": "Manages Family Sharing features like shared purchases, iCloud storage, and location.",
    "impact": "All Family Sharing functionality will stop working.",
  },
  "com.apple.ScreenTimeAgent": {
    "description": "The agent for Screen Time, which tracks your usage and enforces set limits.",
    "impact": "Screen Time will not be able to track usage or enforce configured limits.",
  },
  "com.apple.parentalcontrols.check": {
    "description": "A helper process to check parental controls settings.",
    "impact": "Parental controls may not be enforced correctly.",
  },
  "com.apple.FamilyControlsAgent": {
    "description": "Agent for Family Controls and Screen Time.",
    "impact": "You will not be able to manage or enforce parental controls or Screen Time settings.",
  },
  "com.apple.familycontrols": {
    "description": "The main daemon for parental controls and Screen Time.",
    "impact": "You will not be able to manage or enforce parental controls or Screen Time settings."
  },
  # Filesystem & Storage
  "com.apple.fseventsd": {
    "description": "The File System Events daemon. It logs file and directory modifications, used by Time Machine, Spotlight, and many other apps.",
    "impact": "CRITICAL: Many applications that rely on detecting file changes (Time Machine, Spotlight, Dropbox, etc.) will break.",
  },
  "com.apple.diskarbitrationd": {
    "description": "Manages the mounting and unmounting of disks and volumes. It notifies applications about disk appearances and disappearances.",
    "impact": "CRITICAL: Your Mac will not be able to mount or unmount internal or external drives, disk images, or network shares. System may not boot.",
  },
  "com.apple.storagekitd": {
    "description": "A daemon for the StorageKit framework, which is used for managing storage, including APFS volumes and partitions.",
    "impact": "Features related to disk and volume management, like in Disk Utility, may fail.",
  },
  "com.apple.corestorage.corestoraged": {
    "description": "The daemon for Core Storage, a legacy logical volume manager (used for Fusion Drives and FileVault on HFS+).",
    "impact": "If your system uses a Core Storage volume (like an older Fusion Drive), disabling this could lead to data loss or an unbootable system.",
  },
  "com.apple.hdiejectd": {
    "description": "A helper daemon that assists in the process of ejecting disk images (.dmg files).",
    "impact": "You may have trouble properly ejecting mounted disk images.",
  },
  "com.apple.nfsd": {
    "description": "The Network File System (NFS) daemon, allowing your Mac to serve files to other computers over the network using the NFS protocol.",
    "impact": "You will not be able to share files via NFS. Safe to disable if you do not use this feature.",
  },
  "com.apple.smbd": {
    "description": "The main daemon for SMB (Server Message Block) services, used for Windows file sharing.",
    "impact": "You will not be able to share files with or access shares from Windows computers.",
  },
  "com.apple.unmountassistant.useragent": {
    "description": "User agent that assists with unmounting volumes.",
    "impact": "You may encounter issues when trying to eject disks or volumes.",
  },
  "com.apple.apfsuseragent": {
    "description": "User-level agent for APFS filesystem operations.",
    "impact": "Certain APFS features, like volume management from the user session, may fail.",
  },
  "com.apple.DiskArbitrationAgent": {
    "description": "User agent that works with `diskarbitrationd` to manage disks and volumes.",
    "impact": "Mounting and unmounting disks may become unreliable.",
  },
  "com.apple.FileProvider": {
    "description": "A core service that allows apps like Dropbox or OneDrive to integrate with Finder.",
    "impact": "Third-party cloud storage services will not be able to integrate with Finder.",
  },
  "com.apple.fskit.fskit_agent": {
    "description": "Agent for the user-space filesystem framework.",
    "impact": "Filesystems implemented with FSKit will not work.",
  },
  "com.apple.pboard": {
    "description": "The Pasteboard server, which manages the system clipboard.",
    "impact": "CRITICAL: Copy and paste functionality will be completely broken across all applications.",
  },
  "com.apple.FileCoordination": {
    "description": "A service that coordinates access to files to prevent conflicts between different processes or devices.",
    "impact": "May lead to data corruption or sync issues, especially with iCloud Drive and other file syncing services."
  },
  "com.apple.afpfs_afpLoad": {
    "description": "A service to load the Apple Filing Protocol (AFP) file system extension.",
    "impact": "You will not be able to connect to legacy AFP file shares."
  },
  "com.apple.afpfs_checkafp": {
    "description": "A tool to check the status of AFP connections.",
    "impact": "May impact the reliability of AFP connections."
  },
  "com.apple.applessdstatistics": {
    "description": "A service that collects statistics about the solid-state drive (SSD).",
    "impact": "The system will not collect diagnostic data on SSD performance and health."
  },
  "com.apple.apfsd": {
    "description": "The main daemon for the Apple File System (APFS).",
    "impact": "Critical for APFS operations; its absence would likely lead to an unbootable system."
  },
  "com.apple.asr": {
    "description": "Apple Software Restore daemon.",
    "impact": "The `asr` command-line tool for block-level disk imaging will not work."
  },
  "com.apple.autofsd": {
    "description": "Auto-mounts network file systems.",
    "impact": "Network shares will not be automatically mounted."
  },
  "com.apple.automountd": {
    "description": "A daemon that automatically mounts file systems.",
    "impact": "Similar to `autofsd`, this is critical for automatically mounting network and other file systems."
  },
  "com.apple.corestorage.corestoragehelperd": {
    "description": "A helper for Core Storage, a legacy volume management technology.",
    "impact": "If you have a Fusion Drive or a FileVault 2 encrypted HFS+ volume, you may experience data loss or an unbootable system."
  },
  "com.apple.diskimagesiod": {
    "description": "A daemon for handling I/O for disk images.",
    "impact": "You may have issues mounting or accessing the content of disk images."
  },
  "com.apple.diskimagesiod.ram": {
    "description": "A version of `diskimagesiod` for RAM-based disk images.",
    "impact": "Creating or using RAM disks will not work."
  },
  "com.apple.diskimagesiod.spb": {
    "description": "A variant of the Disk Images IO daemon (diskimagesiod). It handles I/O for disk images, including encrypted images and shadow files.",
    "impact": "Mounting or reading disk images may fail."
  },
  "com.apple.diskmanagementstartup": {
    "description": "A service that runs at startup to perform disk management tasks.",
    "impact": "The system may not correctly prepare disks and volumes at startup."
  },
  "com.apple.filesystems.fskitd": {
    "description": "A daemon for the user-space file system framework.",
    "impact": "File systems implemented with FSKit will not work."
  },
  "com.apple.filesystems.userfs_helper": {
    "description": "A helper for the user-space file system framework.",
    "impact": "User-space file systems will not function correctly."
  },
  "com.apple.filesystems.userfsd": {
    "description": "The daemon for the user-space file system framework.",
    "impact": "User-space file systems will not function correctly."
  },
  "com.apple.fskit.fskit_helper": {
    "description": "A helper for the user-space file system framework.",
    "impact": "User-space file systems will not function correctly."
  },
  "com.apple.locate": {
    "description": "A command-line tool for finding files by name.",
    "impact": "The `locate` command will not work."
  },
  "com.apple.nfsconf": {
    "description": "A tool for configuring NFS.",
    "impact": "You will not be able to configure NFS settings."
  },
  "com.apple.revisiond": {
    "description": "A daemon for managing file versions, used by features like 'Revert To'.",
    "impact": "The system will not save historical versions of documents, and the 'Revert To' feature will not work."
  },
  "com.apple.smb.preferences": {
    "description": "A tool for configuring SMB (Windows file sharing) preferences.",
    "impact": "You will not be able to configure SMB settings."
  },
  "com.apple.unmountassistant.sysagent": {
    "description": "A system-level agent for assisting with unmounting volumes.",
    "impact": "May cause issues when unmounting system-related volumes."
  },
  # Game Center
  "com.apple.gamed": {
    "description": "The daemon for Game Center, which manages leaderboards, achievements, and multiplayer functionality.",
    "impact": "Game Center features will not be available in games that use it.",
  },
  "com.apple.GameController.gamecontrolleragentd": {
    "description": "Agent for the Game Controller framework.",
    "impact": "Game controllers may not be properly detected or configured.",
  },
  "com.apple.gamesaved": {
    "description": "The GameSave daemon (GameplayKit). It saves game progress locally and syncs game saves through iCloud.",
    "impact": "Game progress will not be saved or synced.",
  },
  "com.apple.GamePolicyAgent": {
    "description": "Agent that enforces policies related to games.",
    "impact": "Unknown, but could affect game performance or features.",
  },
  "com.apple.GameController.gamecontrollerd": {
    "description": "The main daemon for the Game Controller framework, managing the input from game controllers.",
    "impact": "Game controllers will not be recognized or function in games."
  },
  "com.apple.fpsd.arcadeservice": {
    "description": "An Apple Arcade service hosted by fpsd, Apple's FairPlay Streaming daemon. It handles FairPlay-protected media for Arcade titles.",
    "impact": "Apple Arcade games that rely on FairPlay Streaming may fail to play."
  },
  "com.apple.gamepolicyd": {
    "description": "A daemon that enforces policies related to games.",
    "impact": "May affect game performance or features."
  },
  # Hardware & Drivers
  "com.apple.airportd": {
    "description": "The core daemon that manages Wi-Fi hardware and connections.",
    "impact": "CRITICAL: Wi-Fi will be completely disabled and you will not be able to connect to any wireless networks.",
  },
  "com.apple.appleh13camerad": {
    "description": "A low-level camera daemon that interfaces with the Image Signal Processor (ISP) and Apple Neural Engine (ANE) for the built-in camera on Apple Silicon Macs that use the H13 camera hardware platform.",
    "impact": "The built-in FaceTime/iSight camera will not function. This is a hardware-specific driver.",
  },
  "com.apple.appleh16camerad": {
    "description": "A low-level camera daemon that interfaces with the Image Signal Processor (ISP) and Apple Neural Engine (ANE) for the built-in camera on Apple Silicon Macs that use the H16 camera hardware platform.",
    "impact": "The built-in FaceTime/iSight camera will not function. This is a hardware-specific driver.",
  },
  "com.apple.audio.AudioComponentRegistrar": {
    "description": "Manages the system's registry of Audio Unit (AU) plugins, making them available to host applications like Logic Pro, GarageBand, and other DAWs.",
    "impact": "Audio applications will not be able to find or load any third-party audio effects or virtual instrument plugins.",
  },
  "com.apple.audio.coreaudiod": {
    "description": "The main daemon for Core Audio, which manages all audio input and output.",
    "impact": "CRITICAL: All audio on the system will cease to function. You will have no sound output or microphone input.",
  },
  "com.apple.audio.isolated.historicalaudiod": {
    "description": "A sandboxed daemon that likely logs historical audio device usage for diagnostic or system intelligence purposes.",
    "impact": "The system will stop collecting diagnostic data about audio device usage. No immediate impact on audio functionality.",
  },
  "com.apple.audio.isolated.micactivityd": {
    "description": "A sandboxed daemon that manages the microphone-in-use privacy indicator (the orange dot in the menu bar).",
    "impact": "The orange dot privacy indicator for microphone access will no longer appear, reducing user awareness of microphone activity.",
  },
  "com.apple.audio.systemsoundserverd": {
    "description": "A dedicated server for playing all system user interface sound effects, such as alerts and volume change feedback.",
    "impact": "All system UI sounds will be silenced. Main application audio (e.g., music, video) will not be affected.",
  },
  "com.apple.audiomxd": {
    "description": "The Core Audio mixer daemon. It mixes and routes audio streams between apps, devices, and system services.",
    "impact": "Disabling this would likely cause severe audio malfunctions, possibly breaking all audio input or output. HIGH RISK.",
  },
  "com.apple.cameracaptured": {
    "description": "A high-level daemon that manages and arbitrates access to camera hardware, preventing conflicts between applications.",
    "impact": "Applications will be unable to access the camera, as the service for managing capture sessions will be unavailable.",
  },
  "com.apple.cmio.uvcassistantextension": {
    "description": "A system extension that acts as an assistant for generic USB Video Class (UVC) cameras, enabling plug-and-play functionality for most third-party webcams.",
    "impact": "Most external USB webcams will not be detected by the system or any applications.",
  },
  "com.apple.colorsync.displayservices": {
    "description": "A specialized agent that provides ColorSync services directly to the WindowServer and loginwindow for system-level display color management.",
    "impact": "Display color may become inaccurate. Features like custom display profiles, Night Shift, or True Tone may be affected.",
  },
  "com.apple.colorsyncd": {
    "description": "The main daemon for the ColorSync framework, responsible for managing color profiles to ensure consistent color across applications and devices.",
    "impact": "Color management will be disabled, leading to inaccurate color representation in image editors, web browsers, and other applications.",
  },
  "com.apple.corebrightnessd": {
    "description": "The daemon that manages all aspects of display brightness, including manual adjustments, auto-brightness, and features like Night Shift.",
    "impact": "All display brightness controls (manual and automatic) and features like Night Shift will cease to function.",
  },
  "com.apple.ctkd": {
    "description": "The CryptoTokenKit Daemon. It's the central process for the framework that gives apps access to hardware cryptographic tokens like smart cards.",
    "impact": "Access to all hardware security tokens (including smart cards) will be broken. Essential for corporate/government environments using smart card authentication.",
  },
  "com.apple.deviceinterfaced": {
    "description": "The device interface daemon. It publishes user-space DriverKit device interfaces so apps can communicate with peripherals.",
    "impact": "Unknown. Disabling this service is not recommended as its function and dependencies are not clear, and it could affect hardware stability.",
  },
  "com.apple.displaypolicyd": {
    "description": "The Display Policy Daemon. Enforces high-level policies for displays and GPUs, most notably automatic graphics switching on dual-GPU Macs.",
    "impact": "On dual-GPU Macs, may break power-saving graphics switching. On all Macs, its failure during boot can prevent the system from starting up.",
  },
  "com.apple.hidd": {
    "description": "Human Interface Device Daemon. It processes all input from keyboards, mice, trackpads, and other input devices.",
    "impact": "CRITICAL: All input devices will stop working. You will lose control of your computer.",
  },
  "com.apple.ifdreader": {
    "description": "The 'Interface for Devices' reader daemon. This is the core service for interacting with PC/SC compliant smart card readers.",
    "impact": "Smart card readers will not function. Safe to disable if you do not use smart cards for authentication or other purposes.",
  },
  "com.apple.iomfb_bics_daemon": {
    "description": "A low-level helper daemon for the I/O Mobile Framebuffer (IOMFB), which is the core framework for sending pixels to the screen.",
    "impact": "CRITICAL: This is a fundamental component of the display driver stack. Disabling it is extremely risky and would likely result in a black screen or system crash.",
  },
  "com.apple.iomfb_fdr_loader": {
    "description": "A low-level 'Firmware Data/Driver Loader' for the I/O Mobile Framebuffer. It appears to load critical data to the display controller during boot.",
    "impact": "CRITICAL: Disabling this service will very likely prevent the system from booting, as it is essential for initializing the display hardware.",
  },
  "com.apple.kernelmanagerd": {
    "description": "The Kernel Manager Daemon. This highly privileged process is responsible for loading and unloading legacy Kernel Extensions (KEXTs).",
    "impact": "CRITICAL: Prevents the system from loading any kernel extensions, which will break many third-party drivers (for audio, networking, etc.) and may cause system instability or failure to boot.",
  },
  "com.apple.nand.aspcarry": {
    "description": "A daemon to collect and log I/O patterns and diagnostics directly from the physical NAND flash storage (SSD). Related to 'Apple Storage Provider'.",
    "impact": "HIGH RISK: Disabling could interfere with the SSD controller's ability to manage the flash memory, potentially impacting performance, longevity, or data integrity.",
  },
  "com.apple.nand_task_scheduler": {
    "description": "A service for scheduling low-level maintenance tasks (e.g., garbage collection, TRIM) directly on the physical NAND flash storage controller.",
    "impact": "HIGH RISK: Disabling could degrade SSD performance and reduce its lifespan by preventing essential maintenance tasks from running.",
  },
  "com.apple.powerd": {
    "description": "The central power management daemon. It handles sleep, processor speed scaling, and other power-related settings.",
    "impact": "CRITICAL: The system will be unable to manage power states. Sleep will not work, and battery life will be severely impacted. May lead to overheating.",
  },
  "com.apple.retimerd": {
    "description": "The Retimer Daemon. Manages the retimer hardware chips that ensure signal integrity for high-speed ports like Thunderbolt and USB4.",
    "impact": "High-speed ports (Thunderbolt/USB4) may become unstable or non-functional, especially with demanding peripherals or long cables.",
  },
  "com.apple.scsid": {
    "description": "The SCSI Daemon. Manages communication with devices using the SCSI command protocol, which includes many external USB storage devices and older SATA drives.",
    "impact": "External hard drives, optical drives, and other storage devices that use the SCSI protocol may become inaccessible.",
  },
  "com.apple.sysextd": {
    "description": "The System Extension Daemon. Manages the entire lifecycle of modern user-space drivers (DriverKit) and System Extensions.",
    "impact": "CRITICAL: Prevents any modern driver or system extension from working. This will break VPN clients, security software, and many hardware drivers, crippling the OS.",
  },
  "com.apple.thermald": {
    "description": "Monitors system temperature sensors and manages thermal controls to prevent overheating.",
    "impact": "The system will lose its ability to respond to high temperatures, which could lead to performance throttling, shutdowns, or hardware damage.",
  },
  "com.apple.touchbarserver": {
    "description": "Manages the Touch Bar on MacBook Pro models that have one.",
    "impact": "The Touch Bar and Control Strip will become non-functional.",
  },
  "com.apple.SafeEjectGPUAgent": {
    "description": "Agent for safely ejecting external GPUs (eGPUs).",
    "impact": "The system may not properly handle the disconnection of an eGPU, potentially leading to instability or data loss.",
  },
  "com.apple.cmio.LaunchCMIOUserExtensionsAgent": {
    "description": "Launches user-level Core Media I/O extensions.",
    "impact": "Third-party video devices or software that use CMIO extensions may not work.",
  },
  "com.apple.usbnotificationagent": {
    "description": "Agent for showing notifications related to USB devices.",
    "impact": "You may not see important notifications about USB device power or connectivity.",
  },
  "com.apple.IOUIAgent": {
    "description": "User-level agent for the I/O Kit framework.",
    "impact": "May affect communication between user-space and hardware drivers.",
  },
  "com.apple.midiserver": {
    "description": "The central server for MIDI (Musical Instrument Digital Interface) services.",
    "impact": "MIDI keyboards, controllers, and applications will not function.",
  },
  "com.apple.ptpcamerad": {
    "description": "Daemon for handling cameras that use the Picture Transfer Protocol (PTP).",
    "impact": "You will not be able to import photos directly from many digital cameras.",
  },
  "com.apple.SafeEjectGPUService": {
    "description": "Service for safely ejecting external GPUs (eGPUs).",
    "impact": "The system may not properly handle the disconnection of an eGPU, potentially leading to instability or data loss.",
  },
  "com.apple.AmbientDisplayAgent": {
    "description": "Manages ambient display functionality, such as True Tone, which adjusts the display's color and intensity to match the ambient light.",
    "impact": "Disabling this will prevent True Tone and similar display adjustments from functioning, potentially leading to less comfortable viewing experiences in varying lighting conditions."
  },
  "com.apple.IOAccelMemoryInfoCollector": {
    "description": "Collects memory usage information from the graphics acceleration framework.",
    "impact": "The system will not be able to collect detailed memory diagnostics for the GPU."
  },
  "com.apple.IOUserBluetoothSerialDriver-0x10000067b": {
    "description": "A user-space driver for a specific Bluetooth serial device.",
    "impact": "The specific Bluetooth device associated with this driver will not function."
  },
  "com.apple.IOUserDockChannelSerial-0x100000414": {
    "description": "A user-space driver for a specific dock or adapter that provides serial communication.",
    "impact": "The specific dock or adapter will not function correctly."
  },
  "com.apple.KernelEventAgent": {
    "description": "An agent that listens for and responds to low-level kernel events.",
    "impact": "May cause a variety of system-level issues, as communication from the kernel to user-space may be impaired."
  },
  "com.apple.SafeEjectGPUStartupDaemon": {
    "description": "A daemon that runs at startup to manage the state of external GPUs (eGPUs).",
    "impact": "eGPUs may not be properly recognized or managed at startup."
  },
  "com.apple.accessoryd": {
    "description": "A daemon for managing connected accessories.",
    "impact": "May cause issues with the functionality of connected accessories like docks or adapters."
  },
  "com.apple.accessoryupdaterd": {
    "description": "A daemon that handles firmware updates for connected accessories.",
    "impact": "Firmware updates for Apple and third-party accessories will not be installed."
  },
  "com.apple.aned": {
    "description": "Apple Neural Engine Daemon.",
    "impact": "Applications that use the Apple Neural Engine for machine learning tasks will fail or perform poorly."
  },
  "com.apple.aneuserd": {
    "description": "A user-space daemon for the Apple Neural Engine.",
    "impact": "User-level applications will be unable to access the Apple Neural Engine."
  },
  "com.apple.aonsensed": {
    "description": "'Always On' sensor daemon.",
    "impact": "'Always On' features that rely on sensors may not work."
  },
  "com.apple.avbdeviced": {
    "description": "Audio Video Bridging device daemon.",
    "impact": "Professional audio and video equipment that uses the AVB networking standard will not work."
  },
  "com.apple.cmio.VDCAssistant": {
    "description": "The CoreMediaIO VDC (Video Digitizer Component) assistant. It provides access to built-in and USB cameras for apps such as FaceTime.",
    "impact": "Some older webcams may not function correctly."
  },
  "com.apple.cmio.iOSScreenCaptureAssistant": {
    "description": "A helper for capturing the screen of an iOS device.",
    "impact": "You will not be able to record the screen of a connected iPhone or iPad."
  },
  "com.apple.corekdld": {
    "description": "Downloads and manages the Kernel Debug Kit (KDL) from Apple, which supplies debug symbols and kernel development support for Xcode and kernel debugging.",
    "impact": "Kernel debugging and symbolication of kernel core dumps will not work properly."
  },
  "com.apple.cvmsServ": {
    "description": "A server for OpenGL and Metal compute services.",
    "impact": "Applications that use GPU for computation will fail or perform poorly."
  },
  "com.apple.driverkit.AppleUserHIDDrivers-0x100000463": {
    "description": "A user-space driver for a specific Human Interface Device (HID).",
    "impact": "The specific HID device associated with this driver will not function."
  },
  "com.apple.dvdplayback.setregion": {
    "description": "A tool for setting the region code for the DVD drive.",
    "impact": "You will not be able to change the region of your DVD drive."
  },
  "com.apple.eoshostd": {
    "description": "The EmbeddedOSSupport host daemon. It communicates with the embedded OS (eosd) on accessories and coprocessors and manages their connection watchdog.",
    "impact": "Certain camera or imaging functionalities may fail."
  },
  "com.apple.iokit.ioserviceauthorized": {
    "description": "Handles authorization for I/O Kit services.",
    "impact": "May prevent applications from accessing certain hardware functionalities."
  },
  "com.apple.ionodecache": {
    "description": "Caches I/O Kit node information for performance.",
    "impact": "May lead to slower hardware interactions."
  },
  "com.apple.ioupsd": {
    "description": "A daemon for interacting with Uninterruptible Power Supply (UPS) devices.",
    "impact": "Your Mac will not be able to communicate with a connected UPS."
  },
  "com.apple.kernelmanager_helper": {
    "description": "A helper for managing legacy kernel extensions (KEXTs).",
    "impact": "The system may have issues loading or unloading KEXTs."
  },
  "com.apple.liquiddetectiond": {
    "description": "The Liquid Damage Detection daemon. It monitors and logs liquid exposure events in the Mac's ports.",
    "impact": "The system will not be able to warn you about liquid in the ports, potentially preventing damage."
  },
  "com.apple.nfcd": {
    "description": "The daemon for Near Field Communication (NFC).",
    "impact": "If your Mac has an NFC reader, it will not function. Not relevant for most Macs."
  },
  "com.apple.oahd": {
    "description": "The Rosetta 2 helper daemon. It installs and maintains the Rosetta translation environment on Apple Silicon so Intel-only apps can run.",
    "impact": "Intel-only apps will not be able to install or use Rosetta; existing translated apps may fail to launch."
  },
  "com.apple.oahd-root-helper": {
    "description": "The privileged helper used by Rosetta's oahd to install or update the Rosetta 2 environment.",
    "impact": "Rosetta 2 cannot be installed or updated, so some Intel apps may stop working after an update."
  },
  "com.apple.printtool.daemon": {
    "description": "A daemon for the printing system.",
    "impact": "You will not be able to print from this Mac."
  },
  "com.apple.thermalmonitord": {
    "description": "A daemon that monitors system thermals.",
    "impact": "The system will lose its ability to respond to high temperatures, which could lead to performance throttling, shutdowns, or hardware damage."
  },
  "com.apple.timesync.audioclocksyncd": {
    "description": "A service for synchronizing audio clocks across devices.",
    "impact": "May affect pro audio applications that sync with external audio hardware."
  },
  "com.apple.usbaudiod": {
    "description": "The daemon for USB audio devices.",
    "impact": "USB microphones, headphones, and audio interfaces will not work."
  },
  "com.apple.usbpowerd": {
    "description": "A daemon that manages power delivery over USB-C ports.",
    "impact": "Your Mac may not be able to correctly charge or provide power to connected USB-C devices."
  },
  "com.apple.usbsmartcardreaderd": {
    "description": "A daemon for USB smart card readers.",
    "impact": "USB smart card readers will not function."
  },
  "com.apple.wifiFirmwareLoader": {
    "description": "A service that loads the firmware for the Wi-Fi card.",
    "impact": "Wi-Fi will not function."
  },
  "org.cups.cupsd": {
    "description": "The Common UNIX Printing System daemon.",
    "impact": "You will not be able to print from this Mac."
  },
  # HomeKit
  "com.apple.homed": {
    "description": "The primary daemon for HomeKit, managing all HomeKit devices, scenes, and automations.",
    "impact": "You will not be able to control any HomeKit devices from your Mac. Home app will not work.",
  },
  "com.apple.homeenergyd": {
    "description": "Manages energy-related features within HomeKit.",
    "impact": "HomeKit energy monitoring and management features will not work.",
  },
  # iCloud & CloudKit
  "com.apple.cloudd": {
    "description": "A fundamental daemon for iCloud, responsible for syncing data between your Mac and iCloud.",
    "impact": "Will break most iCloud functionality, including iCloud Drive, Photos, and app data syncing.",
  },
  "com.apple.bird": {
    "description": "A core daemon for iCloud Drive, handling the syncing of documents and data.",
    "impact": "iCloud Drive will stop syncing. Files will not upload or download from iCloud.",
  },
  "com.apple.cloudphotod": {
    "description": "Manages the syncing of your photo and video library with iCloud Photos.",
    "impact": "Photos and videos will no longer sync with iCloud.",
  },
  "com.apple.icloud.findmydeviced": {
    "description": "Core daemon for the 'Find My' service, tracking the location of your device.",
    "impact": "The 'Find My' service will be non-functional, preventing you from locating this device.",
  },
  "com.apple.icloud.searchpartyd": {
    "description": "Daemon for the 'Find My' network, helps locate offline devices by leveraging other Apple devices.",
    "impact": "Offline finding capabilities for your devices will be disabled.",
  },
  "com.apple.protectedcloudstorage.protectedcloudkeysyncing": {
    "description": "Securely syncs sensitive data, such as keychain passwords and home data, with iCloud Keychain.",
    "impact": "Will break iCloud Keychain syncing; your passwords will not be available across your devices.",
  },
  "com.apple.itunescloudd": {
    "description": "Handles synchronization of your music library with iCloud Music Library (Apple Music/iTunes Match) and TV show/movie purchases.",
    "impact": "Your music and video library will no longer sync across your devices via iCloud.",
  },
  "com.apple.ckdiscretionaryd": {
    "description": "Manages discretionary background tasks for CloudKit.",
    "impact": "Background syncing for some iCloud-enabled apps may be delayed or fail.",
  },
  "com.apple.AOSPushRelay": {
    "description": "A push notification relay for legacy iCloud services (Back to My Mac).",
    "impact": "Legacy iCloud features are likely to fail.",
  },
  "com.apple.findmymacmessenger": {
    "description": "Handles messaging for the 'Find My Mac' feature.",
    "impact": "Remote lock and wipe commands sent via Find My may not be received.",
  },
  "com.apple.cmfsyncagent": {
    "description": "The CommunicationsFilter sync agent. It syncs call-filtering settings (such as Silence Unknown Callers and Live Voicemail) across devices.",
    "impact": "Call-filtering settings may not sync between your devices.",
  },
  "com.apple.CloudPhotosConfiguration": {
    "description": "Manages the configuration for iCloud Photos.",
    "impact": "iCloud Photos may not function or sync correctly.",
  },
  "com.apple.icloud.findmydeviced.findmydevice-user-agent": {
    "description": "User agent for the 'Find My Device' service.",
    "impact": "The 'Find My' service will be non-functional.",
  },
  "com.apple.AOSHeartbeat": {
    "description": "A 'heartbeat' service to check the status of legacy iCloud services.",
    "impact": "Legacy iCloud features may not work reliably.",
  },
  "com.apple.cloudsettingssyncagent": {
    "description": "Syncs various system and app settings via iCloud.",
    "impact": "Settings may not sync correctly between your Apple devices.",
  },
  "com.apple.iCloudHelper": {
    "description": "A helper agent for various iCloud functionalities.",
    "impact": "General iCloud reliability may be reduced.",
  },
  "com.apple.iCloudUserNotificationsd": {
    "description": "The iCloud user notifications daemon. It displays alerts about iCloud account and storage events.",
    "impact": "You may not receive notifications related to iCloud services.",
  },
  "com.apple.privatecloudcomputed": {
    "description": "Daemon for Private Cloud Compute features, which process sensitive data securely.",
    "impact": "On-device intelligence features that rely on Private Cloud Compute will fail.",
  },
  "com.apple.cdpd": {
    "description": "The Cloud Data Protection daemon, responsible for managing the iCloud Keychain.",
    "impact": "CRITICAL: iCloud Keychain syncing will fail. Passwords and other sensitive data will not sync.",
  },
  "com.apple.appleaccountd": {
    "description": "Manages the Apple ID account for the system.",
    "impact": "Signing into or managing your Apple ID in System Settings will fail.",
  },
  "com.apple.findmy.findmybeaconingd": {
    "description": "A daemon for the 'Find My' network that sends out Bluetooth beacons.",
    "impact": "Your device will not be findable by the 'Find My' network when it is offline."
  },
  "com.apple.findmymacd": {
    "description": "The Find My Mac daemon. It receives Find My commands and manages the associated secure state so the Mac can be located, locked, or erased.",
    "impact": "'Find My Mac' will not be functional."
  },
  # Installation & Updates
  "com.apple.installd": {
    "description": "The core daemon responsible for installing software, including apps from the App Store and package installers.",
    "impact": "You will not be able to install, update, or remove most software.",
  },
  "com.apple.softwareupdated": {
    "description": "The daemon for the macOS Software Update mechanism. It checks for, downloads, and installs system updates.",
    "impact": "You will not be notified of or be able to install macOS updates, leaving your system potentially vulnerable.",
  },
  "com.apple.mobileassetd": {
    "description": "Manages and downloads 'mobile assets', which are resources used by the OS and apps (e.g., Siri voices, dictionaries, ML models).",
    "impact": "Many system features may fail to update their resources, leading to outdated or non-functional behavior.",
  },
  "com.apple.mobile.obliteration": {
    "description": "A service that manages the 'Erase All Content and Settings' feature, which securely erases user data and returns the Mac to its factory state.",
    "impact": "Disabling this will likely cause the 'Erase All Content and Settings' feature in System Settings to fail.",
  },
  "com.apple.AssetCache.agent": {
    "description": "User agent for the Content Caching service.",
    "impact": "The system will not be able to use a local Content Caching server to speed up downloads.",
  },
  "com.apple.installerauthagent": {
    "description": "Agent for authenticating software installation requests.",
    "impact": "You may not be able to provide a password to authorize software installations.",
  },
  "com.apple.appleseed.seedusaged": {
    "description": "Daemon for tracking usage statistics for beta (AppleSeed) software.",
    "impact": "If you are on a beta seed, usage data will not be sent to Apple.",
  },
  "com.apple.installd.user": {
    "description": "User-level daemon for software installation.",
    "impact": "Installing software within the user session may fail.",
  },
  "com.apple.SoftwareUpdateNotificationManager": {
    "description": "Manages the notifications for available software updates.",
    "impact": "You will not receive notifications about new macOS and app updates.",
  },
  "com.apple.suhelperd": {
    "description": "A helper daemon for the Software Update process.",
    "impact": "macOS updates may fail to download or install.",
  },
  "com.apple.AssetCacheLocatorService": {
    "description": "Service to locate a Content Caching server on the local network.",
    "impact": "The system will not be able to discover or use a local Content Caching server.",
  },
  "com.apple.betaenrollmentagent": {
    "description": "Agent for enrolling the Mac in the beta software program.",
    "impact": "You will not be able to enroll in or unenroll from the macOS beta program.",
  },
  "com.apple.AssetCache.builtin": {
    "description": "A built-in component of the Content Caching service.",
    "impact": "The Content Caching service may not function correctly, leading to slower downloads of Apple software and iCloud content on your local network."
  },
  "com.apple.AssetCacheManagerService": {
    "description": "Manages the Content Caching service, which speeds up the download of Apple software and iCloud content.",
    "impact": "The Content Caching service will be unavailable."
  },
  "com.apple.AssetCacheTetheratorService": {
    "description": "Lets iOS devices use this Mac's Content Caching service over a USB tether.",
    "impact": "Content Caching over tethered connections will not work."
  },
  "com.apple.InstallerDiagnostics.installerdiagd": {
    "description": "A daemon for collecting diagnostics during software installations.",
    "impact": "The system will not be able to gather detailed diagnostic logs when an installation fails."
  },
  "com.apple.InstallerDiagnostics.installerdiagwatcher": {
    "description": "Watches for and reports on issues during the installation process.",
    "impact": "The system will have reduced ability to diagnose and report on installation failures."
  },
  "com.apple.InstallerProgress": {
    "description": "Manages the user interface for installer progress bars.",
    "impact": "The progress bar for software installations may not display correctly."
  },
  "com.apple.MobileAsset.ManifestStorageService": {
    "description": "Manages the storage of manifests for Mobile Assets (e.g., Siri voices, fonts).",
    "impact": "The system may be unable to track or update its downloadable assets correctly."
  },
  "com.apple.MobileInstallationHelperService": {
    "description": "A helper service for installing applications, particularly those with origins in iOS.",
    "impact": "Installation of certain applications may fail."
  },
  "com.apple.MobileSoftwareUpdate.CleanupPreparePathService": {
    "description": "A service that prepares paths for cleaning up after a software update.",
    "impact": "The system may fail to clean up temporary files after an update, leading to wasted disk space."
  },
  "com.apple.MobileSoftwareUpdate.CryptegraftService": {
    "description": "Handles cryptographic sealing and 'cryptex grafting' of system components during a software update.",
    "impact": "Software updates may fail, especially if they involve encrypted system components."
  },
  "com.apple.UpdateSettings": {
    "description": "A service that manages settings related to software updates.",
    "impact": "Software update preferences may not be correctly applied."
  },
  "com.apple.appleseed.fbahelperd": {
    "description": "A helper for the Feedback Assistant application, used for submitting feedback on beta software.",
    "impact": "The Feedback Assistant app may not function correctly."
  },
  "com.apple.betaenrollmentd": {
    "description": "A daemon for enrolling the Mac in the beta software program.",
    "impact": "You will not be able to enroll in or unenroll from the macOS beta program."
  },
  "com.apple.bootinstalld": {
    "description": "A daemon that handles the installation of boot-related files.",
    "impact": "System updates and installations that modify the boot process may fail."
  },
  "com.apple.bridgeOSUpdateProxy": {
    "description": "A proxy for handling updates to bridgeOS, the operating system that runs on the T2 chip and Apple Silicon Macs.",
    "impact": "The system will be unable to update the firmware, which is a critical security and stability risk."
  },
  "com.apple.idleassetsd": {
    "description": "A daemon that manages the download of assets when the system is idle.",
    "impact": "The system will not download resources in the background when idle."
  },
  "com.apple.installandsetup.systemmigrationd": {
    "description": "A daemon for migrating system data during a new setup or migration.",
    "impact": "The Migration Assistant may fail to transfer all system settings."
  },
  "com.apple.installcoordination_proxy": {
    "description": "A proxy for coordinating software installations.",
    "impact": "Software installations may fail, especially if multiple installations are happening."
  },
  "com.apple.installcoordinationd": {
    "description": "A daemon that coordinates software installations to prevent conflicts.",
    "impact": "Software installations may fail or become corrupted."
  },
  "com.apple.mobile.softwareupdated": {
    "description": "A daemon for software updates, with a 'mobile' origin.",
    "impact": "Software updates may fail."
  },
  "com.apple.softwareupdate_firstrun_tasks": {
    "description": "Tasks that run the first time after a software update.",
    "impact": "The system may not correctly finalize the setup after an update."
  },
  "com.apple.system_installd": {
    "description": "The system-level installer daemon.",
    "impact": "You will not be able to install software that requires system-level changes."
  },
  "com.apple.uninstalld": {
    "description": "A daemon for uninstalling software.",
    "impact": "You may have issues uninstalling some applications."
  },
  # Management & Development
  "com.apple.ManagedClient": {
    "description": "The primary agent for Mobile Device Management (MDM) and managed profiles from a server.",
    "impact": "If this Mac is managed by an organization (school, business), it will no longer receive configuration profiles or commands from the MDM server.",
  },
  "com.apple.RemotePairTool": {
    "description": "A tool used by developers with Xcode to pair with and debug remote devices, such as an Apple TV.",
    "impact": "Remote device debugging in Xcode will not work.",
  },
  "com.apple.ManagedClientAgent.agent": {
    "description": "User agent for MDM services.",
    "impact": "If this Mac is managed, it will no longer receive configuration or commands from the MDM server.",
  },
  "com.apple.ManagedSettingsAgent": {
    "description": "Agent for managed settings, often deployed via MDM.",
    "impact": "Enforced settings from an MDM server may not apply correctly.",
  },
  "com.apple.testmanagerd": {
    "description": "Daemon for managing automated testing with Xcode.",
    "impact": "Automated UI tests and other Xcode testing features will not work.",
  },
  "com.apple.mdmclient.agent": {
    "description": "The client agent for MDM.",
    "impact": "If this Mac is managed, it will no longer receive configuration or commands from the MDM server.",
  },
  "com.apple.dmd": {
    "description": "Device Management Daemon, a core part of the MDM framework.",
    "impact": "The system will be unable to communicate with an MDM server.",
  },
  "com.apple.studentd": {
    "description": "Daemon for managing configurations in an educational environment (e.g., Schoolwork app).",
    "impact": "Features for managed school environments will not work.",
  },
  "com.apple.remotemanagementd": {
    "description": "Core daemon for remote management services, including MDM.",
    "impact": "The system will not be able to be managed remotely.",
  },
  "com.apple.ManagedClient.enroll": {
    "description": "A process that handles the enrollment of a Mac into a Mobile Device Management (MDM) service.",
    "impact": "The Mac cannot be enrolled in an MDM solution."
  },
  "com.apple.ManagedClient.mechanism": {
    "description": "A ManagedClient mechanism that performs legacy managed-preferences tasks on managed devices.",
    "impact": "Certain MDM policies or commands may not be correctly applied."
  },
  "com.apple.RemoteDesktop.PrivilegeProxy": {
    "description": "A proxy for handling privileged operations for Apple Remote Desktop.",
    "impact": "Apple Remote Desktop may not be able to perform administrative tasks on remote machines."
  },
  "com.apple.devicemanagementclient.managedeventsd": {
    "description": "A daemon for handling managed events from a Mobile Device Management (MDM) server.",
    "impact": "If this Mac is managed, it will not correctly process events from the MDM server."
  },
  "com.apple.devicemanagementclient.teslad": {
    "description": "The device management enrollment daemon. It processes MDM enrollment, migration, and check-in requests.",
    "impact": "May cause issues with MDM functionality."
  },
  "com.apple.dt.RemotePairingDataVaultHelper": {
    "description": "A helper for securely storing pairing data for remote development with Xcode.",
    "impact": "Remote debugging with Xcode may fail or be less secure."
  },
  "com.apple.dt.automationmode-writer": {
    "description": "A tool for enabling automation mode for UI testing with Xcode.",
    "impact": "UI testing with Xcode will not work correctly."
  },
  "com.apple.dt.fetchsymbolsd": {
    "description": "A daemon for fetching debugging symbols for Xcode.",
    "impact": "Xcode will be unable to download debugging symbols, making it difficult to debug system-level code."
  },
  "com.apple.managedappdistributiond": {
    "description": "A daemon for distributing managed applications via MDM.",
    "impact": "If this Mac is managed, it will not receive applications pushed from the MDM server."
  },
  "com.apple.mdmclient.daemon": {
    "description": "The main daemon for the Mobile Device Management (MDM) client.",
    "impact": "If this Mac is managed, it will be unable to communicate with the MDM server."
  },
  "com.apple.swiftuitracingsupport.xpc": {
    "description": "A service for tracing and debugging SwiftUI applications.",
    "impact": "Developers will not be able to use certain debugging tools for SwiftUI."
  },
  "com.apple.testmanagerd.remote": {
    "description": "A remote version of the test manager for Xcode.",
    "impact": "You will not be able to run automated tests on a remote Mac from Xcode."
  },
  # Networking
  "com.apple.mDNSResponder": {
    "description": "The system-wide service for Multicast DNS and DNS Service Discovery (Bonjour). It's responsible for local network device discovery and some DNS resolutions.",
    "impact": "CRITICAL: Local network discovery (e.g., finding printers, file shares, AirPlay devices) will fail. Some aspects of internet name resolution will also break, causing significant network issues.",
  },
  "com.apple.configd": {
    "description": "Maintains the system's network configuration, including IP addresses, DNS settings, and network interface states.",
    "impact": "CRITICAL: The system will lose its ability to manage network configurations. You will likely lose all network connectivity.",
  },
  "com.apple.sharingd": {
    "description": "A central daemon for many sharing services, including AirDrop, Handoff, Instant Hotspot, and Remote Disc.",
    "impact": "Disabling this will break most Continuity features that allow Apple devices to work together.",
  },
  "com.apple.screensharing": {
    "description": "The main daemon for the Screen Sharing service.",
    "impact": "You will not be able to share your screen or remotely control another Mac.",
  },
  "com.apple.netbiosd": {
    "description": "Handles NetBIOS services for interacting with older Windows file/print sharing (SMB).",
    "impact": "Generally safe to disable if not in a mixed Windows/Mac network environment relying on NetBIOS.",
  },
  "com.apple.nesessionmanager": {
    "description": "Manages NetworkExtension sessions, which are used by VPN clients, content filters, and other network-modifying apps.",
    "impact": "VPN apps and other software that uses the NetworkExtension framework will not function.",
  },
  "com.apple.apsd": {
    "description": "Apple Push Notification service daemon. Manages push notifications from servers.",
    "impact": "CRITICAL: Push notifications for all applications (Mail, Messages, etc.) will not work.",
  },
  "com.apple.nsurlsessiond": {
    "description": "A core networking daemon that handles background network sessions for apps.",
    "impact": "Background downloads and uploads for many applications will fail.",
  },
  "com.apple.networkserviceproxy": {
    "description": "The network service proxy. It supports iCloud Private Relay and other proxied network services.",
    "impact": "May affect Private Relay and other network proxying features.",
  },
  "com.apple.neagent": {
    "description": "A generic agent for the Network Extension framework.",
    "impact": "VPN clients and other network filter apps may fail.",
  },
  "com.apple.captiveagent": {
    "description": "Agent for detecting and displaying login pages for captive Wi-Fi networks (e.g., in hotels or airports).",
    "impact": "You will not be able to log into captive Wi-Fi networks.",
  },
  "com.apple.intelligentroutingd": {
    "description": "The IntelligentRouting daemon. It makes automatic network-path decisions, such as choosing between Wi-Fi and cellular for better connectivity.",
    "impact": "The system may not intelligently switch between networks, potentially leading to connection issues.",
  },
  "com.apple.NetworkSharing": {
    "description": "The main daemon for the Internet Sharing feature.",
    "impact": "You will not be able to share your Mac's internet connection with other devices."
  },
  "com.apple.RFBEventHelper": {
    "description": "A helper for handling events in an RFB (Remote Framebuffer) session, used by VNC and screen sharing.",
    "impact": "May cause issues with controlling a Mac remotely via Screen Sharing or VNC."
  },
  "com.apple.SCHelper": {
    "description": "A helper for SystemConfiguration, which manages network settings.",
    "impact": "May cause issues with network configuration changes."
  },
  "com.apple.WirelessRadioManager": {
    "description": "Manages the various wireless radios in the Mac (Wi-Fi, Bluetooth).",
    "impact": "May cause instability or incorrect behavior of Wi-Fi and Bluetooth."
  },
  "com.apple.cfnetwork.cfnetworkagent": {
    "description": "An agent for the CFNetwork framework, which handles networking.",
    "impact": "May cause a variety of networking issues for applications."
  },
  "com.apple.dpdkswitchd": {
    "description": "A legacy, undocumented switching daemon. It is not present on current macOS releases and no public documentation describes its purpose.",
    "impact": "Unknown; this service is not present on current macOS.",
  },
  "com.apple.eapolcfg_auth": {
    "description": "A tool for configuring EAP (Extensible Authentication Protocol) over LAN (EAPOL), used in 802.1X network authentication.",
    "impact": "You will not be able to configure 802.1X network settings."
  },
  "com.apple.mDNSResponder.reloaded": {
    "description": "The mDNSResponder daemon (the label gains a '.reloaded' suffix on recent macOS). It provides Bonjour/mDNS and DNS Service Discovery for the system.",
    "impact": "Not a standalone service."
  },
  "com.apple.mDNSResponderHelper.reloaded": {
    "description": "The helper for mDNSResponder (the label gains a '.reloaded' suffix on recent macOS). It performs privileged Bonjour/mDNS tasks that the main responder cannot do itself.",
    "impact": "Not a standalone service."
  },
  "com.apple.msrpc.lsarpc": {
    "description": "A service for Microsoft Remote Procedure Call (MSRPC) for the Local Security Authority (LSA).",
    "impact": "Will break compatibility with certain Windows networking and authentication services."
  },
  "com.apple.msrpc.mdssvc": {
    "description": "An MSRPC service for Spotlight, for remote searching.",
    "impact": "Will break remote Spotlight searches from other machines."
  },
  "com.apple.msrpc.netlogon": {
    "description": "The Netlogon MSRPC service, for authenticating with Windows domain controllers.",
    "impact": "This Mac will not be able to authenticate in a Windows domain environment."
  },
  "com.apple.msrpc.srvsvc": {
    "description": "The Server Service MSRPC service, for remote administration of a server.",
    "impact": "Will break remote administration of this Mac from Windows machines."
  },
  "com.apple.msrpc.wkssvc": {
    "description": "The Workstation Service MSRPC service.",
    "impact": "Will break certain Windows networking functionalities."
  },
  "com.apple.nehelper": {
    "description": "A privileged helper for the Network Extension framework.",
    "impact": "VPN clients and other network filter applications will fail to install or run."
  },
  "com.apple.netauth.sys.auth": {
    "description": "A system-level authentication service for network accounts.",
    "impact": "Network-based logins will fail."
  },
  "com.apple.netauth.sys.gui": {
    "description": "A GUI component for network authentication.",
    "impact": "The user interface for logging in with network accounts will be broken."
  },
  "com.apple.nlcd": {
    "description": "Netlogon Client Daemon, for Windows domain integration.",
    "impact": "This Mac will not be able to properly integrate with a Windows domain."
  },
  "com.apple.nsurlsessiond_privileged": {
    "description": "A privileged version of `nsurlsessiond` for handling background network tasks that require higher permissions.",
    "impact": "Certain system-level background network operations will fail."
  },
  "com.apple.pcapd": {
    "description": "A daemon for packet capture, used by tools like Wireshark.",
    "impact": "You will not be able to capture network traffic on this Mac."
  },
  "com.apple.pfctl": {
    "description": "A tool to control the Packet Filter (PF) firewall.",
    "impact": "You will not be able to configure the low-level PF firewall."
  },
  "com.apple.postfix.master": {
    "description": "The master process for the Postfix mail server.",
    "impact": "This Mac cannot function as an SMTP server."
  },
  "com.apple.postfix.newaliases": {
    "description": "A tool to rebuild the Postfix alias database.",
    "impact": "You will not be able to manage mail aliases for the Postfix server."
  },
  "com.apple.racoon": {
    "description": "A legacy daemon for IKE (Internet Key Exchange), used in some VPNs.",
    "impact": "Older IKEv1 VPN connections will not work."
  },
  "com.apple.rpcbind": {
    "description": "A service that maps RPC services to the ports they run on, used by NFS.",
    "impact": "NFS and other RPC-based services will not function."
  },
  "com.apple.srp-mdns-proxy": {
    "description": "A proxy for Secure Remote Password (SRP) over mDNS.",
    "impact": "May impact the security of some local network services."
  },
  "com.apple.statd.notify": {
    "description": "A component of the network status monitor, used by NFS.",
    "impact": "May cause issues with NFS file locking."
  },
  "com.apple.threadradiod": {
    "description": "The daemon for the Thread networking protocol, used by some smart home devices.",
    "impact": "Thread-based smart home devices will not function."
  },
  "com.apple.wifip2pd": {
    "description": "The daemon for Wi-Fi Peer-to-Peer, which underlies features like AirDrop.",
    "impact": "AirDrop and other direct Wi-Fi connection features will not work."
  },
  "com.apple.wifivelocityd": {
    "description": "The Wi-Fi analytics daemon. It collects Wi-Fi performance data and supports roaming and connection-quality analysis.",
    "impact": "Roaming between Wi-Fi access points may be less reliable."
  },
  # Safari & WebKit
  "com.apple.SafariHistoryServiceAgent": {
    "description": "Agent for managing Safari's Browse history.",
    "impact": "Safari history will not be saved or may become corrupt.",
  },
  "com.apple.SafariBookmarksSyncAgent": {
    "description": "Agent for syncing Safari bookmarks via iCloud.",
    "impact": "Safari bookmarks will not sync across your devices.",
  },
  "com.apple.Safari.PasswordBreachAgent": {
    "description": "Agent that checks for compromised passwords saved in Safari.",
    "impact": "Safari's password breach detection feature will not work.",
  },
  "com.apple.SafariNotificationAgent": {
    "description": "Agent for handling web push notifications from Safari.",
    "impact": "You will not receive push notifications from websites.",
  },
  "com.apple.SafariLaunchAgent": {
    "description": "An agent that assists with launching Safari.",
    "impact": "Safari may not launch correctly or restore its previous state.",
  },
  "com.apple.Safari.History": {
    "description": "A process related to accessing Safari's Browse history.",
    "impact": "Safari history features may not work correctly.",
  },
  "com.apple.webkit.webpushd": {
    "description": "Daemon for the Web Push notification standard used by browsers.",
    "impact": "Web push notifications will not work.",
  },
  "com.apple.webprivacyd": {
    "description": "Daemon related to privacy features in WebKit, such as tracking prevention.",
    "impact": "Intelligent Tracking Prevention and other privacy features in Safari may fail.",
  },
  "com.apple.webinspectord": {
    "description": "The backend for the Web Inspector developer tool.",
    "impact": "You will not be able to use the Web Inspector to debug websites in Safari.",
  },
  "com.apple.swcd": {
    "description": "Shared Web Credentials daemon, manages links between apps and websites (Universal Links).",
    "impact": "Universal Links that should open in an app will open in Safari instead.",
  },
  # Maps & Location
  "com.apple.locationd": {
    "description": "The primary daemon for all Location Services on macOS.",
    "impact": "Prevents all apps (Maps, Weather, Find My) and system services from determining your Mac's location.",
  },
  "com.apple.geod": {
    "description": "The main daemon for GeoServices, providing location, mapping, and routing information to applications.",
    "impact": "Maps and all other location-based services will be severely degraded or non-functional.",
  },
  "com.apple.routined": {
    "description": "Learns your frequently visited locations to provide proactive suggestions (e.g., traffic alerts, significant locations).",
    "impact": "The system will not learn your significant locations, affecting proactive features and location-based suggestions.",
  },
  "com.apple.Maps.mapspushd": {
    "description": "Manages push notifications for Apple Maps.",
    "impact": "You will not receive notifications from Maps, such as turn-by-turn directions sent from another device.",
  },
  "com.apple.countryd": {
    "description": "A service that determines the user's country based on network information.",
    "impact": "The system may not be able to suggest the correct region or show region-specific services."
  },
  # Photos & Media
  "com.apple.photoanalysisd": {
    "description": "The agent that performs analysis of the photo library for Memories, People, and object/scene recognition for search.",
    "impact": "The intelligent features of the Photos app will be disabled. People, Memories, and search by content will not work.",
  },
  "com.apple.photolibraryd": {
    "description": "The primary agent for the Photos library. It handles all requests and modifications to the library.",
    "impact": "The Photos app will not be able to access or modify your photo library.",
  },
  "com.apple.mediaanalysisd": {
    "description": "A daemon that performs analysis of media in the background for Photos and other apps.",
    "impact": "Features that rely on analyzing photos and videos (like object recognition) may be affected.",
  },
  "com.apple.mediastream.mstreamd": {
    "description": "The daemon for My Photo Stream and Shared Albums.",
    "impact": "My Photo Stream and Shared Albums will no longer function.",
  },
  "com.apple.AMPArtworkAgent": {
    "description": "The agent responsible for fetching and managing artwork for Music.app and TV.app.",
    "impact": "Album and movie/TV show artwork may not appear in the Music and TV apps.",
  },
  "com.apple.avconferenced": {
    "description": "Provides the backend for audio and video conferencing (e.g., FaceTime, and third-party apps using the framework).",
    "impact": "FaceTime, Photo Booth, and third-party video conferencing apps will likely fail.",
  },
  "com.apple.amp.mediasharingd": {
    "description": "Daemon for sharing media from the Music app (Home Sharing).",
    "impact": "Home Sharing for music and media will not work.",
  },
  "com.apple.AMPLibraryAgent": {
    "description": "Agent for managing the Apple Media Player (Music.app) library.",
    "impact": "The Music app may not be able to access or modify its library.",
  },
  "com.apple.tonelibraryd": {
    "description": "Daemon for managing the tone library (ringtones, text tones).",
    "impact": "Syncing and managing custom ringtones will not work.",
  },
  "com.apple.rcd": {
    "description": "Remote Control Daemon. It handles media control events from headphones and other remotes.",
    "impact": "The play/pause and volume buttons on your headphones or remote may not work.",
  },
  "com.apple.musicd": {
    "description": "The daemon for the Music app.",
    "impact": "The Music app may not function correctly."
  },
  # Proactive & Intelligence
  "com.apple.suggestd": {
    "description": "A core daemon for providing suggestions throughout the OS (Spotlight, Safari, Look Up) by processing user content.",
    "impact": "You will not receive proactive suggestions in various parts of macOS.",
  },
  "com.apple.parsecd": {
    "description": "Powers Siri and Spotlight suggestions by fetching results from the web.",
    "impact": "Siri and Spotlight will not be able to provide web-based suggestions and results.",
  },
  "com.apple.intelligenceplatformd": {
    "description": "A core daemon for the on-device intelligence platform that powers many smart features by analyzing on-device content.",
    "impact": "Will likely break a wide range of intelligent features, including Proactive suggestions and the on-device knowledge graph.",
  },
  "com.apple.knowledge-agent": {
    "description": "Works with the system's knowledge base to provide info for Spotlight and Siri Suggestions.",
    "impact": "Spotlight and Siri Suggestions will be less informative and may not provide rich results.",
  },
  "com.apple.BiomeAgent": {
    "description": "Collects and manages on-device intelligence for features like Proactive suggestions.",
    "impact": "Proactive suggestions and personalized features will be less effective or may not work.",
  },
  "com.apple.coreduetd": {
    "description": "The Duet Activity Scheduler. It intelligently monitors usage to optimize performance and power.",
    "impact": "May lead to less efficient background processing and reduced battery life.",
  },
  "com.apple.proactiveeventtrackerd": {
    "description": "Tracks events to power proactive suggestions.",
    "impact": "Proactive features like 'time to leave' alerts will not work.",
  },
  "com.apple.spotlightknowledged": {
    "description": "Powers knowledge-based results in Spotlight search.",
    "impact": "Spotlight will provide less intelligent and context-aware results.",
  },
  "com.apple.callintelligenced": {
    "description": "Provides intelligence features for calls, such as identifying callers.",
    "impact": "Caller ID and other smart calling features may not work.",
  },
  "com.apple.synapse.contentlinkingd": {
    "description": "Links content across apps for proactive suggestions.",
    "impact": "The system's ability to provide proactive, cross-app suggestions will be reduced.",
  },
  "com.apple.attentionawarenessd": {
    "description": "The daemon for Attention Aware features, which can tell when you are looking at the screen.",
    "impact": "Features like preventing the screen from dimming while you are reading will not work."
  },
  "com.apple.contextstored": {
    "description": "Stores contextual data for proactive and intelligence features.",
    "impact": "Siri and other proactive features will be less intelligent and context-aware."
  },
  "com.apple.modelcatalogd": {
    "description": "A daemon that manages catalogs of machine learning models.",
    "impact": "The system will be unable to download or manage machine learning models for features like Siri and Photos."
  },
  "com.apple.modelmanagerd": {
    "description": "Manages machine learning models on the device.",
    "impact": "Machine learning features may fail to load their required models."
  },
  "com.apple.ospredictiond": {
    "description": "The OSIntelligence prediction daemon. It predicts battery drain and inactivity to drive Low Power Mode and energy-saving decisions.",
    "impact": "The system may be less efficient at predicting user behavior to optimize performance."
  },
  "com.apple.uarpassetmanagerd": {
    "description": 'UARP asset helper launched as /usr/libexec/uarpassetmanagerd. Its precise responsibilities are not documented in the installed launch configuration.',
    "impact": 'The full effect of disabling this helper is not verified; accessory-related functionality may be affected.'
  },
  "com.apple.uarpd": {
    "description": 'Manages UARP accessory devices.',
    "impact": 'Disabling may interfere with accessory management or updates. The manual does not document the complete impact.'
  },
  "com.apple.uarphidd": {
    "description": 'UARP helper launched as /usr/libexec/uarphidd. Its precise responsibilities are not documented in the installed launch configuration.',
    "impact": 'The full effect of disabling this helper is not verified; accessory-related functionality may be affected.'
  },
  # Security & Keychain
  "com.apple.securityd": {
    "description": "A core security daemon responsible for managing the keychain, certificates, and cryptographic services.",
    "impact": "CRITICAL: System-wide authentication and keychain access will fail. Many apps will not launch. System may become unstable or unusable.",
  },
  "com.apple.tccd": {
    "description": "Transparency, Consent, and Control Daemon. Manages privacy permissions for apps accessing your contacts, photos, microphone, etc.",
    "impact": "CRITICAL: The privacy permission system will break. Apps will not be able to request access to sensitive data, and existing permissions may not be enforced.",
  },
  "com.apple.syspolicyd": {
    "description": "System Policy Daemon. Enforces security policies, including Gatekeeper and Notarization checks for applications.",
    "impact": "CRITICAL: Security checks for launching applications will fail. This could prevent apps from launching or compromise system security by allowing unverified code to run.",
  },
  "com.apple.authd": {
    "description": "The authorization services daemon. It handles requests for privileged operations (e.g., when you type your password to install software).",
    "impact": "CRITICAL: You will not be able to perform any action that requires administrator privileges.",
  },
  "com.apple.cryptexd": {
    "description": "Manages cryptexes, which are cryptographically signed and sealed volumes containing system content. This is a core security feature that ensures the integrity of the operating system.",
    "impact": "CRITICAL: Disabling this is highly discouraged. It will break system integrity checks and may prevent macOS from booting or updating correctly. It compromises a fundamental security layer of the OS.",
  },
  "com.apple.lockd": {
    "description": "The file locking daemon used by NFS. It prevents multiple clients from concurrently modifying the same file.",
    "impact": "If using NFS, file corruption can occur. Safe to disable if NFS is not in use.",
  },
  "com.apple.devicecheckd": {
    "description": "A service for apps to verify that they are running on a genuine, unmodified Apple device.",
    "impact": "Some apps that use DeviceCheck for security may fail to work.",
  },
  "com.apple.MRTa": {
    "description": "An agent related to Apple's Malware Removal Tool.",
    "impact": "The system's anti-malware capabilities will be reduced.",
  },
  "com.apple.trustd.agent": {
    "description": "User agent for the trust daemon, which verifies digital certificates.",
    "impact": "Certificate validation for apps and websites may fail.",
  },
  "com.apple.TrustedPeersHelper": {
    "description": "A helper for managing trusted devices for services like iCloud Keychain.",
    "impact": "iCloud Keychain and other secure services may fail to sync with other devices.",
  },
  "com.apple.XprotectFramework.PluginService": {
    "description": "A plugin service for the XProtect anti-malware framework.",
    "impact": "XProtect's ability to detect and block malware will be impaired.",
  },
  "com.apple.LocalAuthentication.UIAgent": {
    "description": "User interface agent for Local Authentication (Touch ID and password prompts).",
    "impact": "Touch ID and password prompts for apps will not appear.",
  },
  "com.apple.security.KeychainStasher": {
    "description": "A service for stashing keychain data.",
    "impact": "Could affect keychain reliability and data integrity.",
  },
  "com.apple.secinitd": {
    "description": "Initializes security services for a user session.",
    "impact": "User login may fail, or security services may not work correctly within the session.",
  },
  "com.apple.ctkbind": {
    "description": "A process related to the CryptoTokenKit framework for smart cards.",
    "impact": "Smart card functionalities may fail.",
  },
  "com.apple.alf.useragent": {
    "description": "User agent for the Application Layer Firewall (ALF).",
    "impact": "The application firewall may not function correctly.",
  },
  "com.apple.lockdownmoded": {
    "description": "The daemon that manages Lockdown Mode, a high-security mode that restricts features.",
    "impact": "You will not be able to enable or disable Lockdown Mode.",
  },
  "com.apple.XProtect.agent.scan": {
    "description": "An agent that performs scans for the XProtect anti-malware engine.",
    "impact": "The system's anti-malware scanning will be disabled.",
  },
  "com.apple.SecureBackupDaemon": {
    "description": "The iCloud Keychain secure backup daemon. It encrypts and stores keychain backups in iCloud.",
    "impact": "Secure backups of sensitive data will not be performed.",
  },
  "com.apple.security.agent": {
    "description": "A general agent for the security framework.",
    "impact": "Various security prompts and operations may fail.",
  },
  "com.apple.secd": {
    "description": "The Security Daemon, a core process for managing keychain and other security data.",
    "impact": "CRITICAL: Keychain access and many authentication services will fail.",
  },
  "com.apple.akd": {
    "description": "AuthKit Daemon. Manages iCloud authentication tokens and credentials.",
    "impact": "CRITICAL: You will not be able to sign into iCloud or any services that use Apple ID.",
  },
  "com.apple.AppSSOAgent": {
    "description": "Agent for Single Sign-On extensions in applications.",
    "impact": "Single Sign-On functionality for enterprise and other apps will not work.",
  },
  "com.apple.CoreAuthentication.agent": {
    "description": "Agent for the core authentication framework.",
    "impact": "System and app-level authentication prompts may fail.",
  },
  "com.apple.keychainsharingmessagingd": {
    "description": "Handles messaging for keychain sharing and syncing.",
    "impact": "iCloud Keychain syncing will be impaired.",
  },
  "com.apple.security.keychain-circle-notification": {
    "description": "Handles notifications for iCloud Keychain syncing.",
    "impact": "You may not receive notifications about the status of iCloud Keychain.",
  },
  "com.apple.frauddefensed": {
    "description": "The TrustKit fraud-defense daemon. It evaluates device and transaction signals for fraud protection in Apple services.",
    "impact": "The system's ability to detect and prevent fraudulent transactions will be reduced.",
  },
  "com.apple.AppSSOAgent.login": {
    "description": "A login-specific agent for the App Single Sign-On (SSO) framework.",
    "impact": "Single Sign-On functionality for applications may not work correctly at the time of user login."
  },
  "com.apple.AppSSODaemon": {
    "description": "The primary daemon for the App Single Sign-On (SSO) framework, which allows users to sign in once to a set of related apps.",
    "impact": "Enterprise and other applications that rely on SSO will not function as expected."
  },
  "com.apple.AppleCredentialManagerDaemon": {
    "description": "Manages user credentials for various services, potentially related to password and passkey management.",
    "impact": "Issues may arise with saving, retrieving, or syncing credentials across the system and devices."
  },
  "com.apple.CodeSigningHelper": {
    "description": "Assists with code signing verification for applications and system components.",
    "impact": "The system may fail to properly verify the integrity and origin of applications, potentially preventing them from launching or compromising security."
  },
  "com.apple.CoreAuthentication.daemon": {
    "description": "The main daemon for the CoreAuthentication framework, handling authentication requests.",
    "impact": "System-wide authentication services, including password and Touch ID prompts, may fail."
  },
  "com.apple.CryptoTokenKit.ahp": {
    "description": "The CryptoTokenKit Authentication Hints Provider. It supplies authentication hints (for example PIN prompts) for smart cards and hardware tokens.",
    "impact": "Authentication using smart cards or other hardware tokens may fail."
  },
  "com.apple.GSSCred": {
    "description": "Manages Generic Security Service (GSS) credentials, often used in Kerberos authentication.",
    "impact": "Single sign-on in enterprise environments using Kerberos will likely fail."
  },
  "com.apple.Kerberos.digest-service": {
    "description": "A service for Kerberos that provides digest-based authentication.",
    "impact": "Certain Kerberos authentication methods will not be available."
  },
  "com.apple.Kerberos.kadmind": {
    "description": "The Kerberos administration daemon, used for managing a Kerberos database.",
    "impact": "You will not be able to administer a Kerberos server from this Mac."
  },
  "com.apple.Kerberos.kcm": {
    "description": "The Kerberos Credential Manager daemon, which manages Kerberos tickets.",
    "impact": "Kerberos-based authentication will fail."
  },
  "com.apple.Kerberos.kdc": {
    "description": "The Kerberos Key Distribution Center, which issues Kerberos tickets.",
    "impact": "This Mac cannot function as a Kerberos KDC."
  },
  "com.apple.Kerberos.kpasswdd": {
    "description": "The Kerberos password changing daemon.",
    "impact": "Users will not be able to change their passwords in a Kerberos environment."
  },
  "com.apple.MRTd": {
    "description": "The daemon for Apple's Malware Removal Tool (MRT).",
    "impact": "The system's built-in malware scanning and removal capabilities will be disabled."
  },
  "com.apple.MobileFileIntegrity": {
    "description": "A service that verifies the integrity of files on the system, particularly for mobile-derived components.",
    "impact": "May compromise system security by not verifying the integrity of certain system files."
  },
  "com.apple.TrustEvaluationAgent.system": {
    "description": "A system-level agent for evaluating the trust of certificates and code signatures.",
    "impact": "The system may fail to properly evaluate trust for certificates and applications, leading to security or connectivity issues."
  },
  "com.apple.XProtect.daemon.scan": {
    "description": "A daemon that performs scans for the XProtect anti-malware engine.",
    "impact": "The system's built-in malware scanning will be disabled."
  },
  "com.apple.XProtect.daemon.scan.startup": {
    "description": "Performs an XProtect scan at startup.",
    "impact": "The system will not perform its initial malware scan at boot."
  },
  "com.apple.alf": {
    "description": "Application Layer Firewall daemon.",
    "impact": "The macOS application firewall will not function."
  },
  "com.apple.alwaysonexclavesd": {
    "description": "The AlwaysOnExclaves daemon. It manages always-on isolated (exclave) services on the Secure Enclave.",
    "impact": "'Always On' processor features that rely on the secure enclave may not work."
  },
  "com.apple.applekeystored": {
    "description": "Manages the system's keystore for cryptographic keys.",
    "impact": "The system will be unable to store and retrieve cryptographic keys, breaking many security features."
  },
  "com.apple.biomed": {
    "description": "A daemon for biometric services.",
    "impact": "Biometric authentication, such as Touch ID, may not function correctly."
  },
  "com.apple.biometrickitd": {
    "description": "The main daemon for the BiometricKit framework, which underlies Touch ID.",
    "impact": "Touch ID will not function."
  },
  "com.apple.configureLocalKDC": {
    "description": "A tool to configure a local Kerberos Key Distribution Center (KDC).",
    "impact": "You will not be able to set up this Mac as a Kerberos server."
  },
  "com.apple.csrutil.report": {
    "description": "A tool that reports the status of System Integrity Protection (SIP).",
    "impact": "The system will not be able to report on the status of SIP."
  },
  "com.apple.endpointsecurity.endpointsecurityd": {
    "description": "The main daemon for the Endpoint Security framework, used by third-party security software.",
    "impact": "Security applications that use the Endpoint Security framework will not function."
  },
  "com.apple.gkreport": {
    "description": "A service that reports on Gatekeeper activity.",
    "impact": "The system will not be able to log or report on Gatekeeper's security actions."
  },
  "com.apple.gssd": {
    "description": "Generic Security Service daemon, primarily for Kerberos.",
    "impact": "Kerberos authentication will fail."
  },
  "com.apple.kcproxy": {
    "description": "A proxy for Kerberos Credential Manager.",
    "impact": "Kerberos authentication may fail."
  },
  "com.apple.kuncd": {
    "description": "Kerberos User-to-User Name and Credential daemon.",
    "impact": "A specific Kerberos authentication mechanism will not be available."
  },
  "com.apple.mobile.keybagd": {
    "description": "Manages 'keybags,' which store cryptographic keys for protecting user data.",
    "impact": "A critical service for data protection; its absence could lead to data loss or an unbootable system."
  },
  "com.apple.ocspd": {
    "description": "The Online Certificate Status Protocol (OCSP) daemon, for checking the revocation status of SSL/TLS certificates.",
    "impact": "The system will be unable to check if a certificate has been revoked, which is a security risk."
  },
  "com.apple.online-auth-agent.xpc": {
    "description": "An agent for online authentication services.",
    "impact": "May cause issues with signing into online accounts."
  },
  "com.apple.sandboxd": {
    "description": "The daemon that enforces application sandboxing.",
    "impact": "A critical security feature; its absence will allow applications to access data they shouldn't, posing a major security risk."
  },
  "com.apple.security.agent.login": {
    "description": "A security agent that runs at login.",
    "impact": "May cause issues with authentication or security policy enforcement at login."
  },
  "com.apple.security.agent.login.00000000-0000-0000-0000-0000000186A1": {
    "description": "A specific instance of the login security agent.",
    "impact": "Similar to `security.agent.login`, may cause login issues."
  },
  "com.apple.security.authhost": {
    "description": "A host for authentication plugins.",
    "impact": "May prevent third-party authentication methods from working."
  },
  "com.apple.security.authhost.00000000-0000-0000-0000-0000000186A1": {
    "description": "A specific instance of the authentication host.",
    "impact": "Similar to `security.authhost`."
  },
  "com.apple.security.authtrampoline": {
    "description": "A 'trampoline' for launching authentication processes with the correct permissions.",
    "impact": "May cause authentication prompts to fail."
  },
  "com.apple.security.cryptexd": {
    "description": "An alias for `com.apple.cryptexd`, which manages secure system volumes.",
    "impact": "Critical for system integrity and boot."
  },
  "com.apple.security.syspolicy": {
    "description": "An alias for `com.apple.syspolicyd`, which enforces Gatekeeper and other security policies.",
    "impact": "Critical for application security."
  },
  "com.apple.securityd.system": {
    "description": "The system-level security daemon.",
    "impact": "A critical service; its absence will lead to system-wide security failures."
  },
  "com.apple.systemkeychain": {
    "description": "A service for interacting with the system keychain.",
    "impact": "Applications will not be able to access items stored in the system keychain."
  },
  "com.apple.taskgated": {
    "description": "A daemon that handles task gating, a security feature related to code signing.",
    "impact": "A critical security service; its absence may prevent applications from launching or compromise system security."
  },
  "com.apple.taskgated-helper": {
    "description": "A helper for `taskgated`.",
    "impact": "`taskgated` may not function correctly."
  },
  "com.apple.tccd.system": {
    "description": "The system-level daemon for privacy permissions.",
    "impact": "A critical service for enforcing privacy settings."
  },
  "com.apple.trustd": {
    "description": "The main daemon for evaluating the trust of certificates and code signatures.",
    "impact": "The system will be unable to verify certificates, breaking HTTPS connections and code signature checks. A critical security service."
  },
  "com.apple.trustdFileHelper": {
    "description": "A helper for `trustd`.",
    "impact": "`trustd` may not function correctly."
  },
  "com.apple.xpc.roleaccountd": {
    "description": "A daemon for managing role accounts.",
    "impact": "May impact enterprise environments that use role-based access control."
  },
  # Siri & Dictation
  "com.apple.assistantd": {
    "description": "The main daemon for Siri, handling voice commands, processing requests, and providing responses.",
    "impact": "Siri will become non-functional.",
  },
  "com.apple.corespeechd": {
    "description": "Manages the speech recognition capabilities of the system for Siri, Dictation, etc.",
    "impact": "Will break all speech recognition functionalities.",
  },
  "com.apple.siriknowledged": {
    "description": "Manages the knowledge base Siri uses to answer questions and provide information.",
    "impact": "Will likely limit Siri's ability to answer factual questions.",
  },
  "com.apple.Siri.agent": {
    "description": "An agent that supports the functionality of Siri on the desktop.",
    "impact": "May impact the reliability and performance of Siri.",
  },
  "com.apple.shazamd": {
    "description": "Daemon for the Shazam music recognition service.",
    "impact": "Shazam features, including music recognition from the Control Center, will not work.",
  },
  "com.apple.speech.speechsynthesisd.x86_64": {
    "description": "The text-to-speech synthesis server.",
    "impact": "All text-to-speech functionality will be broken.",
  },
  "com.apple.speech.synthesisserver": {
    "description": "The main text-to-speech synthesis server.",
    "impact": "All text-to-speech functionality will be broken.",
  },
  "com.apple.speech.speechdatainstallerd": {
    "description": "Installs data for speech services, such as new voices.",
    "impact": "You will not be able to download and install new voices for text-to-speech or Siri.",
  },
  "com.apple.siri.context.service": {
    "description": "Service that provides context to Siri for more relevant responses.",
    "impact": "Siri's responses may become less personalized and context-aware.",
  },
  "com.apple.DictationIM": {
    "description": "An input method for the Dictation feature.",
    "impact": "Dictation will not function.",
  },
  "com.apple.corespeechd_system": {
    "description": "The system-level daemon for speech recognition.",
    "impact": "System-wide speech recognition features will fail."
  },
  "com.apple.siri.acousticsignature": {
    "description": "A service that analyzes acoustic signatures for 'Hey Siri'.",
    "impact": "The 'Hey Siri' feature may not work correctly."
  },
  # System Core
  "com.apple.coreservicesd": {
    "description": "A master daemon that oversees other core services. It's one of the first processes to launch.",
    "impact": "CRITICAL: Disabling this will cause widespread system failure and will almost certainly prevent the system from booting.",
  },
  "com.apple.runningboardd": {
    "description": "Manages the lifecycle of applications and processes, tracking their state (running, suspended, etc.).",
    "impact": "CRITICAL: Application lifecycle management will fail, leading to severe instability, apps not launching, and incorrect resource management.",
  },
  "com.apple.lsd": {
    "description": "Launch Services Daemon. Manages the database that associates documents with the applications that can open them.",
    "impact": "CRITICAL: Double-clicking files to open them will not work. The 'Open With' menu will be broken. The system will not know what application to use for any file type.",
  },
  "com.apple.loginwindow": {
    "description": "The process that manages the user login window and user sessions.",
    "impact": "CRITICAL: You will not be able to log in to your Mac. Disabling this will lock you out of your system.",
  },
  "com.apple.logind": {
    "description": "Handles the login process and user session setup after authentication.",
    "impact": "CRITICAL: User sessions will fail to start correctly after login.",
  },
  "com.apple.opendirectoryd": {
    "description": "Open Directory Daemon. Manages access to directory services, including local user accounts and network accounts.",
    "impact": "CRITICAL: You will not be able to log in, as the system will be unable to look up user account information.",
  },
  "com.apple.notifyd": {
    "description": "The notification distribution daemon. It allows processes to exchange stateless notifications.",
    "impact": "CRITICAL: A fundamental inter-process communication mechanism will be disabled, leading to unpredictable system-wide failures.",
  },
  "com.apple.distnoted": {
    "description": "Distributed Notification Center daemon. Another key IPC mechanism for processes to communicate.",
    "impact": "CRITICAL: Will cause severe system instability as many processes rely on it to coordinate.",
  },
  "com.apple.cfprefsd": {
    "description": "CoreFoundation Preferences Daemon. Manages the reading and writing of preference files for the OS and applications.",
    "impact": "CRITICAL: The system and applications will be unable to save or read their settings, leading to default configurations on every launch and major instability.",
  },
  "com.apple.contactsd": {
    "description": "The background daemon that manages the central database for the Contacts app.",
    "impact": "Contacts will not sync or be available to other apps. Apps that read contacts may behave oddly or show no contact data.",
  },
  "com.apple.xpc.smd": {
    "description": "Service Management Daemon. One of the core processes of launchd, responsible for managing XPC services.",
    "impact": "CRITICAL: This is a fundamental system process. Disabling it will likely cause system instability or prevent it from booting.",
  },
  "com.apple.mds": {
    "description": "Metadata Server, a core part of Spotlight.",
    "impact": "CRITICAL: Spotlight indexing and searching will be completely broken.",
  },
  "com.apple.timed": {
    "description": "The system time daemon, which synchronizes the clock with network time servers.",
    "impact": "The system clock will drift and become inaccurate, which can break network authentication and other time-sensitive operations.",
  },
  "com.apple.deleted_helper": {
    "description": "A helper utility for managing the 'deleted users' process.",
    "impact": "Issues may arise when deleting user accounts from the system.",
  },
  "com.apple.recentsd": {
    "description": "Manages the 'Recents' list in Finder and other applications.",
    "impact": "The 'Recents' folder and menu items will not update.",
  },
  "com.apple.xpc.otherbsd": {
    "description": "A generic XPC service that may provide compatibility with older BSD-layer functionalities.",
    "impact": "Unknown, but could cause instability as its purpose is not clearly defined.",
  },
  "com.apple.timezoneupdates.tznotify": {
    "description": "Notifies the system about timezone updates.",
    "impact": "The system may not automatically update its timezone information.",
  },
  "com.apple.cfprefsd.xpc.agent": {
    "description": "User-level agent for managing preferences.",
    "impact": "CRITICAL: Applications will be unable to save or read their settings.",
  },
  "com.apple.xpc.loginitemregisterd": {
    "description": "Daemon for registering login items.",
    "impact": "The system for adding or removing login items will be broken.",
  },
  "com.apple.coreservices.useractivityd": {
    "description": "Manages user activity for Handoff and other continuity features.",
    "impact": "Handoff will not function correctly.",
  },
  "com.apple.cache_delete": {
    "description": "A service that intelligently deletes cache files to free up storage space.",
    "impact": "The system will not be able to automatically clear caches, potentially leading to wasted disk space.",
  },
  "com.apple.UserEventAgent-Aqua": {
    "description": "Manages user-level system events within the Aqua (GUI) session.",
    "impact": "CRITICAL: A fundamental part of the user session; disabling will cause severe instability.",
  },
  "com.apple.backgroundtaskmanagement.agent": {
    "description": "Manages background tasks for applications.",
    "impact": "Apps may not be able to run tasks in the background correctly.",
  },
  "com.apple.coreservices.sharedfilelistd": {
    "description": "Manages the 'Recent Items' list and other shared file lists.",
    "impact": "The 'Recent Items' menu in apps will not work.",
  },
  "com.apple.containermanagerd": {
    "description": "Manages app containers to enforce sandboxing.",
    "impact": "CRITICAL: The app sandbox will be broken, compromising system security and stability.",
  },
  "com.apple.accountsd": {
    "description": "The central daemon for managing accounts in System Settings (iCloud, Google, etc.).",
    "impact": "You will not be able to add, remove, or manage accounts in System Settings.",
  },
  "com.apple.coreservices.uiagent": {
    "description": "Provides user interface elements for core services, such as app launch warnings.",
    "impact": "Important system dialogs and warnings may not appear.",
  },
  "com.apple.distnoted.xpc.agent": {
    "description": "User-level agent for the distributed notification system.",
    "impact": "CRITICAL: A fundamental inter-process communication mechanism will be disabled.",
  },
  "com.apple.AppleQEMUGuestAgent": {
    "description": "A service that runs within a macOS virtual machine to improve integration with the QEMU host.",
    "impact": "If running macOS in a VM on QEMU, features like clipboard sharing and automatic resolution changing will not work. Not relevant for bare-metal installs."
  },
  "com.apple.ContainerMigrationService": {
    "description": "Migrates application container data during system or application updates.",
    "impact": "Application data may not be correctly migrated after an update, potentially leading to data loss or app malfunctions."
  },
  "com.apple.DASDelegateService": {
    "description": "A delegate service for the Duet Activity Scheduler (DAS), which manages background tasks.",
    "impact": "Background task scheduling may be less efficient, potentially impacting performance and battery life."
  },
  "com.apple.UserEventAgent-System": {
    "description": "A system-level agent for managing user events.",
    "impact": "A critical component for system stability; its absence could lead to widespread issues."
  },
  "com.apple.Virtualization.AppleVirtualPlatformHIDBridge": {
    "description": "A bridge for Human Interface Devices (HID) in Apple's Virtualization framework.",
    "impact": "If using macOS virtual machines, keyboard and mouse input may not work correctly."
  },
  "com.apple.backgroundtaskmanagementd": {
    "description": "Manages background tasks for applications.",
    "impact": "Applications may not be able to run tasks in the background correctly."
  },
  "com.apple.bsd.dirhelper": {
    "description": "A helper for directory services at the BSD level.",
    "impact": "May cause issues with user and group lookups, potentially preventing logins."
  },
  "com.apple.cfprefsd.xpc.daemon": {
    "description": "The system-level daemon for managing preferences.",
    "impact": "The system will be unable to read or write its own preference files, leading to major instability."
  },
  "com.apple.containermanagerd.system": {
    "description": "The system-level daemon for managing application sandboxes.",
    "impact": "The application sandboxing security feature will be broken, posing a security risk."
  },
  "com.apple.corerepaird": {
    "description": "A daemon that may attempt to repair corrupted core system components.",
    "impact": "The system will lose some of its ability to self-heal from software corruption."
  },
  "com.apple.coreservices.appleevents": {
    "description": "The daemon that handles Apple Events, a core inter-process communication technology.",
    "impact": "Many applications that use AppleScript or communicate with each other will be broken."
  },
  "com.apple.coreservices.launchservicesd": {
    "description": "The Launch Services daemon, which manages the relationship between applications and documents.",
    "impact": "The system will not know which application to use to open a file, breaking a fundamental user experience."
  },
  "com.apple.dasd": {
    "description": "The Duet Activity Scheduler daemon, which manages background tasks.",
    "impact": "Background task scheduling will be less efficient, potentially impacting performance and battery life."
  },
  "com.apple.devicerecoveryd": {
    "description": "A daemon for Device Recovery Mode (DFU).",
    "impact": "You will not be able to restore the firmware on this Mac using another Mac."
  },
  "com.apple.distnoted.xpc.daemon": {
    "description": "The system-level daemon for the distributed notification system.",
    "impact": "A critical inter-process communication mechanism; its absence will lead to severe system instability."
  },
  "com.apple.dspluginhelperd": {
    "description": "A helper for Directory Service plugins.",
    "impact": "May cause issues with third-party directory service integrations."
  },
  "com.apple.dynamic_pager": {
    "description": "Manages virtual memory paging.",
    "impact": "A critical system service; its absence would likely cause an unbootable system."
  },
  "com.apple.efilogin-helper": {
    "description": "A helper for the EFI (Extensible Firmware Interface) login process.",
    "impact": "May cause issues with the boot process, especially with features like FileVault."
  },
  "com.apple.erasecontentsettingshelperd": {
    "description": "A helper for the 'Erase All Content and Settings' feature.",
    "impact": "The 'Erase All Content and Settings' feature will not work."
  },
  "com.apple.loginwindow.E4B99820-2E63-4075-99ED-7E1B4FCAC597": {
    "description": "A specific instance of the login window process, likely for a particular user session.",
    "impact": "May cause issues with logging in or out."
  },
  "com.apple.memory-maintenance": {
    "description": "A service that performs memory maintenance tasks.",
    "impact": "The system may be less efficient at managing memory."
  },
  "com.apple.metadata.mds": {
    "description": "An alias for `com.apple.mds`, the main Spotlight metadata server.",
    "impact": "Spotlight will be broken."
  },
  "com.apple.metadata.mds.index": {
    "description": "The Spotlight indexing process.",
    "impact": "Spotlight will not be able to index your files."
  },
  "com.apple.metadata.mds.index.readonly": {
    "description": "A read-only version of the Spotlight indexer.",
    "impact": "May cause issues with Spotlight indexing."
  },
  "com.apple.metadata.mds.scan": {
    "description": "The Spotlight scanning process.",
    "impact": "Spotlight will not be able to scan your disks for changes to index."
  },
  "com.apple.metadata.mds.spindump": {
    "description": "A tool to get a spindump of the Spotlight server for diagnostics.",
    "impact": "You will not be able to get detailed diagnostics if Spotlight is hanging."
  },
  "com.apple.misagent": {
    "description": "The Mobile Installation Services agent. It installs and tracks provisioning profiles and mobile-style configuration profiles (for example developer or beta profiles).",
    "impact": "Provisioning and configuration profiles may fail to install or may not be tracked correctly."
  },
  "com.apple.mobile.storage_mounter": {
    "description": "A service for mounting storage, with a 'mobile' origin.",
    "impact": "May affect the mounting of certain types of storage, especially on Apple Silicon Macs."
  },
  "com.apple.mobile.storage_mounter_proxy": {
    "description": "A proxy for the storage mounter.",
    "impact": "Similar to `storage_mounter`, may cause issues with mounting volumes."
  },
  "com.apple.mobile.usermanagerd": {
    "description": "Manages user accounts, with a 'mobile' origin.",
    "impact": "May cause issues with user account creation and management."
  },
  "com.apple.mobileactivationd": {
    "description": "A daemon that handles the activation of the Mac with Apple's servers.",
    "impact": "The Mac may not be able to verify its activation status, potentially leading to service interruptions."
  },
  "com.apple.mobilegestalt.xpc": {
    "description": "A service that provides device information to applications, similar to the `MobileGestalt` framework on iOS.",
    "impact": "Applications may not be able to get detailed information about the device they are running on."
  },
  "com.apple.preferences.timezone.admintool": {
    "description": "An admin tool for setting the system timezone.",
    "impact": "You will not be able to change the system timezone if it requires administrator privileges."
  },
  "com.apple.recoveryos-lockout-service": {
    "description": "A service that handles lockouts in Recovery Mode.",
    "impact": "May impact security features related to Recovery Mode."
  },
  "com.apple.sessionlogoutd": {
    "description": "A daemon that manages the user logout process.",
    "impact": "You may have issues logging out of your user session."
  },
  "com.apple.startupdiskhelper": {
    "description": "A helper for setting the startup disk.",
    "impact": "You may have issues changing the startup disk in System Settings."
  },
  "com.apple.sysmond": {
    "description": "'System Monitor Daemon,' a legacy monitoring tool.",
    "impact": "Not critical for modern macOS."
  },
  "com.apple.systemadministration.writeconfig": {
    "description": "A tool for writing system administration configuration files.",
    "impact": "May prevent changes to some system settings."
  },
  "com.apple.systempreferences.cacheAssistant": {
    "description": "An assistant for caching data for System Preferences.",
    "impact": "System Preferences may load more slowly."
  },
  "com.apple.timezoneupdates.tzd": {
    "description": "The main daemon for timezone updates.",
    "impact": "The system will not automatically update its timezone database."
  },
  "com.apple.tmp_cleaner": {
    "description": "A tool that cleans the `/tmp` directory at startup.",
    "impact": "The temporary files directory will not be cleared, which could eventually consume disk space."
  },
  "com.apple.tzlinkd": {
    "description": "A daemon that manages the timezone link at `/etc/localtime`.",
    "impact": "The system's timezone may not be set correctly."
  },
  "com.apple.warmd": {
    "description": "A background daemon that manages the boot/warm cache on APFS and reports boot telemetry. It keeps frequently used system data warm to speed up startup.",
    "impact": "Startup may be slower and boot-related telemetry/diagnostics may be lost. It is not immediately harmful."
  },
  "com.apple.watchdogd": {
    "description": "A watchdog daemon that monitors core volumes and critical services and can panic or restart the system if a component stops responding.",
    "impact": "A hung system may not be restarted automatically, and you may have to power cycle it manually.",
  },
  "com.vix.cron": {
    "description": "The cron daemon, for scheduling tasks to run at specific times.",
    "impact": "User- and system-level cron jobs will not run."
  },
  # Text & Input
  "com.apple.naturallanguaged": {
    "description": "A daemon that provides natural language processing services to the OS, such as identifying parts of speech.",
    "impact": "Features that rely on understanding natural language text may be affected.",
  },
  "com.apple.languaged": {
    "description": "The language and region settings daemon, responsible for managing internationalization preferences.",
    "impact": "The system may not correctly apply your chosen language and regional format settings.",
  },
  "com.apple.applespell": {
    "description": "The system-wide spell checking service.",
    "impact": "Spell check will not function in any application.",
  },
  "com.apple.FontWorker": {
    "description": "A helper process for managing and validating fonts.",
    "impact": "Fonts may not install or display correctly.",
  },
  "com.apple.localizationswitcherd": {
    "description": "A service that may handle switching UI localization dynamically.",
    "impact": "Apps may not correctly switch languages without a restart.",
  },
  "com.apple.languageassetd": {
    "description": "Manages the download of language-related assets.",
    "impact": "The system may not be able to download new dictionaries or language packs.",
  },
  "com.apple.TextInputMenuAgent": {
    "description": "Manages the Input Method (keyboard) menu in the menu bar.",
    "impact": "You will not be able to switch between different keyboard layouts or input methods.",
  },
  "com.apple.keyboardservicesd": {
    "description": "A daemon for keyboard-related services, including text replacements and shortcuts.",
    "impact": "Text shortcuts and other keyboard services will not work.",
  },
  "com.apple.ATS.FontValidator": {
    "description": "A service for validating fonts.",
    "impact": "Corrupt or invalid fonts may cause instability.",
  },
  "com.apple.TextInputSwitcher": {
    "description": "A service for switching between different text input sources.",
    "impact": "The ability to switch keyboard layouts may be impaired.",
  },
  "com.apple.imklaunchagent": {
    "description": "Launches the Input Method Kit server.",
    "impact": "Complex input methods (e.g., for Chinese, Japanese, Korean) will not work.",
  },
  "com.apple.textunderstandingd": {
    "description": "The text-understanding daemon. It extracts meaning from text for data detection, suggestions, and other system features.",
    "impact": "Features that detect data like dates or addresses in text may fail.",
  },
  "com.apple.DataDetectorsSourceAccess": {
    "description": "Allows applications to access the data detectors framework, which recognizes dates, locations, and other data types in text.",
    "impact": "Data detection features in applications like Mail and Messages will not work."
  },
  "com.apple.fontmover": {
    "description": "A utility that moves font files between system and user font locations during activation.",
    "impact": "May cause issues with font management in older applications."
  },
  "com.apple.handwritingd": {
    "description": "The daemon for handwriting recognition, used with features like Scribble on an iPad.",
    "impact": "Handwriting recognition features will not work."
  },
  # User Interface & Windowing
  "com.apple.WindowServer": {
    "description": "The core process that manages and draws all windows, menus, icons, and other graphical elements on the screen.",
    "impact": "CRITICAL: Disabling this will kill the entire graphical user interface. The screen will go blank.",
  },
  "com.apple.Dock.agent": {
    "description": "The agent that runs and manages the Dock.",
    "impact": "The Dock will disappear and will not function.",
  },
  "com.apple.SystemUIServer.agent": {
    "description": "The agent that manages the right side of the menu bar (status items) and Notification Center.",
    "impact": "The menu bar status icons (Wi-Fi, Battery, etc.) and Notification Center will disappear.",
  },
  "com.apple.quicklook.ThumbnailsAgent": {
    "description": "Responsible for generating file icon thumbnails displayed in Finder.",
    "impact": "Finder will show generic icons for files instead of image or document previews.",
  },
  "com.apple.quicklook": {
    "description": "The main service for Quick Look, which generates previews of files when you press the spacebar in Finder.",
    "impact": "Quick Look functionality will be disabled.",
  },
  "com.apple.donotdisturbd": {
    "description": "Manages the Do Not Disturb mode and Focus modes.",
    "impact": "Focus and Do Not Disturb modes will not work, so notifications will not be silenced by Focus.",
  },
  "com.apple.chronod": {
    "description": "The background agent for widgets, including those on the desktop and in Notification Center.",
    "impact": "All widgets will stop working or updating.",
  },
  "com.apple.AirPlayXPCHelper": {
    "description": "A helper process for AirPlay, handling the discovery of and connection to AirPlay devices.",
    "impact": "CRITICAL: You will not be able to stream video or audio to an Apple TV or other AirPlay receivers. Disabling this is known to cause media playback errors in web browsers.",
  },
  "com.apple.mediaremoted": {
    "description": "Manages remote control of media playback, including the Now Playing widget and media keys.",
    "impact": "Media control keys (play/pause, next/previous) may not work, and the Now Playing widget will be non-functional.",
  },
  "com.apple.MENotificationService": {
    "description": "The notification service for the MediaExtension framework. It shows prompts and notifications for media extensions such as third-party camera, microphone, and system extensions.",
    "impact": "Notifications and prompts for media extensions may not appear.",
  },
  "com.apple.Finder": {
    "description": "The core application that manages the user's files, folders, and desktop.",
    "impact": "CRITICAL: The desktop, file windows, and overall graphical file management will be disabled.",
  },
  "com.apple.mediaremoteagent": {
    "description": "Agent for remotely controlling media playback.",
    "impact": "Media control keys and the Now Playing widget may not work reliably.",
  },
  "com.apple.iconservices.iconservicesagent": {
    "description": "User agent for managing file and app icons.",
    "impact": "Icons may not display correctly throughout the system.",
  },
  "com.apple.wallpaper.agent": {
    "description": "Agent for managing the desktop wallpaper.",
    "impact": "The desktop wallpaper will not be displayed or be user-configurable.",
  },
  "com.apple.UserPictureSyncAgent": {
    "description": "Syncs the user's account picture (e.g., via iCloud).",
    "impact": "Your user account picture will not sync across devices.",
  },
  "com.apple.WindowManager.agent": {
    "description": "The WindowManager agent. It provides Stage Manager, window tiling, and related window-management features.",
    "impact": "Window management features, including Mission Control and window placement, may be buggy.",
  },
  "com.apple.noticeboard.agent": {
    "description": "An agent for the 'Noticeboard' service, which may be related to notifications or widgets.",
    "impact": "Certain notifications or informational widgets may not function.",
  },
  "com.apple.UserNotificationCenterAgent": {
    "description": "Agent for the User Notification Center.",
    "impact": "The Notification Center may not function correctly.",
  },
  "com.apple.controlcenter": {
    "description": "The process that runs and manages Control Center.",
    "impact": "Control Center will be disabled.",
  },
  "com.apple.talagent": {
    "description": "Transparent Application Lifecycle agent, helps with restoring app windows after a restart.",
    "impact": "Apps may not restore their open windows when you log back in.",
  },
  "com.apple.carboncore.csnameddata": {
    "description": "A legacy Carbon Core service for managing named data.",
    "impact": "Older Carbon-based applications may fail to work correctly.",
  },
  "com.apple.controlstrip": {
    "description": "The process that manages the Control Strip on the Touch Bar.",
    "impact": "The Control Strip on the Touch Bar will be disabled.",
  },
  "com.apple.pbs": {
    "description": "Pasteboard server, another name for the service managing the clipboard.",
    "impact": "CRITICAL: Copy and paste functionality will be completely broken.",
  },
  "com.apple.AirPlayUIAgent": {
    "description": "Provides the user interface for AirPlay, such as the device picker.",
    "impact": "You will not be able to see the UI for selecting AirPlay devices.",
  },
  "com.apple.notificationcenterui.agent": {
    "description": "The user interface agent for Notification Center.",
    "impact": "The Notification Center UI will be broken.",
  },
  "com.apple.DesktopServicesHelper": {
    "description": "A helper process for Finder and desktop-related services.",
    "impact": "May cause issues with Finder functionality, such as file operations and desktop management."
  },
  "com.apple.UserNotificationCenter": {
    "description": "The main daemon for the User Notification Center.",
    "impact": "The Notification Center will be non-functional, and no notifications will be displayed."
  },
  "com.apple.iconservices.iconservicesd": {
    "description": "The main daemon for managing file and application icons.",
    "impact": "Icons may not display correctly throughout the system."
  },
  "com.apple.mobile.notification_proxy": {
    "description": "A compatibility proxy that delivers iOS-style notifications to apps and services running on macOS.",
    "impact": "Some notifications may not be delivered correctly."
  },
  "com.apple.noticeboard.state": {
    "description": "Manages the state for the 'Noticeboard' service.",
    "impact": "May cause issues with notifications or widgets."
  },
  "com.apple.wallpaper.export": {
    "description": "A tool for exporting wallpaper data.",
    "impact": "May affect wallpaper-related features."
  },
  # Weather
  "com.apple.weatherd": {
    "description": "The background daemon for the Weather framework and app.",
    "impact": "The Weather app and widgets will not update.",
  },
  "com.apple.weather.menu": {
    "description": "Manages the Weather menu bar item.",
    "impact": "The Weather widget in the menu bar will not function.",
  },
  # Undocumented
  "com.apple.IFCStart": {
    "description": "A legacy Carbon/CoreServices startup helper (label com.apple.IFCStart). Its exact purpose is undocumented and it has no user-facing configuration; it is likely an old compatibility shim kept for legacy boot tasks.",
    "impact": "Unknown. It is not known to affect normal usage.",
  },
  "com.apple.corercd": {
    "description": "The CoreRC daemon. It implements HDMI-CEC and remote-control support so the Mac can control, or be controlled by, TVs and AV receivers.",
    "impact": "HDMI-CEC and some remote-control features for connected displays and TVs will not work.",
  },
  "com.apple.filesystems.doubleagentd": {
    "description": "The DoubleAgent file-system daemon. It handles kernel upcalls for extended-attribute (xattr) operations on behalf of user-space processes.",
    "impact": "The impact of this service's absence is unknown due to a lack of public information."
  },
  "com.apple.griddatad": {
    "description": "The Grid Data daemon. It downloads and maintains the geographic grid/boundary data used by CoreLocation for reverse geocoding and region determination.",
    "impact": "Reverse geocoding and region/boundary lookups may fail or use stale data."
  },
  "com.apple.internal.aupbregistrarservice": {
    "description": "An internal Audio Unit registrar service. It scans and registers Audio Unit plug-ins for the system.",
    "impact": "May cause issues with the registration or functioning of audio unit plugins, particularly non-standard ones."
  },
  "com.apple.lskdd": {
    "description": "The CoreLSKD daemon. It provides a local security/key-data service over XPC (com.apple.lskdd) to system components.",
    "impact": "The impact of this service's absence is unknown but could potentially relate to local security policies or key distribution."
  },
  "com.apple.multiversed": {
    "description": "The Multiverse support daemon. It loads plug-ins that service Apple coprocessor I/O buffer copy engines (matched through IOKit) for low-level data paths.",
    "impact": "Coprocessor data-path plug-ins will not load, which may affect hardware-specific features on some Macs.",
  },
  "com.apple.pfd": {
    "description": "The Packet Filter daemon. It provides a user-space XPC interface (com.apple.pf) used to manage pf firewall rules and state.",
    "impact": "Tools and features that configure the pf packet filter may fail. The kernel firewall itself continues to run."
  },
  "com.apple.powerd.swd": {
    "description": "The powerd software watchdog. It monitors sleep/wake transitions and captures stackshots and logs when a sleep/wake failure occurs.",
    "impact": "May impact specific software-related power management features. The exact impact is unknown."
  },
  "com.apple.relatived": {
    "description": "The daemon behind Spatial Audio head tracking. It processes motion data from AirPods/Beats and other accessories to update the relative listener pose used by Spatial Audio.",
    "impact": "Spatial Audio with dynamic head tracking will no longer follow your head movements."
  },
  "com.apple.systemstatusd": {
    "description": "The SystemStatus server. It publishes system status domains such as recording, screen capture, and telephony status to clients.",
    "impact": "The impact is unclear, but its absence could affect how the system or certain applications respond to changes in system state."
  },
  "com.apple.tracd": {
    "description": "The Trusted Accessory daemon. It authenticates and monitors trusted accessories (for example Apple-branded USB-C and MFi devices), including reading accessory firmware version information.",
    "impact": "Some trusted/authenticated accessories may be rejected or stop reporting firmware and status information."
  },
  "com.apple.ucupdate.plist": {
    "description": "The CPU microcode update service. It applies Intel CPU microcode updates at boot to fix errata and security issues on Intel-based Macs.",
    "impact": "Microcode fixes and security mitigations will not be applied on Intel Macs. It has no effect on Apple Silicon."
  },
  "com.apple.xartstorageremoted": {
    "description": "Bridges access to xART (Secure Enclave-backed secure storage used for anti-replay and device secrets) between the startup volume and the SEP/BridgeOS, for example to read xART user data from the main volume.",
    "impact": "Secure-enclave-backed storage operations used by some Apple Pay, FileVault, and bridgeOS functions may fail."
  },
  "com.apple.xpc.uscwoap": {
    "description": "An Apple-internal boot shell job that runs /bin/bash with a null bootstrap. It exists for low-level debugging and diagnostic access at boot and is not a user-facing service.",
    "impact": "Apple's boot-time diagnostic shell will be unavailable. Normal usage is unaffected, so leave it alone unless you know you need it."
  },
  "com.apple.mobile.NRDUpdated": {
    "description": "The NRD update daemon for MobileSoftwareUpdate. It downloads and applies the update 'brain' used to prepare and validate software updates.",
    "impact": "May affect the system's ability to discover network resources."
  },
  "com.apple.MessageUIMacHelperService": {
    "description": "A helper service for the Mail app's user interface.",
    "impact": "Certain UI elements or features within the Mail app may break.",
  },
  "com.apple.SpeechRecognitionCore.brokerd": {
    "description": "A broker daemon for the Speech Recognition Core framework.",
    "impact": "Core speech recognition functionalities used by Siri, Dictation, and other apps will fail.",
  },
  "com.apple.hiservices-xpcservice": {
    "description": "An XPC service for HIToolbox, a legacy Carbon framework for user interface elements.",
    "impact": "Older applications that rely on Carbon for their UI may not function correctly.",
  },
  "com.apple.iokit.IOServiceAuthorizeAgent": {
    "description": "An agent that handles authorization requests for I/O Kit services, allowing user-space applications to access hardware.",
    "impact": "Applications may be unable to get the necessary permissions to interact with certain hardware.",
  },
  "com.apple.installandsetup.migrationhelper.user": {
    "description": "A user-level helper for the Migration Assistant.",
    "impact": "The Migration Assistant may fail to transfer user-specific data and settings correctly.",
  },
  "com.apple.mdworker.mail": {
    "description": "A Spotlight metadata importer specifically for indexing email content for Mail searches.",
    "impact": "The content of your emails will not be searchable via Spotlight.",
  },
  "com.apple.mdworker.shared": {
    "description": "A shared Spotlight metadata importer used by various applications.",
    "impact": "Spotlight indexing for multiple file types may be incomplete, leading to poor search results.",
  },
  "com.apple.mdworker.single": {
    "description": "A generic Spotlight metadata importer that runs as a single-use process for specific file types.",
    "impact": "Spotlight indexing will be impaired, affecting search capabilities.",
  },
  "com.apple.metadata.mdbulkimport": {
    "description": "A Spotlight service for importing large amounts of metadata in bulk.",
    "impact": "Initial Spotlight indexing and re-indexing of large volumes may be slow or fail.",
  },
  "com.apple.netauth.user.auth": {
    "description": "A user-level authentication service for network accounts.",
    "impact": "Logging in with network-based user accounts will likely fail.",
  },
  "com.apple.pluginkit.pkd": {
    "description": "The 'pkd' (PluginKit Daemon) is responsible for managing app extensions and plugins.",
    "impact": "App extensions (like Share menu items, Notification Center widgets, Finder extensions) will not work.",
  },
  "com.apple.speech.speechsynthesisd": {
    "description": "The primary daemon for speech synthesis (text-to-speech).",
    "impact": "All text-to-speech functionality, including VoiceOver and 'Speak Selection', will be broken.",
  },
  "com.apple.usermanagerhelper": {
    "description": "A helper tool for managing user accounts.",
    "impact": "May cause issues with creating, deleting, or modifying user accounts in System Settings.",
  },
  "com.apple.ViewBridgeAuxiliary": {
    "description": "An auxiliary service for ViewBridge, which securely embeds views from one process into another (e.g., app extensions).",
    "impact": "UI elements from app extensions or helper apps may not display correctly.",
  },
  "com.apple.WorkflowKit.ShortcutsViewService": {
    "description": "A service for displaying and managing views related to the Shortcuts app.",
    "impact": "The Shortcuts app and its integration with the system may be broken.",
  },
  "com.apple.duetexpertd": {
    "description": "The 'Duet Expert' daemon is part of the Duet Activity Scheduler, providing intelligence for proactive features.",
    "impact": "Proactive suggestions, like predicting your next app launch, may not work. Could affect battery life.",
  },
  "com.apple.familynotificationd": {
    "description": "Handles the delivery of notifications related to Family Sharing.",
    "impact": "You will not receive notifications for Family Sharing events like purchase requests.",
  },
  "com.apple.generativeexperiencesd": {
    "description": "The Generative Experiences daemon. It supports Apple Intelligence generative features such as Writing Tools and Image Playground.",
    "impact": "Emerging generative AI features within macOS will not be available.",
  },
  "com.apple.helpd": {
    "description": "The daemon that powers the macOS Help Viewer.",
    "impact": "You will not be able to access the built-in help manuals for macOS or its applications.",
  },
  "com.apple.icloud.fmfd": {
    "description": "The 'Find My Friends' daemon, a legacy service for the Find My network.",
    "impact": "Location sharing with friends and family via Find My may not function.",
  },
  "com.apple.icloud.searchpartyuseragent": {
    "description": "A user agent for the 'Search Party' (Find My network), helping to locate offline devices.",
    "impact": "The ability to find your Mac when it's offline will be disabled.",
  },
  "com.apple.icloudmailagent": {
    "description": "An agent responsible for syncing Mail.app with iCloud.",
    "impact": "iCloud email will not sync.",
  },
  "com.apple.imautomatichistorydeletionagent": {
    "description": "An agent that automatically deletes old iMessage history based on user settings.",
    "impact": "Your iMessage history may not be automatically pruned, potentially using more disk space.",
  },
  "com.apple.inputanalyticsd": {
    "description": "A daemon that collects analytics about your use of keyboards and input methods.",
    "impact": "No input device usage data will be sent to Apple. May be desirable for privacy.",
  },
  "com.apple.intelligencecontextd": {
    "description": "A daemon that provides context to the on-device intelligence platform.",
    "impact": "Many intelligent and proactive features will be less effective.",
  },
  "com.apple.intelligenceflowd": {
    "description": "A daemon that manages the flow of data for the on-device intelligence platform.",
    "impact": "Intelligent features may fail to process information correctly.",
  },
  "com.apple.knowledgeconstructiond": {
    "description": "Constructs and maintains the on-device knowledge graph used by Siri and Spotlight.",
    "impact": "Siri and Spotlight will have a reduced understanding of your personal data and context.",
  },
  "com.apple.navd": {
    "description": "Navigation Daemon. Provides routing and navigation services, primarily for Apple Maps.",
    "impact": "Turn-by-turn directions and route planning in Maps will fail.",
  },
  "com.apple.progressd": {
    "description": "A system-wide daemon for tracking and displaying progress for tasks like file copies or downloads.",
    "impact": "Progress indicators in Finder and other apps may not appear or may be inaccurate.",
  },
  "com.apple.replicatord": {
    "description": "The ReplicatorCore daemon. It replicates state between processes and devices for continuity and data-consistency features.",
    "impact": "The exact impact is unclear, but it could affect data syncing reliability.",
  },
  "com.apple.security.cloudkeychainproxy3": {
    "description": "A proxy service for iCloud Keychain, facilitating communication for keychain syncing.",
    "impact": "iCloud Keychain syncing may become unreliable or fail completely.",
  },
  "com.apple.sidecar-hid-relay": {
    "description": "A relay service for Human Interface Devices (keyboard, mouse, trackpad) used with Sidecar.",
    "impact": "You will not be able to use your Mac's keyboard and mouse to interact with the iPad in a Sidecar session.",
  },
  "com.apple.siriactionsd": {
    "description": "The daemon that manages and executes Siri Actions and Shortcuts.",
    "impact": "The Shortcuts app and any Siri-integrated shortcuts will not function.",
  },
  "com.apple.SiriTTSTrainingAgent": {
    "description": "An agent that may be used for training or optimizing Siri's Text-to-Speech (TTS) capabilities.",
    "impact": "No immediate user-facing impact, but may prevent improvements to Siri's voice.",
  },
  "com.apple.tipsd": {
    "description": "The daemon for the Tips app, which provides suggestions on how to use macOS.",
    "impact": "The Tips app and its related notifications will not work.",
  },
  "com.apple.UsageTrackingAgent": {
    "description": "An agent that tracks application and system usage for Screen Time.",
    "impact": "Screen Time data will be inaccurate or not collected at all.",
  },
  "com.apple.videosubscriptionsd": {
    "description": "A daemon for managing video channel subscriptions within the TV app.",
    "impact": "Subscriptions to Apple TV Channels may not work correctly.",
  },
  "com.apple.assistant_service": {
    "description": "A core service for Siri (Assistant).",
    "impact": "Siri will be completely non-functional.",
  },
  "com.apple.ContextStoreAgent": {
    "description": "An agent that manages the storage of contextual data for proactive features.",
    "impact": "Proactive suggestions and other intelligent features will be less effective.",
  },
  "com.apple.maps.destinationd": {
    "description": "The Maps destination daemon. It learns frequent routes and provides destination suggestions to Maps and other apps.",
    "impact": "Maps may not be able to provide suggestions for destinations.",
  },
  "com.apple.geoanalyticsd": {
    "description": "A daemon that collects and processes analytics related to geolocation and Maps usage.",
    "impact": "No location-based analytics will be sent to Apple.",
  },
  "com.apple.sirittsd": {
    "description": "Siri Text-to-Speech daemon. Responsible for generating Siri's voice.",
    "impact": "Siri will be unable to speak.",
  },
  "com.apple.cvmsCompAgent": {
    "description": "A compute agent for the Core Video and Metal frameworks, managing GPU tasks.",
    "impact": "Graphics-intensive applications and games may fail or perform poorly.",
  },
  "com.apple.metadata.mdflagwriter": {
    "description": "A Spotlight helper that writes flags to metadata.",
    "impact": "Spotlight indexing may not function correctly.",
  },
  "com.apple.screencaptureui": {
    "description": "Handles the user interface for taking screenshots and screen recordings.",
    "impact": "The built-in screenshot and screen recording tools (Cmd+Shift+5) will not work.",
  },
  "com.apple.CoreRoutine.helperservice": {
    "description": "A helper service for the 'routined' daemon, which learns your frequently visited locations to provide proactive suggestions.",
    "impact": "Disabling this may impair the functionality of location-based suggestions and the Significant Locations feature.",
  },
  "com.apple.DistributionKit.DistributionHelper": {
    "description": "A helper tool for the DistributionKit framework, which is used by the macOS Installer for package distribution.",
    "impact": "Installation of some software, particularly from `.pkg` files, may fail.",
  },
  "com.apple.DictionaryServiceHelper": {
    "description": "A helper service for the built-in Dictionary application.",
    "impact": "The Dictionary app and the 'Look Up' feature may not function correctly.",
  },
  # --- Third-Party Services Added Below ---
  "com.google.keystone.user.agent": {
    "description": "Google Keystone Agent. Part of Google Updater, it keeps Google applications (like Chrome) up-to-date.",
    "impact": "Disabling will prevent automatic updates for Google software, which is a potential security risk.",
  },
  "com.google.keystone.user.xpcservice": {
    "description": "Google Keystone XPC Service. Works with the main agent to handle update tasks.",
    "impact": "Disabling will prevent automatic updates for Google software.",
  },
  "com.docker.helper": {
    "description": "Docker Desktop Helper. A privileged helper tool that manages networking, filesystems, and other system-level resources for Docker Desktop.",
    "impact": "CRITICAL: Docker Desktop will not be able to function without this helper.",
  },
  "com.adobe.GC.AGM": {
    "description": "Adobe Genuine Service (AGM). Periodically validates your Adobe software licenses.",
    "impact": "Adobe applications may complain about being non-genuine or may fail to launch.",
  },
  "com.adobe.GC.Scheduler-1.0": {
    "description": "Adobe Genuine Copy Scheduler. Schedules tasks for the Adobe Genuine Service.",
    "impact": "Adobe applications may complain about being non-genuine or may fail to launch.",
  },
  "com.microsoft.update.agent": {
    "description": "Microsoft AutoUpdate Agent. Manages and applies updates for Microsoft Office applications.",
    "impact": "Microsoft Office apps will not receive automatic updates, which is a potential security risk.",
  },
  "com.microsoft.autoupdate.helper": {
    "description": "Microsoft AutoUpdate Helper. A privileged helper for installing updates for Microsoft products.",
    "impact": "Microsoft Office apps will not be able to install updates.",
  },
  "2BUA8C4S2C.com.agilebits.onepassword7-helper": {
    "description": "A helper agent for 1Password 7.",
    "impact": "1Password 7 browser integration and other features may not work correctly.",
  },
  "com.1password.1password-launcher": {
    "description": "The main launcher for the 1Password 8+ application helper.",
    "impact": "1Password browser integration and other features may not work correctly.",
  },
  # --- Accessibility ---
  "com.apple.AccessibilityVisualsAgent": {
    "description": "Apple's accessibility visuals agent. It draws accessibility-related visual overlays such as the pointer outline and other on-screen aids.",
    "impact": "Visual accessibility aids may not appear.",
  },
  "com.apple.scrod": {
    "description": "The Screen Reader Output daemon, the output layer for VoiceOver. It manages braille displays and other screen-reader output devices.",
    "impact": "VoiceOver braille and other screen-reader output devices will not work.",
  },
  # --- Advertising & Analytics ---
  "com.apple.ecosystemagent": {
    "description": "A user agent from the Ecosystem framework that supports analytics and feature coordination across Apple devices.",
    "impact": "Some cross-device ecosystem features or analytics may be less reliable.",
  },
  # --- App & Store Related ---
  "com.apple.appstorecomponentsd": {
    "description": "A daemon that renders App Store components (product pages, charts, and recommendations) for apps and the App Store UI.",
    "impact": "Embedded App Store content and some App Store screens may fail to load.",
  },
  "com.apple.storeassetd": {
    "description": "A CommerceKit daemon that downloads and manages App Store assets such as product metadata and artwork.",
    "impact": "App Store product pages, screenshots, and metadata may not load correctly.",
  },
  "com.apple.storelegacy": {
    "description": "A legacy CommerceKit store daemon that supports older App Store purchase and download flows.",
    "impact": "Legacy App Store purchase/download flows may fail. Mostly relevant for older content.",
  },
  "com.apple.triald": {
    "description": 'Supports Apple’s Trial framework. Its launch configuration schedules experiment fetching and maintenance.',
    "impact": 'Disabling may prevent Trial experiment configuration and maintenance. Effects depend on the features using this framework.',
  },
  "com.apple.backgroundassets.user": {
    "description": "The user-level Background Assets agent. It downloads large app assets in the background on behalf of apps and games.",
    "impact": "Apps that use Background Assets may not download their content, leaving them incomplete.",
  },
  "com.apple.ndoagent": {
    "description": "The New Device Outreach agent. It handles Apple's promotional outreach about new devices and upgrade offers.",
    "impact": "You may not see new-device or upgrade offers. Safe to disable if you do not want them.",
  },
  # --- Backup & Time Machine ---
  "com.apple.mbproximityhelper": {
    "description": "A Setup Assistant helper used when migrating data from a nearby Mac or device over a direct connection.",
    "impact": "Nearby-device migration during Setup Assistant may fail.",
  },
  # --- Calendar & Reminders ---
  "com.apple.calendar.CalendarAgentBookmarkMigrationService": {
    "description": "A one-time migration service that converts legacy Calendar agent bookmarks into the modern format.",
    "impact": "Calendar account bookmarks may not migrate correctly after an upgrade.",
  },
  # --- Device Communication ---
  "com.apple.AMPDeviceDiscoveryAgent": {
    "description": "An Apple Media Products agent that discovers connected iPhone, iPad, and iPod devices for Finder/Music device sync.",
    "impact": "Connected iOS devices may not be discovered for syncing.",
  },
  "com.apple.AMPDevicesAgent": {
    "description": "The Apple Media Products device agent. It manages the connection and content sync sessions with iOS devices.",
    "impact": "Syncing media or data with a connected iPhone/iPad may fail.",
  },
  "com.apple.AMPSystemPlayerAgent": {
    "description": "An agent from the iTunesLibrary framework that handles playback and transfer of media to connected iOS devices.",
    "impact": "Media transfer to connected iOS devices may fail.",
  },
  "com.apple.bluetoothaudiod": {
    "description": "The Bluetooth audio daemon. It manages audio routing and codec handling for Bluetooth headphones and speakers.",
    "impact": "Bluetooth audio output may fail or fall back to lower-quality codecs.",
  },
  "com.apple.btsa": {
    "description": "The Bluetooth Setup Assistant. It walks users through pairing new Bluetooth devices.",
    "impact": "The Bluetooth setup assistant may not launch when pairing new devices.",
  },
  "com.apple.cloudpaird": {
    "description": "A cloud pairing daemon for audio accessories. It helps AirPods/Beats pair across devices and support Find My.",
    "impact": "Audio accessories may not pair automatically across your devices or appear in Find My.",
  },
  "com.apple.facetimemessagestored": {
    "description": "The FaceTime message store daemon. It stores and syncs FaceTime call/message data.",
    "impact": "FaceTime call history or related data may not be stored correctly.",
  },
  "com.apple.mediacontinuityd": {
    "description": "The media continuity daemon. It supports handing off media playback between devices and related Continuity media features.",
    "impact": "Handoff of media playback between devices may not work.",
  },
  "com.apple.rapportd-user": {
    "description": "The per-user Rapport (Continuity) daemon. It maintains nearby-device communication for Handoff, AirDrop, and Universal Clipboard.",
    "impact": "Continuity features such as Handoff and Universal Clipboard may fail.",
  },
  "com.apple.ensemble": {
    "description": "The Universal Control agent (code-named Ensemble). It links the keyboard, mouse, and trackpad across nearby Macs and iPads.",
    "impact": "Universal Control between devices will not work.",
  },
  "com.apple.idsremoteurlconnectionagent": {
    "description": "An IDS (Identity Services) agent that performs remote URL connections on behalf of iMessage/FaceTime identity services.",
    "impact": "Some iMessage/FaceTime network operations may fail.",
  },
  "com.apple.idsfoundation.IDSRemoteURLConnectionAgent": {
    "description": "The IDS remote URL connection agent. It performs network requests on behalf of iMessage/FaceTime identity services.",
    "impact": "Some iMessage/FaceTime network requests may fail.",
  },
  "com.apple.imdpersistence.IMDPersistenceAgent": {
    "description": "The Messages persistence agent. It writes iMessage and SMS data to the message database.",
    "impact": "Messages may not be saved or may disappear after restarts.",
  },
  "com.apple.mobiledeviceupdater": {
    "description": "Updates firmware and software on connected iOS devices (iPhone, iPad, iPod).",
    "impact": "You may not be able to update connected iOS devices from this Mac.",
  },
  "com.apple.ThreadCommissionerService": {
    "description": "The Thread Commissioner service. It manages Thread network credentials and joins Thread devices for HomeKit.",
    "impact": "Thread-based smart home accessories may not join or stay connected.",
  },
  # --- Diagnostics & Logging ---
  "com.apple.DiagnosticsReporter": {
    "description": "The Diagnostics Reporter app. It collects and displays diagnostics for Apple support and can upload reports.",
    "impact": "Apple support diagnostics may not be collected or shown.",
  },
  "com.apple.DumpPanicRecoveryOS": {
    "description": "Saves kernel panic information when the Mac is running in RecoveryOS.",
    "impact": "Panic logs from RecoveryOS will not be saved, making boot failures harder to diagnose.",
  },
  "com.apple.ReportGPURestart": {
    "description": "A diagnostic helper that logs information when the GPU restarts unexpectedly.",
    "impact": "GPU restart diagnostics will not be collected.",
  },
  "com.apple.diagnosticspushd": {
    "description": "A daemon that uploads diagnostic reports to Apple when diagnostics sharing is enabled.",
    "impact": "Diagnostics will not be uploaded to Apple. May be desirable for privacy.",
  },
  "com.apple.sysdiagnose.darwinos": {
    "description": "A sysdiagnose variant used for DarwinOS components. It gathers low-level system diagnostics.",
    "impact": "DarwinOS-level diagnostics may not be captured when running sysdiagnose.",
  },
  "com.apple.thermaltrap": {
    "description": "A diagnostic app that captures thermal and power state information when triggered.",
    "impact": "Thermal diagnostic captures may not be available.",
  },
  "com.apple.appleseed.seedusaged.postinstall": {
    "description": "A post-install helper for the AppleSeed beta program that reports beta usage statistics.",
    "impact": "Beta usage data will not be reported after installing a seed build.",
  },
  "com.apple.kdumpd": {
    "description": "The kernel dump daemon. It saves kernel memory dumps for debugging after a panic.",
    "impact": "Kernel core dumps will not be saved.",
  },
  # --- iCloud & CloudKit ---
  "com.apple.FeatureAccessAgent": {
    "description": "An agent from CloudSubscriptionFeatures. It checks and caches feature eligibility (for example iCloud+ and subscription features).",
    "impact": "Some subscription or feature eligibility checks may fail or be slow.",
  },
  "com.apple.iCloudNotificationAgent": {
    "description": "The iCloud notification agent. It delivers iCloud-related notifications to the user.",
    "impact": "You may miss iCloud notifications.",
  },
  "com.apple.icloudwebd": {
    "description": "The iCloud web daemon. It supports iCloud data access from the web and related account features.",
    "impact": "Some iCloud web/account features may not work.",
  },
  "com.apple.findmy.findmylocateagent": {
    "description": "The Find My locate agent. It handles location requests for Find My and shares location with permitted devices.",
    "impact": "Find My location reporting may fail.",
  },
  "com.apple.appleidsetupd": {
    "description": "The Apple ID setup daemon. It assists with the first-run Apple ID sign-in and account setup flow.",
    "impact": "Setting up or signing in with an Apple ID during setup may fail.",
  },
  # --- Family & ScreenTime ---
  "com.apple.asktod": {
    "description": "The Ask To daemon. It processes Ask to Buy purchase requests and approvals for Family Sharing.",
    "impact": "Ask to Buy requests and approvals may not work.",
  },
  "com.apple.ScreenTimeSettingsAgent": {
    "description": "The Settings agent for Screen Time. It applies Screen Time configuration changes made in System Settings.",
    "impact": "Screen Time settings may not apply correctly.",
  },
  "com.apple.macos.studentd": {
    "description": "The macOS student daemon for managed education environments. It supports classroom and Schoolwork features.",
    "impact": "Managed education features may not work on this Mac.",
  },
  "com.apple.assessmentagent": {
    "description": "An agent used in managed education contexts to run assessments and apply assessment restrictions.",
    "impact": "Managed assessment features may not work.",
  },
  # --- Filesystem & Storage ---
  "com.apple.diskspaced": {
    "description": "The disk space daemon. It monitors free space and triggers storage-cleanup actions when the disk fills up.",
    "impact": "The system may not free space automatically, so the disk can fill up.",
  },
  "com.apple.StorageManagement.Service": {
    "description": "The Storage Management service. It powers System Settings storage recommendations and purgeable-space calculations.",
    "impact": "Storage recommendations and purgeable-space reporting may not work.",
  },
  "com.apple.StorageManagementUIHelper": {
    "description": "The UI helper for Storage Management. It displays storage dialogs and progress for cleanup tasks.",
    "impact": "Storage Management dialogs may not appear.",
  },
  "com.apple.storagede.helper": {
    "description": "A helper for the Storage Data Engine that gathers volume and storage information for the system.",
    "impact": "Storage details and diagnostics may be incomplete.",
  },
  "com.apple.xsan": {
    "description": "The Xsan daemon. It manages Xsan storage-area-network volumes and metadata controllers.",
    "impact": "Xsan volumes will not mount or work.",
  },
  "com.apple.xscertadmin": {
    "description": "The Xsan certificate administration tool. It manages certificates used to secure Xsan metadata traffic.",
    "impact": "You will not be able to administer Xsan certificates.",
  },
  "com.apple.xscertd": {
    "description": "The Xsan certificate daemon. It distributes and validates certificates for Xsan clients and controllers.",
    "impact": "Xsan authentication may fail.",
  },
  "com.apple.xscertd-helper": {
    "description": "A helper for the Xsan certificate daemon.",
    "impact": "Xsan certificate operations may fail.",
  },
  "com.apple.NVMeAgent": {
    "description": "An agent that collects NVMe SSD health and telemetry information.",
    "impact": "NVMe health/diagnostic information may not be collected.",
  },
  # --- Game Center ---
  "com.apple.GameOverlayUI": {
    "description": "The in-game overlay UI for Game Center, showing achievements, leaderboards, and game status.",
    "impact": "The Game Center overlay will not appear in games.",
  },
  "com.apple.gamecontroller.ConfigService": {
    "description": "The Game Controller configuration service. It applies controller mappings, profiles, and settings.",
    "impact": "Custom controller mappings and profiles may not apply.",
  },
  # --- Hardware & Drivers ---
  "com.apple.accessorysensormgrd": {
    "description": "The accessory sensor manager. It reads sensor data from connected Apple accessories (for example motion or orientation data).",
    "impact": "Accessory sensor features such as motion input may not work.",
  },
  "com.apple.audio.AudioComponentRegistrar.daemon": {
    "description": "The system daemon for the Audio Component Registrar. It scans and registers Audio Unit plug-ins for all users.",
    "impact": "Third-party Audio Unit plug-ins may not be discovered.",
  },
  "com.apple.audio.micactivityd": {
    "description": "The system-level microphone activity daemon. It enforces microphone-in-use reporting and privacy indicators.",
    "impact": "Microphone activity reporting and the orange privacy indicator may fail.",
  },
  "com.apple.centaurid": {
    "description": "The Centauri firmware daemon. It manages firmware loading and sleep-state bookkeeping for Apple's Centauri wireless/companion chip.",
    "impact": "Wireless/companion hardware managed by Centauri may behave incorrectly.",
  },
  "com.apple.CSCSupportd": {
    "description": "The Common Smart Card support daemon. It provides smart card services (for example PIV/CAC authentication) to the system.",
    "impact": "Smart card authentication may fail.",
  },
  "com.apple.colorsync.useragent": {
    "description": "The per-user ColorSync agent. It applies display color profiles for the logged-in session.",
    "impact": "Display color profiles may not apply correctly in the user session.",
  },
  "com.apple.cmio.ContinuityCaptureAgent": {
    "description": "The Continuity Camera agent. It lets an iPhone be used as a webcam or scanner by the Mac.",
    "impact": "Continuity Camera will not work.",
  },
  "com.apple.cmio.registerassistantservice": {
    "description": "A CoreMediaIO service that registers CMIO assistant plug-ins for camera and capture devices.",
    "impact": "Some camera/capture assistants may not load.",
  },
  "com.apple.cmio.videodriverkithostextension": {
    "description": "The DriverKit host extension for video drivers. It loads user-space camera/video drivers.",
    "impact": "Third-party or Apple DriverKit video devices may not work.",
  },
  "com.apple.MTLAssetUpgraderD": {
    "description": "The Metal asset upgrader. It converts Metal shader and asset caches to the current format after OS or driver updates.",
    "impact": "Apps may stutter or fail on first launch while their Metal shaders are rebuilt.",
  },
  "com.apple.ExpansionSlotNotification": {
    "description": "A helper that reports changes in expansion slots (for example PCIe slots on Mac Pro).",
    "impact": "Expansion-slot change notifications may not appear.",
  },
  "com.apple.MemorySlotNotification": {
    "description": "A helper that reports changes in memory slots (for example on Mac Pro).",
    "impact": "Memory-slot change notifications may not appear.",
  },
  "com.apple.gputoolsserviced": {
    "description": "The GPU tools service. It supports Metal developer tools, GPU captures, and performance analysis.",
    "impact": "GPU debugging and Metal developer tools may not work.",
  },
  "com.apple.lightsoutmanagementd": {
    "description": "The Lights Out Management daemon. It supports remote power control and management on Mac Pro and server hardware.",
    "impact": "Remote power management features will not work.",
  },
  "com.apple.preference.displays.MirrorDisplays": {
    "description": "The Mirror Displays helper from the Displays preference pane. It applies display mirroring settings.",
    "impact": "Display mirroring controls may not work from the preferences pane.",
  },
  "com.apple.uarppersonalizationd": {
    "description": "The UARP personalization daemon. It fetches device-specific firmware personalization data for accessory updates.",
    "impact": "Accessory firmware updates may fail because the image cannot be personalized.",
  },
  "com.apple.videoconference.camera": {
    "description": "The AV conference daemon (avconferenced). It provides audio/video conferencing and camera capture services for FaceTime and other apps.",
    "impact": "Video-conferencing apps may not be able to access the camera.",
  },
  # --- Security & Keychain ---
  "com.apple.EscrowSecurityAlert": {
    "description": "The escrow security alert agent. It warns when the recovery key for FileVault/iCloud Keychain escrow is missing or invalid.",
    "impact": "You may not be warned about recovery-key escrow problems.",
  },
  "com.apple.prngseedd": {
    "description": "The PRNG seed daemon. It seeds the system random number generator from the Secure Enclave at boot.",
    "impact": "Early-boot entropy may be weaker, which can slow or weaken cryptographic operations.",
  },
  "com.apple.seserviced": {
    "description": "The Secure Element service daemon. It provides applets and secure-element services for NFC, Apple Pay, and similar features.",
    "impact": "Secure Element-backed features such as NFC and some Apple Pay operations may fail.",
  },
  "com.apple.security.xprotectd": {
    "description": "The XProtect daemon. It performs background malware scanning using Apple's XProtect signatures.",
    "impact": "Built-in malware scanning will be reduced or disabled.",
  },
  "com.apple.securityuploadd": {
    "description": "The security analytics uploader. It uploads security-related analytics and telemetry to Apple.",
    "impact": "Security telemetry will not be uploaded.",
  },
  "com.apple.security.DiskUnmountWatcher": {
    "description": "A Kerberos helper that watches for disk unmounts so it can clear credentials associated with removed volumes.",
    "impact": "Kerberos credentials on removable volumes may not be cleared promptly.",
  },
  "com.apple.security.FDERecoveryAgent": {
    "description": "The FileVault recovery agent. It handles recovery-key operations and FileVault unlock support.",
    "impact": "FileVault recovery key operations may fail.",
  },
  "com.apple.security.XPCKeychainSandboxCheck": {
    "description": "An XPC service that verifies keychain sandbox access for clients.",
    "impact": "Apps may fail keychain sandbox checks and lose keychain access.",
  },
  "com.apple.security.XPCTimeStampingService": {
    "description": "An XPC time-stamping service used when signing code and timestamping requests.",
    "impact": "Timestamped code signing operations may fail.",
  },
  "com.apple.LocalAuthentication.userauthd": {
    "description": "The user authentication daemon. It evaluates Touch ID and password prompts for LocalAuthentication clients.",
    "impact": "Touch ID and password prompts for apps may fail.",
  },
  "com.apple.CryptoTokenKit.ahp.agent": {
    "description": "The per-user CryptoTokenKit authentication helper. It connects smart cards and hardware tokens to the user session.",
    "impact": "Smart cards and hardware tokens may not work in apps.",
  },
  "com.apple.filevaultd": {
    "description": "The FileVault daemon. It coordinates FileVault encryption state and unlock operations.",
    "impact": "FileVault encryption or unlock operations may fail.",
  },
  "com.apple.securemessagingagent": {
    "description": "The Secure Messaging agent. It supports encrypted/secure messaging features.",
    "impact": "Secure messaging features may not work.",
  },
  "com.apple.transparencyd": {
    "description": "The Apple Account transparency daemon. It maintains verifiable transparency data for account security.",
    "impact": "Account transparency and verification features may fail.",
  },
  "com.apple.transparencyStaticKey": {
    "description": "The transparency static key service. It manages static keys used by Apple Account transparency.",
    "impact": "Account transparency verification may fail.",
  },
  "com.apple.swtransparencyd": {
    "description": "The software transparency daemon. It verifies transparency data for software and services.",
    "impact": "Software transparency checks may fail.",
  },
  "com.apple.appleaccounttransparencyd": {
    "description": "The Apple Account transparency daemon (per-user). It verifies account transparency records in the user session.",
    "impact": "Apple Account transparency features may not work in the user session.",
  },
  "com.apple.auditd": {
    "description": "The audit daemon. It writes kernel audit records for security auditing.",
    "impact": "Security audit logs will not be written.",
  },
  "com.apple.lockoutagent": {
    "description": "The lockout agent. It enforces login lockouts after repeated failed authentication attempts.",
    "impact": "Failed-login lockout enforcement may not work.",
  },
  "com.apple.locationaccessstored": {
    "description": "The location access store. It records which apps and services are authorized to access location data.",
    "impact": "Location permission state may not be stored correctly.",
  },
  "com.apple.scopedbookmarksagent.xpc": {
    "description": "The scoped bookmark agent. It resolves security-scoped bookmarks so sandboxed apps can reopen files.",
    "impact": "Sandboxed apps may lose access to previously bookmarked files.",
  },
  # --- HomeKit ---
  "com.apple.homeeventsd": {
    "description": "The HomeKit events daemon. It records and delivers HomeKit accessory events, triggers, and automations.",
    "impact": "HomeKit automations and event notifications may not fire.",
  },
  # --- Installation & Updates ---
  "com.apple.PackageUIKit.InstallStatus": {
    "description": "The 'Install in Progress' UI helper. It shows progress and status for package installations.",
    "impact": "Package install progress may not be shown.",
  },
  "com.apple.dt.CommandLineTools.installondemand": {
    "description": "The on-demand installer for Apple's Command Line Tools. It prompts for and installs the developer tools when needed.",
    "impact": "Tools that trigger an on-demand Command Line Tools install (git, clang, make) may not install.",
  },
  "com.apple.postupgraded": {
    "description": "A one-shot daemon that performs post-upgrade cleanup and migration tasks after a macOS update.",
    "impact": "Post-update cleanup tasks may not run, potentially leaving stale data.",
  },
  "com.apple.package-script-service": {
    "description": "A transient service that runs package installer scripts.",
    "impact": "Some package installers may fail to run their scripts.",
  },
  # --- Mgt & Development ---
  "com.apple.RemoteDesktop": {
    "description": "The Apple Remote Desktop agent. It allows this Mac to be controlled or observed remotely via ARD.",
    "impact": "Apple Remote Desktop control and observation will not work.",
  },
  "com.apple.RemoteDesktop.agent": {
    "description": "The per-user Apple Remote Desktop agent. It handles the user-session side of ARD sessions.",
    "impact": "Remote Desktop sessions in the user session may fail.",
  },
  "com.apple.RemoteManagementAgent": {
    "description": "The Remote Management agent. It applies management commands (MDM/ARD) in the user session.",
    "impact": "Remote management commands may not be applied.",
  },
  "com.apple.ssinvitationagent": {
    "description": "The screen-sharing invitation agent. It asks the user to accept or decline a Screen Sharing/Remote Management session.",
    "impact": "You may not be able to accept screen-sharing invitations.",
  },
  "com.apple.managedappdistributionagent": {
    "description": "The managed app distribution agent. It installs apps pushed by an MDM server.",
    "impact": "MDM-pushed apps will not install.",
  },
  "com.apple.dmd.agent": {
    "description": "The per-user Device Management daemon agent. It applies MDM commands and queries in the user session.",
    "impact": "Some MDM commands may not be applied in the user session.",
  },
  "com.apple.mdmclient.daemon.runatboot": {
    "description": "The MDM client run at boot. It connects to the MDM server early in startup to pick up pending commands.",
    "impact": "Early-boot MDM check-ins and commands will not happen.",
  },
  "com.apple.dt.AutomationModeUI": {
    "description": "The UI for Xcode's automation mode, which temporarily enables UI automation for testing.",
    "impact": "Xcode UI tests may not be able to enable automation mode.",
  },
  "com.apple.dt.previewsd": {
    "description": "The Xcode Previews daemon. It builds and serves SwiftUI previews.",
    "impact": "Xcode Previews may not work.",
  },
  "com.apple.dt.previewsviewservice": {
    "description": "The view service for Xcode Previews. It renders preview content in a separate process.",
    "impact": "SwiftUI previews may not render.",
  },
  "com.apple.previewshellapp": {
    "description": "PreviewShell, the host app used to render previews and UI snapshots for developer tools.",
    "impact": "Some preview/pre-rendering features may not work.",
  },
  "com.apple.swiftuitraced": {
    "description": "The SwiftUI tracing daemon. It collects trace data for debugging SwiftUI apps.",
    "impact": "SwiftUI debugging and tracing will not work.",
  },
  # --- Networking ---
  "com.apple.mDNSResponderHelper": {
    "description": "The helper for mDNSResponder. It performs privileged Bonjour/mDNS tasks that the main responder cannot do itself.",
    "impact": "Some Bonjour discovery and DNS Service Discovery features may fail.",
  },
  "com.apple.dhcp6d": {
    "description": "The DHCPv6 client daemon. It obtains IPv6 addresses and configuration from DHCPv6 servers.",
    "impact": "DHCPv6 address assignment may fail.",
  },
  "com.apple.sntpd": {
    "description": "The SNTP/NTP client daemon. It synchronizes the system clock with network time servers.",
    "impact": "The clock may drift, which can break authentication and time-sensitive operations.",
  },
  "com.apple.netauth.user.gui": {
    "description": "The GUI for network authentication. It shows login prompts for network accounts.",
    "impact": "The login UI for network accounts may not appear.",
  },
  "com.apple.msrpc.echosvc": {
    "description": "The MSRPC echo service. It provides an RPC endpoint used for Windows/SMB interoperability.",
    "impact": "Windows RPC interoperability features may not work.",
  },
  "com.apple.ftp-proxy": {
    "description": "The FTP proxy helper for the pf packet filter. It allows passive FTP through the firewall.",
    "impact": "Passive FTP may fail when the firewall is enabled.",
  },
  "com.apple.screensharing.agent": {
    "description": "The Screen Sharing agent. It runs the user-session side of VNC/Screen Sharing sessions.",
    "impact": "Screen Sharing into the user session may fail.",
  },
  "com.apple.screensharing.menuextra": {
    "description": "The Screen Sharing menu extra. It provides the menu item for sharing and controlling this Mac.",
    "impact": "The Screen Sharing menu extra may be missing.",
  },
  "com.apple.screensharing.MessagesAgent": {
    "description": "The AppleVNC helper used when screen sharing is initiated through Messages.",
    "impact": "Screen sharing via Messages may fail.",
  },
  "com.apple.cfnetwork.AuthBrokerAgent": {
    "description": "The CFNetwork authentication broker agent. It handles proxy and network challenge authentication for apps.",
    "impact": "Apps may fail to authenticate to proxies or networks.",
  },
  "com.apple.ftp": {
    "description": "The FTP server wrapper.",
    "impact": "FTP sharing will not work.",
  },
  "com.openssh.sshd": {
    "description": "The SSH server (sshd) launchd wrapper. It accepts incoming SSH connections when Remote Login is enabled.",
    "impact": "Remote Login (SSH) will not work.",
  },
  "com.openssh.ssh-agent": {
    "description": "The OpenSSH agent. It holds private keys for SSH authentication and answers signing requests.",
    "impact": "SSH keys added to the agent will not be available for passwordless login.",
  },
  "org.apache.httpd": {
    "description": "The Apache HTTP server. It serves websites when Web Sharing is configured.",
    "impact": "The built-in Apache web server will not start.",
  },
  "org.net-snmp.snmpd": {
    "description": "The Net-SNMP daemon. It provides SNMP monitoring and management for this Mac.",
    "impact": "SNMP monitoring will not work.",
  },
  "org.openldap.slapd": {
    "description": "The OpenLDAP slapd server. It can serve directory data over LDAP.",
    "impact": "An LDAP directory served by this Mac will not work.",
  },
  "org.cups.cups-lpd": {
    "description": "The CUPS line printer daemon. It accepts legacy LPD print jobs.",
    "impact": "Legacy LPD printing to this Mac will not work.",
  },
  "com.apple.tftpd": {
    "description": "The TFTP server. It serves files over Trivial FTP for network boot and device provisioning.",
    "impact": "TFTP file transfers will not work.",
  },
  "com.apple.uucp": {
    "description": "The legacy UUCP daemon (uucico). It handles Unix-to-Unix Copy file transfers and remote execution.",
    "impact": "Legacy UUCP transfers will not work. Not relevant for most users.",
  },
  "com.apple.ntalkd": {
    "description": "The legacy talk daemon. It supports the old Unix talk protocol.",
    "impact": "Legacy talk requests will not work. Not relevant for most users.",
  },
  "com.apple.getty": {
    "description": "The getty daemon. It provides text console login prompts on ttys.",
    "impact": "Text console logins may not be available.",
  },
  # --- Power Management ---
  "com.apple.PerfPowerServices": {
    "description": "The performance and power services daemon. It collects detailed power/performance telemetry for diagnostics and optimization.",
    "impact": "Power and performance telemetry will not be collected.",
  },
  "com.apple.PerfPowerServicesExtended": {
    "description": "The extended performance and power services daemon. It collects additional long-term telemetry.",
    "impact": "Extended power/performance telemetry will not be collected.",
  },
  "com.apple.PowerUIAgent": {
    "description": "The power UI agent. It shows battery, charging, and low-power alerts and manages related UI.",
    "impact": "Battery and power notifications may not appear.",
  },
  "com.apple.peakpowermanagerd": {
    "description": "The peak power manager daemon. It caps short-term CPU/GPU power draw to protect the power supply and manage thermals.",
    "impact": "The system may allow power spikes that trigger throttling or shutdowns.",
  },
  "com.apple.powerexperienced": {
    "description": "The power experience daemon. It adapts power behavior and collects data for battery/energy optimization.",
    "impact": "Adaptive power management may be less effective.",
  },
  "com.apple.powerchime": {
    "description": "The power chime app. It plays the chime when the charger is connected.",
    "impact": "The charger-connect chime will not play.",
  },
  # --- Photos & Media ---
  "com.apple.sportsd": {
    "description": "The sports daemon. It fetches sports scores and schedules for the TV and News apps.",
    "impact": "Sports scores and schedules may not update.",
  },
  "com.apple.replayd": {
    "description": "The ReplayKit daemon. It handles screen recording and broadcast features for apps and games.",
    "impact": "Screen recording and game broadcast features may not work.",
  },
  "com.apple.voicememod": {
    "description": "The Voice Memos daemon. It manages voice memo recordings and their metadata.",
    "impact": "Voice Memos may not record or manage recordings correctly.",
  },
  "com.apple.mobiletimerd": {
    "description": "The timer daemon for the Clock app. It runs timers and alarms.",
    "impact": "Timers and alarms may not fire.",
  },
  "com.apple.MENotificationAgent": {
    "description": "The notification agent for MediaExtension. It displays prompts and notifications for media extensions.",
    "impact": "Notifications about media extensions may not appear.",
  },
  "com.apple.sociallayerd": {
    "description": "The SocialLayer daemon. It provides shared links and social content in Messages and other apps.",
    "impact": "Shared links and social content may not appear.",
  },
  "com.apple.stickersd": {
    "description": "The Stickers daemon. It provides sticker data and sticker pickers to Messages and other apps.",
    "impact": "Stickers may not appear or sync.",
  },
  # --- Proactive & Intelligence ---
  "com.apple.ModelCatalogAgent": {
    "description": "The Model Catalog agent. It manages the on-device catalog of available machine-learning models.",
    "impact": "ML-backed features may not find or update their models.",
  },
  "com.apple.milod": {
    "description": "The MicroLocation daemon. It learns fine-grained location context from nearby signals for proactive features.",
    "impact": "Micro-location based suggestions may not work.",
  },
  "com.apple.mlhostd": {
    "description": "The machine-learning host daemon. It hosts Core ML models for other processes.",
    "impact": "Apps and system features that use hosted ML models may fail.",
  },
  "com.apple.mlruntimed": {
    "description": "The machine-learning runtime daemon. It executes ML models on behalf of clients.",
    "impact": "ML-backed features may fail to run.",
  },
  "com.apple.intelligencetasksd": {
    "description": "The intelligence tasks daemon. It schedules and runs on-device intelligence tasks.",
    "impact": "On-device intelligence features may not run.",
  },
  "com.apple.siriinferenced": {
    "description": "The Siri inference daemon. It runs on-device inference for Siri and related intelligence features.",
    "impact": "Siri and other on-device intelligence features may not work.",
  },
  "com.apple.proactived": {
    "description": "The proactive daemon. It coordinates proactive suggestions and predictions.",
    "impact": "Proactive suggestions may not appear.",
  },
  "com.apple.reversetemplated": {
    "description": "The CoreSuggestions reverse-templating service. It extracts structured data from text for suggestions.",
    "impact": "Suggestions from mail/messages content may be less accurate.",
  },
  "com.apple.searchtoold": {
    "description": "The OmniSearch tool daemon. It supports Spotlight/OmniSearch queries and ranking.",
    "impact": "Search results may be incomplete or slower.",
  },
  "com.apple.spotlightknowledged.importer": {
    "description": "The Spotlight knowledge importer. It imports data into the on-device knowledge store for search and Siri.",
    "impact": "Spotlight and Siri knowledge results may be less complete.",
  },
  "com.apple.spotlightknowledged.updater": {
    "description": "The Spotlight knowledge updater. It keeps the on-device knowledge store current.",
    "impact": "Spotlight and Siri knowledge results may become stale.",
  },
  "com.apple.peopled": {
    "description": "The People daemon. It finds and suggests people from contacts, mail, and messages for sharing and Siri.",
    "impact": "People suggestions in sharing sheets and Siri may not work.",
  },
  "com.apple.contacts.donation-agent": {
    "description": "The contacts donation agent. It donates contact information to Spotlight and Siri for search and suggestions.",
    "impact": "Contacts may not appear in Spotlight/Siri suggestions.",
  },
  "com.apple.biomesyncd": {
    "description": "The Biome sync daemon. It syncs on-device behavioral data used by proactive and intelligence features.",
    "impact": "Behavioral data will not sync, reducing proactive feature quality.",
  },
  # --- Safari & WebKit ---
  "com.apple.Safari.SafeBrowsing.Service": {
    "description": "The Safari Safe Browsing service. It checks URLs against Apple/Google safe-browsing lists to block malicious sites.",
    "impact": "Safari will not warn about or block known malicious websites.",
  },
  # --- Siri & Dictation ---
  "com.apple.assistant_cdmd": {
    "description": "The Siri continuous dialog manager daemon. It manages multi-turn Siri conversations.",
    "impact": "Multi-turn Siri conversations may not work.",
  },
  "com.apple.speech.speechsynthesisd.arm64": {
    "description": "The Apple Silicon build of the speech synthesis daemon.",
    "impact": "Text-to-speech may fail on Apple Silicon if this architecture-specific job is missing.",
  },
  # --- System Core ---
  "com.apple.coredatad": {
    "description": "The Core Data daemon. It supports Core Data stores, including CloudKit mirroring.",
    "impact": "Apps using Core Data with CloudKit may fail to sync.",
  },
  "com.apple.datastored": {
    "description": "The XPC data store daemon. It publishes and manages data-store endpoints for system frameworks.",
    "impact": "Some system frameworks may fail to access their data stores.",
  },
  "com.apple.accounts.dom": {
    "description": "The accounts daemon (DOM variant). It maintains account data for the system.",
    "impact": "Some account-management features may fail.",
  },
  "com.apple.linkd": {
    "description": "The link index daemon. It maintains the shared index used to resolve app links and related metadata.",
    "impact": "Universal Links and some app-link resolution may fail.",
  },
  "com.apple.xtyped": {
    "description": "The XType/font daemon (the successor to fontd). It activates and manages fonts for the user session and system.",
    "impact": "Some text/font services may not work.",
  },
  "com.apple.kcgend": {
    "description": "The KernelCGEvent daemon. It delivers low-level kernel events to user space.",
    "impact": "Low-level kernel event delivery may be impaired.",
  },
  "com.apple.atrun": {
    "description": "The at-job runner. It executes jobs scheduled with the at command.",
    "impact": "Jobs scheduled with at will not run.",
  },
  "com.apple.toolkitd": {
    "description": "The App Intents toolkit daemon. It indexes and resolves App Intents metadata for Shortcuts and Siri.",
    "impact": "Shortcuts and Siri may not discover app actions.",
  },
  "com.apple.uikitsystemapp": {
    "description": "UIKitSystem, the host app that runs UIKit apps and system UI on macOS.",
    "impact": "UIKit-based apps and some system UI may fail to run.",
  },
  "com.apple.AEServer": {
    "description": "The Apple Event Program-to-Program Communication server (AEServer). It routes Apple Events between processes.",
    "impact": "AppleScript and Apple Event automation may fail.",
  },
  "com.apple.jetsamproperties.Mac": {
    "description": "A property list (not a runnable service) that defines Jetsam memory limits for macOS.",
    "impact": "Jetsam memory limits may fall back to defaults, changing memory-pressure behavior.",
  },
  "com.apple.loginwindow.LWWeeklyMessageTracer": {
    "description": "The loginwindow weekly analytics helper. It reports weekly login/window-server statistics.",
    "impact": "Weekly login analytics will not be reported.",
  },
  "com.apple.UserEventAgent-CryptexContainer": {
    "description": "A UserEventAgent instance for cryptex containers. It routes system events inside the cryptex environment.",
    "impact": "Some events inside cryptex containers may not be handled.",
  },
  "com.apple.UserEventAgent-LoginWindow": {
    "description": "A UserEventAgent instance for the login window. It routes events before a user logs in.",
    "impact": "Some login-window events may not be handled.",
  },
  # --- Undocumented ---
  "com.apple.ctcategories.service": {
    "description": "The CT categories service. It manages category data for CoreTelephony-style services.",
    "impact": "Some telephony/communication categorization features may not work.",
  },
  # --- Text & Input ---
  "com.apple.textcomposerd": {
    "description": "The text composer daemon. It composes and transforms text for input methods and writing tools.",
    "impact": "Text composition and writing tools may not work.",
  },
  "com.apple.translationd": {
    "description": "The translation daemon. It provides on-device and server translation for apps and system text.",
    "impact": "Translation features will not work.",
  },
  "com.apple.DataDetectorsLocalSources": {
    "description": "A helper that supplies local data-detector sources (dates, addresses, phone numbers) to apps.",
    "impact": "Data detection in text may fail.",
  },
  "com.apple.CharacterPicker.FileService": {
    "description": "The Character Viewer file service. It supplies character/emoji data to the picker.",
    "impact": "The Character Viewer may not show all characters or emoji.",
  },
  "com.apple.CharacterPicker.RemoteGenerationViewService": {
    "description": "The remote view service that renders characters and emoji for the Character Viewer.",
    "impact": "Character/emoji previews may not render.",
  },
  "com.apple.fontd.useragent": {
    "description": "The per-user font daemon. It activates and manages fonts for the logged-in user.",
    "impact": "User-installed fonts may not be available to apps.",
  },
  "com.apple.FontValidator": {
    "description": "A validation tool for fonts. It checks fonts for corruption and policy compliance.",
    "impact": "Invalid fonts may not be detected before use.",
  },
  "com.apple.FontRegistryUIAgent": {
    "description": "The Font Registry UI agent. It shows font activation and registration dialogs.",
    "impact": "Font activation dialogs may not appear.",
  },
  # --- User Interface & Windowing ---
  "com.apple.Dock": {
    "description": "The Dock process. It draws and manages the Dock, app icons, and window minimization.",
    "impact": "The Dock will disappear and window management from the Dock will stop.",
  },
  "com.apple.AquaAppearanceHelper": {
    "description": "A helper for the Aqua appearance system. It applies theme colors and appearance settings for the window server.",
    "impact": "System appearance and accent colors may not apply correctly.",
  },
  "com.apple.AquaAppearanceHelper.agent": {
    "description": "The per-user Aqua appearance agent. It applies appearance settings in the user session.",
    "impact": "Appearance changes may not take effect for the user.",
  },
  "com.apple.SystemUIServer": {
    "description": "The SystemUIServer process. It runs the menu bar status items such as Wi-Fi, battery, and the clock.",
    "impact": "Menu bar status icons may disappear.",
  },
  "com.apple.WindowManager": {
    "description": "The WindowManager app. It provides Stage Manager and window tiling/management features.",
    "impact": "Stage Manager and window management features will not work.",
  },
  "com.apple.Spotlight": {
    "description": "The Spotlight menu process. It shows the Spotlight search field and results in the menu bar.",
    "impact": "Spotlight search from the menu bar will not work.",
  },
  "com.apple.notificationcenterui": {
    "description": "The Notification Center UI process. It draws notifications, widgets, and the Notification Center panel.",
    "impact": "Notifications and widgets will not be displayed.",
  },
  "com.apple.UserNotificationCenterAgent-LoginWindow": {
    "description": "The Notification Center agent for the login window. It shows notifications before login.",
    "impact": "Notifications at the login window may not appear.",
  },
  "com.apple.screencaptureui.agent": {
    "description": "The screenshot UI agent. It provides the screenshot and screen-recording interface (Cmd+Shift+5).",
    "impact": "The screenshot interface may not open.",
  },
  "com.apple.wallpaper": {
    "description": "The WallpaperAgent process. It displays and manages the desktop wallpaper and dynamic wallpapers.",
    "impact": "Wallpapers may not display or change.",
  },
  "com.apple.ScriptMenuApp": {
    "description": "The Script Menu extra. It provides the menu bar Scripts menu.",
    "impact": "The Scripts menu will not appear.",
  },
  "com.apple.ServicesUIAgent": {
    "description": "The Services UI agent. It provides the Services menu and service-related UI.",
    "impact": "The Services menu and many app services may not work.",
  },
  "com.apple.OSDUIHelper": {
    "description": "The on-screen display helper. It draws volume, brightness, and other HUD overlays.",
    "impact": "Volume/brightness HUDs and similar on-screen overlays will not appear.",
  },
  "com.apple.PIPAgent": {
    "description": "The Picture-in-Picture agent. It manages the PiP window and controls.",
    "impact": "Picture-in-Picture video will not work.",
  },
  "com.apple.nowplayingtouchui": {
    "description": "The Now Playing UI for the Touch Bar. It shows media controls on the Touch Bar.",
    "impact": "Media controls on the Touch Bar may not appear.",
  },
  "com.apple.PosterBoard": {
    "description": "The PosterBoard UI process. It renders the lock screen and poster-style background content.",
    "impact": "Lock-screen/poster UI may not render correctly.",
  },
  "com.apple.FollowUpUI": {
    "description": "The Follow Up UI. It presents Follow Up items (for example in Mail) to the user.",
    "impact": "Follow Up items may not be shown.",
  },
  "com.apple.menuextra.battery.helper": {
    "description": "The battery menu extra helper. It supplies battery status to the menu bar item.",
    "impact": "The battery menu extra may not display status correctly.",
  },
  "com.apple.TextInputUI.xpc.CursorUIViewService": {
    "description": "The cursor UI view service for text input. It draws the text cursor and related input UI.",
    "impact": "The text cursor or input UI may not render.",
  },
  "com.apple.quicklook.ui.helper": {
    "description": "The Quick Look UI helper. It displays the Quick Look preview window.",
    "impact": "Quick Look previews may not open.",
  },
  "com.apple.FolderActionsDispatcher": {
    "description": "The Folder Actions dispatcher. It runs Folder Action scripts when folders change.",
    "impact": "Folder Actions will not run.",
  },
  "com.apple.appkit.xpc.ColorSampler": {
    "description": "The AppKit color sampler service. It provides the magnifier color picker used by color panels and Digital Color Meter.",
    "impact": "The on-screen color picker may not work.",
  },
  # --- Third-Party ---
  "com.google.GoogleUpdater.wake.system": {
    "description": "Google Updater wake daemon. It periodically wakes to check for and install updates to Google applications.",
    "impact": "Google apps such as Chrome will not update automatically.",
  },
  "com.google.keystone.agent": {
    "description": "The Google Keystone agent (user). It checks for updates to Google applications.",
    "impact": "Google apps will not update automatically for this user.",
  },
  "com.google.keystone.daemon": {
    "description": "The Google Keystone daemon (system). It performs privileged update tasks for Google software.",
    "impact": "Google software updates may fail to install.",
  },
  "com.google.keystone.xpcservice": {
    "description": "The Google Keystone XPC service. It supports update tasks for Google software.",
    "impact": "Google software update tasks may fail.",
  },
  "us.zoom.ZoomDaemon": {
    "description": "The Zoom daemon. It is a privileged helper used by Zoom for system-level features.",
    "impact": "Some Zoom features (installation, sharing, or updates) may not work.",
  },
  "us.zoom.updater": {
    "description": "The Zoom updater agent. It checks for and installs Zoom updates.",
    "impact": "Zoom will not update automatically.",
  },
  "us.zoom.updater.login.check": {
    "description": "The Zoom updater login check agent. It checks for updates at login.",
    "impact": "Zoom updater checks at login will not run.",
  },
  "Adobe_Genuine_Software_Integrity_Service": {
    "description": "The Adobe Genuine Software Integrity Service. It verifies that installed Adobe apps are genuine and licensed.",
    "impact": "Adobe apps may report licensing problems or refuse to launch.",
  },
  "com.docker.socket": {
    "description": "The Docker Desktop socket helper. It manages the Docker daemon socket and related privileged networking.",
    "impact": "Docker Desktop may not be able to start or communicate with its daemon.",
  },
  "com.docker.vmnetd": {
    "description": "The Docker Desktop VM networking daemon. It sets up networking for Docker virtual machines.",
    "impact": "Docker containers may have no network connectivity.",
  },
  "com.figma.daemon": {
    "description": "The Figma daemon. It supports Figma desktop features such as local font access and deep links.",
    "impact": "Some Figma desktop features may not work.",
  },
  "com.macpaw.CleanMyMac-setapp.HealthMonitor": {
    "description": "The CleanMyMac Health Monitor agent from Setapp. It monitors system health for the CleanMyMac app.",
    "impact": "CleanMyMac health monitoring may not work.",
  },
  "com.postgresapp.Postgres2LoginHelper": {
    "description": "The Postgres.app login helper. It helps Postgres.app set up its environment at login.",
    "impact": "Postgres.app helper tasks may not run at login.",
  },
  "homebrew.mxcl.redis": {
    "description": "The Homebrew-managed Redis server service. It runs a local Redis instance.",
    "impact": "The local Redis server will not start.",
  },
  # --- Third-Party ---
  "com.appfactory.core": {
    "description": "The AppLab Core helper from AppFactory. It runs the AppFactory/AppLab development environment.",
    "impact": "AppFactory/AppLab projects may not launch or build.",
  },
  # --- User Interface & Windowing ---
  "com.apple.LinkedNotesUIService": {
    "description": "The PaperKit linked-notes UI service. It renders linked notes and markup previews inside documents.",
    "impact": "Linked notes and markup previews may not render.",
  },
  "com.apple.SpacesTouchBarAgent.app": {
    "description": "The Spaces agent app for the Touch Bar. It shows Mission Control and Spaces controls on the Touch Bar.",
    "impact": "Spaces controls on the Touch Bar will not work.",
  },
  "com.apple.liveactivitiesd": {
    "description": "The Live Activities daemon (SessionKit/ActivityKit). It manages Live Activities and their updates on the Mac.",
    "impact": "Live Activities may not start or update.",
  },
  # --- Installation & Updates ---
  "com.apple.inboxupdaterd": {
    "description": "The Mobile Inbox Updater daemon. It installs preinstalled 'inbox' assets during macOS updates.",
    "impact": "Some preinstalled assets may not be updated during an OS update.",
  },
  "com.apple.jetpackassetd": {
    "description": "The Jet asset daemon. It downloads and manages JetPack assets used by Apple's store and service UIs.",
    "impact": "Store-related artwork and UI assets may not load.",
  },
  # --- Diagnostics & Logging ---
  "com.apple.feedbackd": {
    "description": "The Feedback Assistant daemon. It collects and submits feedback and diagnostic reports to Apple.",
    "impact": "Feedback Assistant reports may not be collected or submitted.",
  },
  "com.apple.symptomsd-diag.agent": {
    "description": "The diagnostics symptoms agent. It collects and reports network and system symptoms for diagnostics.",
    "impact": "Diagnostic symptom reports may not be collected.",
  },
  "com.apple.symptomsd.distributed-agent": {
    "description": "The distributed symptoms agent. It gathers symptoms from other processes for system diagnostics.",
    "impact": "Distributed diagnostic symptom reporting may fail.",
  },
  # --- System Core ---
  "com.apple.AddressBook.AssistantService": {
    "description": "The Address Book assistant service (ABAssistantService). It provides assistant and automation support for Contacts.",
    "impact": "Contacts-related assistant features may fail.",
  },
  "com.apple.AddressBook.abd": {
    "description": "The Address Book manager daemon. It manages the central Contacts database.",
    "impact": "Contacts may not be available or may stop syncing.",
  },
  "com.apple.MailServiceAgent": {
    "description": "The Mail service agent. It performs background Mail tasks such as rules processing and junk-mail handling.",
    "impact": "Mail background processing may fail.",
  },
  "com.apple.email.maild": {
    "description": "The Mail daemon from the EmailDaemon framework. It manages mail accounts, messages, and background fetching.",
    "impact": "Mail may not fetch, send, or update messages.",
  },
  "com.apple.csuseragent": {
    "description": "The CoreServices user agent. It registers and launches user-level CoreServices helper applications.",
    "impact": "Some CoreServices helper apps may not launch.",
  },
  "com.apple.usernoted": {
    "description": "The user notification daemon. It delivers notifications to Notification Center and apps.",
    "impact": "Notifications may not be delivered.",
  },
  "com.apple.usernotificationsd": {
    "description": "The UserNotificationsCore daemon. It provides the core notification service used by apps and the system.",
    "impact": "Notifications and notification-related APIs may fail.",
  },
  "com.apple.systemsettingsagent": {
    "description": "The System Settings agent. It applies settings changes and secure-pairing state for System Settings.",
    "impact": "Some System Settings changes may not apply.",
  },
  "com.apple.syncdefaultsd": {
    "description": "The SyncedDefaults daemon. It syncs app preferences through iCloud key-value storage.",
    "impact": "App settings may not sync between devices.",
  },
  "com.apple.syncservices.SyncServer": {
    "description": "The legacy Sync Services server. It supports older sync schemas and clients.",
    "impact": "Legacy sync clients may not synchronize. Modern macOS uses CloudKit instead.",
  },
  "com.apple.warmd_agent": {
    "description": "The per-user warmd agent. It tracks login-session exit and warm-cache state at logout.",
    "impact": "Warm-cache cleanup at logout may not run correctly.",
  },
  "com.apple.pluginkit.pkreporter": {
    "description": "The PlugInKit reporter. It reports plug-in and extension state to the system.",
    "impact": "Plug-in diagnostics and state reporting may be incomplete.",
  },
  # --- Device Communication ---
  "com.apple.businessservicesd": {
    "description": "The Business Chat daemon. It supports Messages for Business conversations.",
    "impact": "Messages for Business may not work.",
  },
  "com.apple.coreservices.UASharedPasteboardProgressUI": {
    "description": "The Universal Clipboard progress UI. It shows transfer progress when a large clipboard item moves between nearby devices.",
    "impact": "Universal Clipboard transfer progress may not appear.",
  },
  "com.apple.nexusd": {
    "description": "The Nexus daemon. It manages nearby-device connections used by Continuity and handoff features.",
    "impact": "Nearby-device Continuity features may not work.",
  },
  # --- iCloud & CloudKit ---
  "com.apple.contacts.postersyncd": {
    "description": "The Contacts poster sync daemon. It syncs Contact Posters across your devices.",
    "impact": "Contact Posters may not sync between devices.",
  },
  "com.apple.StatusKitAgent": {
    "description": "The StatusKit agent. It shares user status such as Focus across your Apple devices.",
    "impact": "Focus status sharing across devices may not work.",
  },
  "com.apple.bookdatastored": {
    "description": "The BookDataStore daemon. It stores and syncs Books data such as reading position and library state.",
    "impact": "Books data may not be stored or synced.",
  },
  # --- Filesystem & Storage ---
  "com.apple.STMUIHelper": {
    "description": "The Storage Management UI helper. It shows dialogs and progress for storage cleanup and optimization.",
    "impact": "Storage Management dialogs may not appear.",
  },
  "com.apple.FilesystemUI": {
    "description": "The File System UI agent. It displays filesystem-related alerts, such as unreadable or damaged disk warnings.",
    "impact": "Filesystem warning dialogs may not appear.",
  },
  "com.apple.metadata.mdwrite": {
    "description": "The Spotlight metadata writer. It writes metadata attributes to files so Spotlight can index them.",
    "impact": "Spotlight metadata may not be written, making search results incomplete.",
  },
  "com.apple.coreimportd": {
    "description": "The Spotlight core importer. It imports metadata from files and stores it in the Spotlight index.",
    "impact": "New or changed files may not appear in Spotlight search.",
  },
  # --- Hardware & Drivers ---
  "com.apple.MobileAccessoryUpdater.fudHelperAgent": {
    "description": "The firmware update helper agent for MobileAccessoryUpdater. It assists with firmware updates for connected Apple accessories.",
    "impact": "Accessory firmware updates may fail.",
  },
  "com.apple.mobilerepaird": {
    "description": "The CoreRepair daemon. It manages parts pairing, repair status, and repair follow-ups for Apple device repairs.",
    "impact": "Repair status and parts-pairing information may not work.",
  },
  "com.apple.firmwaresyncd": {
    "description": "The firmware sync daemon (part of bless). It synchronizes boot firmware data to the startup volume.",
    "impact": "Boot firmware updates or firmware stamps may not be applied correctly.",
  },
  "com.apple.arkitd": {
    "description": "The ARKit daemon. It provides augmented-reality tracking and sensor services to ARKit apps.",
    "impact": "ARKit-based apps and features may not work.",
  },
  "com.apple.remotecompositorclientd": {
    "description": "The remote compositor client daemon (WakeBoard/CompositorServices). It supports remote compositor sessions such as Mac Virtual Display.",
    "impact": "Remote display and virtual-display features may not work.",
  },
  "com.apple.icdd": {
    "description": "The Image Capture daemon. It detects and communicates with cameras and scanners.",
    "impact": "Image Capture may not detect cameras or scanners.",
  },
  "com.apple.printtool.agent": {
    "description": "The print tool agent from PrintCore. It handles print-job processing and printer communication.",
    "impact": "Printing may fail or print jobs may hang.",
  },
  "com.apple.printuitool.agent": {
    "description": "The Print UI tool agent. It displays printing dialogs and manages print options.",
    "impact": "Print dialogs and print options may not work.",
  },
  "com.apple.cvmsCompAgent3425AMD_x86_64": {
    "description": "An OpenGL shader compiler agent for the AMD 3425 GPU family. It precompiles shaders used by OpenGL apps.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent3425AMD_x86_64_1": {
    "description": "A second instance of the OpenGL shader compiler agent for the AMD 3425 GPU family.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent3600_arm64": {
    "description": "An OpenGL shader compiler agent for the 3600 GPU family on Apple Silicon. It precompiles OpenGL shaders.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent3600_arm64_1": {
    "description": "A second instance of the OpenGL shader compiler agent for the 3600 GPU family on Apple Silicon.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent3600_x86_64": {
    "description": "An OpenGL shader compiler agent for the 3600 GPU family on Intel Macs. It precompiles OpenGL shaders.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent3600_x86_64_1": {
    "description": "A second instance of the OpenGL shader compiler agent for the 3600 GPU family on Intel Macs.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent_arm64": {
    "description": "The OpenGLES shader compiler agent for Apple Silicon. It precompiles OpenGLES shaders.",
    "impact": "OpenGLES apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent_arm64_1": {
    "description": "A second instance of the OpenGLES shader compiler agent for Apple Silicon.",
    "impact": "OpenGLES apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent_x86_64": {
    "description": "The OpenGL shader compiler agent for Intel Macs. It precompiles OpenGL shaders.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  "com.apple.cvmsCompAgent_x86_64_1": {
    "description": "A second instance of the OpenGL shader compiler agent for Intel Macs.",
    "impact": "OpenGL apps may compile shaders on first use, causing slower launches.",
  },
  # --- Photos & Media ---
  "com.apple.avatarsd": {
    "description": "The avatar persistence daemon. It stores and manages Memoji and other avatar data.",
    "impact": "Memoji and avatar data may not persist.",
  },
  # --- Maps & Location ---
  "com.apple.CoreLocationAgent": {
    "description": "The Core Location agent. It provides location data and location-based services to apps in the user session.",
    "impact": "Apps may not be able to determine your location.",
  },
  "com.apple.Maps.mapssyncd": {
    "description": "The MapsSync daemon. It syncs Maps data such as favorites, recents, and guides across devices.",
    "impact": "Maps favorites and recent places may not sync.",
  },
  "com.apple.geodMachServiceBridge": {
    "description": "The GeoServices Mach service bridge. It connects apps to the geod location and mapping services.",
    "impact": "Location and mapping services may fail to connect.",
  },
  # --- Mgt & Development ---
  "com.apple.CoreDevice.remotepairingd": {
    "description": "The CoreDevice remote pairing daemon. It pairs this Mac with development devices for Xcode and device management.",
    "impact": "Xcode and developer tools may not be able to pair with devices.",
  },
  "com.apple.ManagedClient.startup": {
    "description": "The ManagedClient startup agent. It applies managed preferences and legacy management settings at login.",
    "impact": "Managed preferences may not be applied.",
  },
  "com.apple.ManagedClientAgent.enrollagent": {
    "description": "The ManagedClient enrollment agent. It enrolls the Mac in device management and processes enrollment profiles.",
    "impact": "Automatic MDM enrollment may fail.",
  },
  # --- Networking ---
  "com.apple.AirPortBaseStationAgent": {
    "description": "The AirPort Base Station Agent. It discovers and manages AirPort base stations and Time Capsules.",
    "impact": "AirPort base stations cannot be configured or monitored from this Mac.",
  },
  "com.apple.bootpd": {
    "description": "The BOOTP/DHCP server daemon. It provides legacy network boot and DHCP services.",
    "impact": "Legacy BOOTP/DHCP serving will not work.",
  },
  "com.apple.odproxyd": {
    "description": "The Open Directory proxy daemon. It proxies directory-service requests to Open Directory and LDAP servers.",
    "impact": "Directory authentication and lookups may fail.",
  },
  "com.apple.wifi.WiFiAgent": {
    "description": "The Wi-Fi agent. It provides the Wi-Fi menu and user-session Wi-Fi management.",
    "impact": "The Wi-Fi menu and user-session Wi-Fi controls may not work.",
  },
  # --- Proactive & Intelligence ---
  "com.apple.corespotlightd": {
    "description": "The CoreSpotlight daemon. It manages the Spotlight index and answers search queries.",
    "impact": "Spotlight search results may be incomplete or unavailable.",
  },
  "com.apple.corespotlightservice": {
    "description": "The CoreSpotlight service. It indexes app content for Spotlight search.",
    "impact": "Content from apps may not appear in Spotlight results.",
  },
  "com.apple.managedcorespotlightd": {
    "description": "The managed CoreSpotlight daemon. It indexes managed content for Spotlight while respecting management restrictions.",
    "impact": "Managed content may not appear in Spotlight search.",
  },
  "com.apple.mdworker.application": {
    "description": "A Spotlight metadata worker for application content. It extracts metadata from app bundles and documents.",
    "impact": "Some application content may not be indexed for Spotlight.",
  },
  "com.apple.mdworker.single.arm64": {
    "description": "A single-process Spotlight metadata worker for Apple Silicon. It extracts metadata from files for indexing.",
    "impact": "Some files may not be indexed for Spotlight.",
  },
  "com.apple.mdworker.single.x86_64": {
    "description": "A single-process Spotlight metadata worker for Intel Macs. It extracts metadata from files for indexing.",
    "impact": "Some files may not be indexed for Spotlight.",
  },
  "com.apple.mdworker.sizing": {
    "description": "A Spotlight metadata worker that calculates file sizes and related attributes for indexing.",
    "impact": "File-size metadata in Spotlight may be incomplete.",
  },
  "com.apple.ciphermld": {
    "description": "The CipherML daemon. It runs privacy-preserving machine-learning operations on encrypted data.",
    "impact": "Privacy-preserving ML features may not work.",
  },
  # --- Security & Keychain ---
  "com.apple.TrustEvaluationAgent": {
    "description": "The trust evaluation agent. It evaluates certificate and TLS trust for apps and system services.",
    "impact": "Certificate trust evaluation may fail, breaking secure connections.",
  },
  "com.apple.AuthenticationServicesCore.AuthenticationServicesAgent": {
    "description": "The AuthenticationServices agent. It supports passkeys, password autofill, and sign-in with Apple in apps.",
    "impact": "Passkeys, password autofill, and Sign in with Apple may fail.",
  },
  "com.apple.AutoFillPanel": {
    "description": "The AutoFill panel service. It displays saved-password and passkey suggestions in apps and browsers.",
    "impact": "Autofill suggestions may not appear.",
  },
  "com.apple.PasswordService": {
    "description": "The password service. It provides saved-password and credential services to Safari and other apps.",
    "impact": "Saved-password features may fail.",
  },
  "com.apple.XProtect.agent.scan.startup": {
    "description": "The XProtect on-demand scan agent. It performs a malware scan at startup.",
    "impact": "The startup malware scan will not run.",
  },
  "com.apple.communicationtrustd": {
    "description": "The communication trust daemon. It evaluates trust signals for messages and calls, such as unknown-sender filtering.",
    "impact": "Spam and unknown-sender filtering may be less effective.",
  },
  "com.apple.coreidvd": {
    "description": "The CoreIDV daemon. It performs identity-document verification and liveness checks for identity features.",
    "impact": "Identity verification and liveness checks may not work.",
  },
  # --- Family & ScreenTime ---
  "com.apple.AskPermissionUI": {
    "description": "The Ask Permission UI. It displays Ask to Buy and parental-approval prompts.",
    "impact": "Ask to Buy and permission prompts may not appear.",
  },
  "com.apple.Notes.datastore": {
    "description": "The Notes data store daemon. It manages the Notes database and serves note content to the Notes app.",
    "impact": "Notes may not open, save, or sync correctly.",
  },
}

CATEGORIZATION_MAP = {
  "♿️ Accessibility": [
    "com.apple.accessibility.MotionTrackingAgent",
    "com.apple.accessibility.axassetsd",
    "com.apple.AccessibilityVisualsAgent",
    "com.apple.scrod",
    "com.apple.universalaccessd",
    "com.apple.voicebankingd",
    "com.apple.AXMediaUtilitiesService",
    "com.apple.accessibility.mediaaccessibilityd",
    "com.apple.accessibility.heard",
    "com.apple.universalaccessAuthWarn",
    "com.apple.accessibility.LiveTranscriptionAgent",
    "com.apple.accessibility.AXVisualSupportAgent",
    "com.apple.universalaccesscontrol",
    "com.apple.AccessibilityUIServer",
    "com.apple.DwellControl",
    "com.apple.VoiceOver",
    "com.apple.ScreenReaderUIServer",
    "com.apple.AssistiveControl",
    "com.apple.KeyboardAccessAgent",
    "com.apple.accessibility.dfrhud",
  ],
  "📊 Advertising & Analytics": [
    "com.apple.ap.adprivacyd",
    "com.apple.ap.promotedcontentd",
    "com.apple.adid",
    "com.apple.ecosystemagent",
    "com.apple.parsec-fbf",
    "com.apple.analyticsd",
    "com.apple.osanalytics.osanalyticshelper",
    "com.apple.symptomsd",
    "com.apple.wifianalyticsd",
    "com.apple.audioanalyticsd",
    "com.apple.ecosystemanalyticsd",
    "com.apple.perfpowermetricd",
    "com.apple.metrickitd",
    "com.apple.analyticsagent",
    "com.apple.dprivacyd",
    "com.apple.PerfPowerTelemetryClientRegistrationService",
    "com.apple.memoryanalyticsd",
    "com.apple.inputanalyticsd", 
    "com.apple.geoanalyticsd",
  ],
  "🛒 App & Store Related": [
    "com.apple.appstoreagent",
    "com.apple.appstorecomponentsd",
    "com.apple.appstored",
    "com.apple.backgroundassets.user",
    "com.apple.commerce",
    "com.apple.ndoagent",
    "com.apple.passd",
    "com.apple.financed",
    "com.apple.storeassetd",
    "com.apple.storelegacy",
    "com.apple.watchlistd",
    "com.apple.newsd",
    "com.apple.appinstalld",
    "com.apple.assetsubscriptiond",
    "com.apple.bookassetd",
    "com.apple.storeaccountd",
    "com.apple.storeuid",
    "com.apple.storedownloadd",
    "com.apple.appsleep",
    "com.apple.storekitagent",
    "com.apple.appplaceholdersyncd",
    "com.apple.askpermissiond",
    "com.apple.amsondevicestoraged",
    "com.apple.amsaccountsd",
    "com.apple.amsengagementd",
    "com.apple.AppStoreDaemon.StorePrivilegedODRService",
    "com.apple.AppStoreDaemon.StorePrivilegedTaskService",
    "com.apple.eligibilityd",
    "com.apple.fairplayd",
    "com.apple.fairplaydeviceidentityd",
    "com.apple.storereceiptinstaller",
    "com.apple.videosubscriptionsd",
  ],
  "💾 Backup & Time Machine": [
    "com.apple.backupd",
    "com.apple.backupd-helper",
    "com.apple.mbproximityhelper",
    "com.apple.TMHelperAgent",
    "com.apple.mbsystemadministration",
    "com.apple.mbfloagent",
    "com.apple.mbbackgrounduseragent",
    "com.apple.mbuseragent",
    "com.apple.vsdbutil",
    "com.apple.mbusertrampoline",
  ],
  "📅 Calendar & Reminders": [
    "com.apple.calaccessd",
    "com.apple.calendar.CalendarAgentBookmarkMigrationService",
    "com.apple.remindd",
    "com.apple.CallHistoryPluginHelper",
    "com.apple.dataaccess.dataaccessd",
    "com.apple.followupd",
    "com.apple.callhistoryd",
    "com.apple.CallHistorySyncHelper",
    "com.apple.exchange.exchangesyncd",
    "com.apple.notes.exchangenotesd",
  ],
  "📱 Device Communication": [
    "com.apple.AMPDeviceDiscoveryAgent",
    "com.apple.AMPDevicesAgent",
    "com.apple.AMPSystemPlayerAgent",
    "com.apple.bluetoothaudiod",
    "com.apple.bluetoothd",
    "com.apple.btsa",
    "com.apple.businessservicesd",
    "com.apple.cloudpaird",
    "com.apple.coreservices.UASharedPasteboardProgressUI",
    "com.apple.ensemble",
    "com.apple.facetimemessagestored",
    "com.apple.idsfoundation.IDSRemoteURLConnectionAgent",
    "com.apple.idsremoteurlconnectionagent",
    "com.apple.imdpersistence.IMDPersistenceAgent",
    "com.apple.mediacontinuityd",
    "com.apple.mobiledeviceupdater",
    "com.apple.nearbyd",
    "com.apple.nexusd",
    "com.apple.rapportd",
    "com.apple.rapportd-user",
    "com.apple.sidecar-relay",
    "com.apple.ThreadCommissionerService",
    "com.apple.usbmuxd",
    "com.apple.CommCenter-osx",
    "com.apple.imagent",
    "com.apple.imtransferagent",
    "com.apple.telephonyutilities.callservicesd",
    "com.apple.imcore.imtransferagent",
    "com.apple.syncservices.uihandler",
    "com.apple.AddressBook.SourceSync",
    "com.apple.bluetoothuserd",
    "com.apple.bluetoothUIServer",
    "com.apple.CommCenter",
    "com.apple.BTServer.cloudpairing",
    "com.apple.BTServer.le.agent",
    "com.apple.companiond",
    "com.apple.RapportUIAgent",
    "com.apple.identityservicesd",
    "com.apple.sidecar-display-agent",
    "com.apple.BTServer.le",
    "com.apple.BlueTool",
    "com.apple.BluetoothUIService",
    "com.apple.ecosystemd",
    "com.apple.remoted",
    "com.apple.imautomatichistorydeletionagent", 
    "com.apple.sidecar-hid-relay",
  ],
  "🕵️  Diagnostics & Logging": [
    "com.apple.appleseed.seedusaged.postinstall",
    "com.apple.diagnosticspushd",
    "com.apple.DiagnosticsReporter",
    "com.apple.DumpPanicRecoveryOS",
    "com.apple.feedbackd",
    "com.apple.kdumpd",
    "com.apple.logd",
    "com.apple.ReportGPURestart",
    "com.apple.symptomsd-diag.agent",
    "com.apple.symptomsd.distributed-agent",
    "com.apple.sysdiagnose.darwinos",
    "com.apple.syslogd",
    "com.apple.spindump",
    "com.apple.ReportCrash",
    "com.apple.SubmitDiagInfo",
    "com.apple.tailspind",
    "com.apple.coresymbolicationd",
    "com.apple.enhancedloggingd",
    "com.apple.diagnosticextensionsd",
    "com.apple.sysdiagnose_agent",
    "com.apple.diagnostics_agent",
    "com.apple.spindump_agent",
    "com.apple.systemprofiler",
    "com.apple.CrashReporterSupportHelper",
    "com.apple.DumpGPURestart",
    "com.apple.DumpPanic",
    "com.apple.DumpPanic.Accessory",
    "com.apple.ReportCrash.Root",
    "com.apple.ReportMemoryException",
    "com.apple.ReportSystemMemory",
    "com.apple.aslmanager",
    "com.apple.bosreporter",
    "com.apple.boswatcher",
    "com.apple.corecaptured",
    "com.apple.diagnosticd",
    "com.apple.diagnosticextensions.osx.spotlight.helper",
    "com.apple.diagnosticextensions.osx.timemachine.helper",
    "com.apple.diagnosticservicesd",
    "com.apple.logd_helper",
    "com.apple.logd_reporter",
    "com.apple.logkextloadsd",
    "com.apple.newsyslog",
    "com.apple.powerdatad",
    "com.apple.powerlogHelperd",
    "com.apple.rtcreportingd",
    "com.apple.seld",
    "com.apple.signpost.signpost_reporter",
    "com.apple.symptomsd-diag",
    "com.apple.sysdiagnose",
    "com.apple.sysdiagnose_helper",
    "com.apple.systemstats.analysis",
    "com.apple.systemstats.daily",
    "com.apple.systemstats.microstackshot_periodic",
    "com.apple.thermaltrap",
    "com.apple.usbctelemetryd",
  ],
  "👪 Family & ScreenTime": [
    "com.apple.AskPermissionUI",
    "com.apple.asktod",
    "com.apple.assessmentagent",
    "com.apple.familycontrols.useragent",
    "com.apple.familycircled",
    "com.apple.macos.studentd",
    "com.apple.ScreenTimeAgent",
    "com.apple.parentalcontrols.check",
    "com.apple.FamilyControlsAgent",
    "com.apple.familycontrols",
    "com.apple.familynotificationd", 
    "com.apple.ScreenTimeSettingsAgent",
    "com.apple.UsageTrackingAgent",
  ],
  "💽 Filesystem & Storage": [
    "com.apple.coreimportd",
    "com.apple.diskspaced",
    "com.apple.FilesystemUI",
    "com.apple.fseventsd",
    "com.apple.diskarbitrationd",
    "com.apple.metadata.mdwrite",
    "com.apple.NVMeAgent",
    "com.apple.STMUIHelper",
    "com.apple.storagede.helper",
    "com.apple.storagekitd",
    "com.apple.corestorage.corestoraged",
    "com.apple.hdiejectd",
    "com.apple.nfsd",
    "com.apple.smbd",
    "com.apple.StorageManagement.Service",
    "com.apple.StorageManagementUIHelper",
    "com.apple.unmountassistant.useragent",
    "com.apple.apfsuseragent",
    "com.apple.DiskArbitrationAgent",
    "com.apple.FileProvider",
    "com.apple.fskit.fskit_agent",
    "com.apple.pboard",
    "com.apple.FileCoordination",
    "com.apple.afpfs_afpLoad",
    "com.apple.afpfs_checkafp",
    "com.apple.applessdstatistics",
    "com.apple.apfsd",
    "com.apple.asr",
    "com.apple.autofsd",
    "com.apple.automountd",
    "com.apple.corestorage.corestoragehelperd",
    "com.apple.diskimagesiod",
    "com.apple.diskimagesiod.ram",
    "com.apple.diskimagesiod.spb",
    "com.apple.diskmanagementstartup",
    "com.apple.filesystems.fskitd",
    "com.apple.filesystems.userfs_helper",
    "com.apple.filesystems.userfsd",
    "com.apple.fskit.fskit_helper",
    "com.apple.locate",
    "com.apple.nfsconf",
    "com.apple.revisiond",
    "com.apple.smb.preferences",
    "com.apple.unmountassistant.sysagent",
    "com.apple.xsan",
    "com.apple.xscertadmin",
    "com.apple.xscertd",
    "com.apple.xscertd-helper",
  ],
  "🎮 Game Center": [
    "com.apple.gamecontroller.ConfigService",
    "com.apple.gamed",
    "com.apple.GameController.gamecontrolleragentd",
    "com.apple.GameOverlayUI",
    "com.apple.gamesaved",
    "com.apple.GamePolicyAgent",
    "com.apple.GameController.gamecontrollerd",
    "com.apple.fpsd.arcadeservice",
    "com.apple.gamepolicyd",
  ],
  "🔌 Hardware & Drivers": [
    "com.apple.uarpassetmanagerd",
    "com.apple.uarphidd",
    "com.apple.uarpd",
    "com.apple.accessorysensormgrd",
    "com.apple.airportd",
    "com.apple.appleh13camerad",
    "com.apple.appleh16camerad",
    "com.apple.arkitd",
    "com.apple.audio.AudioComponentRegistrar",
    "com.apple.audio.AudioComponentRegistrar.daemon",
    "com.apple.audio.coreaudiod",
    "com.apple.audio.isolated.historicalaudiod",
    "com.apple.audio.isolated.micactivityd",
    "com.apple.audio.micactivityd",
    "com.apple.audio.systemsoundserverd",
    "com.apple.audiomxd",
    "com.apple.cameracaptured",
    "com.apple.centaurid",
    "com.apple.cmio.ContinuityCaptureAgent",
    "com.apple.cmio.registerassistantservice",
    "com.apple.cmio.uvcassistantextension",
    "com.apple.cmio.videodriverkithostextension",
    "com.apple.colorsync.displayservices",
    "com.apple.colorsync.useragent",
    "com.apple.colorsyncd",
    "com.apple.corebrightnessd",
    "com.apple.CSCSupportd",
    "com.apple.ctkd",
    "com.apple.cvmsCompAgent3425AMD_x86_64",
    "com.apple.cvmsCompAgent3425AMD_x86_64_1",
    "com.apple.cvmsCompAgent3600_arm64",
    "com.apple.cvmsCompAgent3600_arm64_1",
    "com.apple.cvmsCompAgent3600_x86_64",
    "com.apple.cvmsCompAgent3600_x86_64_1",
    "com.apple.cvmsCompAgent_arm64",
    "com.apple.cvmsCompAgent_arm64_1",
    "com.apple.cvmsCompAgent_x86_64",
    "com.apple.cvmsCompAgent_x86_64_1",
    "com.apple.deviceinterfaced",
    "com.apple.displaypolicyd",
    "com.apple.ExpansionSlotNotification",
    "com.apple.firmwaresyncd",
    "com.apple.gputoolsserviced",
    "com.apple.hidd",
    "com.apple.icdd",
    "com.apple.ifdreader",
    "com.apple.iomfb_bics_daemon",
    "com.apple.iomfb_fdr_loader",
    "com.apple.kernelmanagerd",
    "com.apple.lightsoutmanagementd",
    "com.apple.MemorySlotNotification",
    "com.apple.MobileAccessoryUpdater.fudHelperAgent",
    "com.apple.mobilerepaird",
    "com.apple.MTLAssetUpgraderD",
    "com.apple.nand.aspcarry",
    "com.apple.nand_task_scheduler",
    "com.apple.preference.displays.MirrorDisplays",
    "com.apple.printtool.agent",
    "com.apple.printuitool.agent",
    "com.apple.remotecompositorclientd",
    "com.apple.retimerd",
    "com.apple.scsid",
    "com.apple.sysextd",
    "com.apple.thermald",
    "com.apple.touchbarserver",
    "com.apple.SafeEjectGPUAgent",
    "com.apple.cmio.LaunchCMIOUserExtensionsAgent",
    "com.apple.uarppersonalizationd",
    "com.apple.usbnotificationagent",
    "com.apple.IOUIAgent",
    "com.apple.midiserver",
    "com.apple.ptpcamerad",
    "com.apple.SafeEjectGPUService",
    "com.apple.AmbientDisplayAgent",
    "com.apple.IOAccelMemoryInfoCollector",
    "com.apple.IOUserBluetoothSerialDriver-0x10000067b",
    "com.apple.IOUserDockChannelSerial-0x100000414",
    "com.apple.KernelEventAgent",
    "com.apple.SafeEjectGPUStartupDaemon",
    "com.apple.accessoryd",
    "com.apple.accessoryupdaterd",
    "com.apple.aned",
    "com.apple.aneuserd",
    "com.apple.aonsensed",
    "com.apple.avbdeviced",
    "com.apple.cmio.VDCAssistant",
    "com.apple.cmio.iOSScreenCaptureAssistant",
    "com.apple.corekdld",
    "com.apple.cvmsServ",
    "com.apple.driverkit.AppleUserHIDDrivers-0x100000463",
    "com.apple.dvdplayback.setregion",
    "com.apple.eoshostd",
    "com.apple.iokit.ioserviceauthorized",
    "com.apple.ionodecache",
    "com.apple.ioupsd",
    "com.apple.kernelmanager_helper",
    "com.apple.liquiddetectiond",
    "com.apple.nfcd",
    "com.apple.oahd",
    "com.apple.oahd-root-helper",
    "com.apple.printtool.daemon",
    "com.apple.thermalmonitord",
    "com.apple.timesync.audioclocksyncd",
    "com.apple.usbaudiod",
    "com.apple.usbpowerd",
    "com.apple.usbsmartcardreaderd",
    "com.apple.videoconference.camera",
    "com.apple.wifiFirmwareLoader",
    "org.cups.cupsd",
    "com.apple.iokit.IOServiceAuthorizeAgent",
    "com.apple.cvmsCompAgent",
  ],
  "🏠 HomeKit": [
    "com.apple.homed",
    "com.apple.homeenergyd",
    "com.apple.homeeventsd",
  ],
  "☁️  iCloud & CloudKit": [
    "com.apple.appleidsetupd",
    "com.apple.bookdatastored",
    "com.apple.cloudd",
    "com.apple.bird",
    "com.apple.cloudphotod",
    "com.apple.contacts.postersyncd",
    "com.apple.FeatureAccessAgent",
    "com.apple.findmy.findmylocateagent",
    "com.apple.icloud.findmydeviced",
    "com.apple.icloud.searchpartyd",
    "com.apple.iCloudNotificationAgent",
    "com.apple.icloudwebd",
    "com.apple.protectedcloudstorage.protectedcloudkeysyncing",
    "com.apple.itunescloudd",
    "com.apple.ckdiscretionaryd",
    "com.apple.AOSPushRelay",
    "com.apple.findmymacmessenger",
    "com.apple.cmfsyncagent",
    "com.apple.CloudPhotosConfiguration",
    "com.apple.icloud.findmydeviced.findmydevice-user-agent",
    "com.apple.AOSHeartbeat",
    "com.apple.cloudsettingssyncagent",
    "com.apple.iCloudHelper",
    "com.apple.iCloudUserNotificationsd",
    "com.apple.privatecloudcomputed",
    "com.apple.cdpd",
    "com.apple.appleaccountd",
    "com.apple.findmy.findmybeaconingd",
    "com.apple.findmymacd",
    "com.apple.icloud.searchpartyuseragent",
    "com.apple.icloud.fmfd",
    "com.apple.icloudmailagent",
    "com.apple.StatusKitAgent",
  ],
  "📦 Installation & Updates": [
    "com.apple.dt.CommandLineTools.installondemand",
    "com.apple.inboxupdaterd",
    "com.apple.installd",
    "com.apple.jetpackassetd",
    "com.apple.package-script-service",
    "com.apple.PackageUIKit.InstallStatus",
    "com.apple.postupgraded",
    "com.apple.softwareupdated",
    "com.apple.mobileassetd",
    "com.apple.mobile.obliteration",
    "com.apple.AssetCache.agent",
    "com.apple.installerauthagent",
    "com.apple.appleseed.seedusaged",
    "com.apple.installd.user",
    "com.apple.SoftwareUpdateNotificationManager",
    "com.apple.suhelperd",
    "com.apple.AssetCacheLocatorService",
    "com.apple.betaenrollmentagent",
    "com.apple.AssetCache.builtin",
    "com.apple.AssetCacheManagerService",
    "com.apple.AssetCacheTetheratorService",
    "com.apple.InstallerDiagnostics.installerdiagd",
    "com.apple.InstallerDiagnostics.installerdiagwatcher",
    "com.apple.InstallerProgress",
    "com.apple.MobileAsset.ManifestStorageService",
    "com.apple.MobileInstallationHelperService",
    "com.apple.MobileSoftwareUpdate.CleanupPreparePathService",
    "com.apple.MobileSoftwareUpdate.CryptegraftService",
    "com.apple.UpdateSettings",
    "com.apple.appleseed.fbahelperd",
    "com.apple.betaenrollmentd",
    "com.apple.bootinstalld",
    "com.apple.bridgeOSUpdateProxy",
    "com.apple.idleassetsd",
    "com.apple.installandsetup.systemmigrationd",
    "com.apple.installcoordination_proxy",
    "com.apple.installcoordinationd",
    "com.apple.mobile.softwareupdated",
    "com.apple.softwareupdate_firstrun_tasks",
    "com.apple.system_installd",
    "com.apple.uninstalld",
    "com.apple.DistributionKit.DistributionHelper",
    "com.apple.installandsetup.migrationhelper.user",
  ],
  "💼 Mgt & Development": [
    "com.apple.CoreDevice.remotepairingd",
    "com.apple.dmd.agent",
    "com.apple.dt.AutomationModeUI",
    "com.apple.dt.previewsd",
    "com.apple.dt.previewsviewservice",
    "com.apple.managedappdistributionagent",
    "com.apple.ManagedClient",
    "com.apple.ManagedClient.startup",
    "com.apple.ManagedClientAgent.enrollagent",
    "com.apple.mdmclient.daemon.runatboot",
    "com.apple.previewshellapp",
    "com.apple.RemoteDesktop",
    "com.apple.RemoteDesktop.agent",
    "com.apple.RemoteManagementAgent",
    "com.apple.RemotePairTool",
    "com.apple.ManagedClientAgent.agent",
    "com.apple.ManagedSettingsAgent",
    "com.apple.ssinvitationagent",
    "com.apple.swiftuitraced",
    "com.apple.testmanagerd",
    "com.apple.mdmclient.agent",
    "com.apple.dmd",
    "com.apple.studentd",
    "com.apple.remotemanagementd",
    "com.apple.ManagedClient.enroll",
    "com.apple.ManagedClient.mechanism",
    "com.apple.RemoteDesktop.PrivilegeProxy",
    "com.apple.devicemanagementclient.managedeventsd",
    "com.apple.devicemanagementclient.teslad",
    "com.apple.dt.RemotePairingDataVaultHelper",
    "com.apple.dt.automationmode-writer",
    "com.apple.dt.fetchsymbolsd",
    "com.apple.managedappdistributiond",
    "com.apple.mdmclient.daemon",
    "com.apple.swiftuitracingsupport.xpc",
    "com.apple.testmanagerd.remote",
  ],
  "🌐 Networking": [
    "com.apple.AirPortBaseStationAgent",
    "com.apple.bootpd",
    "com.apple.cfnetwork.AuthBrokerAgent",
    "com.apple.dhcp6d",
    "com.apple.ftp",
    "com.apple.ftp-proxy",
    "com.apple.getty",
    "com.apple.mDNSResponder",
    "com.apple.configd",
    "com.apple.mDNSResponderHelper",
    "com.apple.msrpc.echosvc",
    "com.apple.netauth.user.auth",
    "com.apple.netauth.user.gui",
    "com.apple.odproxyd",
    "com.apple.screensharing.agent",
    "com.apple.screensharing.menuextra",
    "com.apple.screensharing.MessagesAgent",
    "com.apple.sharingd",
    "com.apple.screensharing",
    "com.apple.netbiosd",
    "com.apple.nesessionmanager",
    "com.apple.apsd",
    "com.apple.nsurlsessiond",
    "com.apple.networkserviceproxy",
    "com.apple.neagent",
    "com.apple.captiveagent",
    "com.apple.intelligentroutingd",
    "com.apple.NetworkSharing",
    "com.apple.RFBEventHelper",
    "com.apple.SCHelper",
    "com.apple.sntpd",
    "com.apple.uucp",
    "com.apple.wifi.WiFiAgent",
    "com.apple.WirelessRadioManager",
    "com.apple.cfnetwork.cfnetworkagent",
    "com.apple.dpdkswitchd",
    "com.apple.eapolcfg_auth",
    "com.apple.mDNSResponder.reloaded",
    "com.apple.mDNSResponderHelper.reloaded",
    "com.apple.msrpc.lsarpc",
    "com.apple.msrpc.mdssvc",
    "com.apple.msrpc.netlogon",
    "com.apple.msrpc.srvsvc",
    "com.apple.msrpc.wkssvc",
    "com.apple.nehelper",
    "com.apple.netauth.sys.auth",
    "com.apple.netauth.sys.gui",
    "com.apple.nlcd",
    "com.apple.nsurlsessiond_privileged",
    "com.apple.pcapd",
    "com.apple.pfctl",
    "com.apple.postfix.master",
    "com.apple.postfix.newaliases",
    "com.apple.racoon",
    "com.apple.rpcbind",
    "com.apple.srp-mdns-proxy",
    "com.apple.statd.notify",
    "com.apple.threadradiod",
    "com.apple.wifip2pd",
    "com.apple.wifivelocityd",
    "com.openssh.ssh-agent",
    "com.apple.ntalkd",
    "org.apache.httpd",
    "org.cups.cups-lpd",
    "org.net-snmp.snmpd",
    "org.openldap.slapd",
    "com.openssh.sshd",
    "com.apple.tftpd",
  ],
  "🗺️  Maps & Location": [
    "com.apple.CoreLocationAgent",
    "com.apple.geodMachServiceBridge",
    "com.apple.locationd",
    "com.apple.geod",
    "com.apple.Maps.mapssyncd",
    "com.apple.routined",
    "com.apple.Maps.mapspushd",
    "com.apple.countryd",
    "com.apple.navd",
    "com.apple.maps.destinationd",
    "com.apple.CoreRoutine.helperservice"
  ],
  "⚡️ Power Management": [
    "com.apple.powerchime",
      "com.apple.powerd",
      "com.apple.PerfPowerServices",
      "com.apple.PerfPowerServicesExtended",
      "com.apple.PowerUIAgent",
      "com.apple.peakpowermanagerd",
      "com.apple.powerexperienced",
  ],
  "🖼️  Photos & Media": [
    "com.apple.avatarsd",
    "com.apple.MENotificationAgent",
    "com.apple.mobiletimerd",
    "com.apple.photoanalysisd",
    "com.apple.photolibraryd",
    "com.apple.mediaanalysisd",
    "com.apple.mediastream.mstreamd",
    "com.apple.AMPArtworkAgent",
    "com.apple.avconferenced",
    "com.apple.amp.mediasharingd",
    "com.apple.AMPLibraryAgent",
    "com.apple.replayd",
    "com.apple.sociallayerd",
    "com.apple.sportsd",
    "com.apple.stickersd",
    "com.apple.tonelibraryd",
    "com.apple.rcd",
    "com.apple.musicd",
    "com.apple.voicememod",
  ],
  "🧠 Proactive & Intelligence": [
    "com.apple.triald.system",
    "com.apple.triald",
    "com.apple.ciphermld",
    "com.apple.contacts.donation-agent",
    "com.apple.corespotlightd",
    "com.apple.corespotlightservice",
    "com.apple.intelligencetasksd",
    "com.apple.managedcorespotlightd",
    "com.apple.mdworker.application",
    "com.apple.mdworker.single.arm64",
    "com.apple.mdworker.single.x86_64",
    "com.apple.mdworker.sizing",
    "com.apple.milod",
    "com.apple.mlhostd",
    "com.apple.mlruntimed",
    "com.apple.ModelCatalogAgent",
    "com.apple.peopled",
    "com.apple.proactived",
    "com.apple.reversetemplated",
    "com.apple.searchtoold",
    "com.apple.siriinferenced",
    "com.apple.spotlightknowledged.importer",
    "com.apple.spotlightknowledged.updater",
    "com.apple.suggestd",
    "com.apple.parsecd",
    "com.apple.intelligenceplatformd",
    "com.apple.knowledge-agent",
    "com.apple.BiomeAgent",
    "com.apple.coreduetd",
    "com.apple.proactiveeventtrackerd",
    "com.apple.spotlightknowledged",
    "com.apple.callintelligenced",
    "com.apple.synapse.contentlinkingd",
    "com.apple.attentionawarenessd",
    "com.apple.contextstored",
    "com.apple.modelcatalogd",
    "com.apple.modelmanagerd",
    "com.apple.ospredictiond",
    "com.apple.duetexpertd",
    "com.apple.generativeexperiencesd",
    "com.apple.intelligenceflowd",
    "com.apple.knowledgeconstructiond",
    "com.apple.ContextStoreAgent",
    "com.apple.intelligencecontextd",
    "com.apple.biomesyncd",
  ],
  "🌐 Safari & WebKit": [
    "com.apple.Safari.SafeBrowsing.Service",
    "com.apple.SafariHistoryServiceAgent",
    "com.apple.SafariBookmarksSyncAgent",
    "com.apple.Safari.PasswordBreachAgent",
    "com.apple.SafariNotificationAgent",
    "com.apple.SafariLaunchAgent",
    "com.apple.Safari.History",
    "com.apple.webkit.webpushd",
    "com.apple.webprivacyd",
    "com.apple.webinspectord",
    "com.apple.swcd",
  ],
  "🔒 Security & Keychain": [
    "com.apple.appleaccounttransparencyd",
    "com.apple.auditd",
    "com.apple.AuthenticationServicesCore.AuthenticationServicesAgent",
    "com.apple.AutoFillPanel",
    "com.apple.communicationtrustd",
    "com.apple.coreidvd",
    "com.apple.CryptoTokenKit.ahp.agent",
    "com.apple.EscrowSecurityAlert",
    "com.apple.filevaultd",
    "com.apple.LocalAuthentication.userauthd",
    "com.apple.locationaccessstored",
    "com.apple.lockoutagent",
    "com.apple.PasswordService",
    "com.apple.prngseedd",
    "com.apple.scopedbookmarksagent.xpc",
    "com.apple.securemessagingagent",
    "com.apple.security.DiskUnmountWatcher",
    "com.apple.security.FDERecoveryAgent",
    "com.apple.security.XPCKeychainSandboxCheck",
    "com.apple.security.XPCTimeStampingService",
    "com.apple.security.xprotectd",
    "com.apple.securityd",
    "com.apple.securityuploadd",
    "com.apple.seserviced",
    "com.apple.swtransparencyd",
    "com.apple.tccd",
    "com.apple.syspolicyd",
    "com.apple.authd",
    "com.apple.cryptexd",
    "com.apple.lockd",
    "com.apple.devicecheckd",
    "com.apple.MRTa",
    "com.apple.transparencyd",
    "com.apple.transparencyStaticKey",
    "com.apple.trustd.agent",
    "com.apple.TrustedPeersHelper",
    "com.apple.TrustEvaluationAgent",
    "com.apple.XProtect.agent.scan.startup",
    "com.apple.XprotectFramework.PluginService",
    "com.apple.LocalAuthentication.UIAgent",
    "com.apple.security.KeychainStasher",
    "com.apple.secinitd",
    "com.apple.ctkbind",
    "com.apple.alf.useragent",
    "com.apple.lockdownmoded",
    "com.apple.XProtect.agent.scan",
    "com.apple.SecureBackupDaemon",
    "com.apple.security.agent",
    "com.apple.secd",
    "com.apple.akd",
    "com.apple.AppSSOAgent",
    "com.apple.CoreAuthentication.agent",
    "com.apple.keychainsharingmessagingd",
    "com.apple.security.keychain-circle-notification",
    "com.apple.frauddefensed",
    "com.apple.AppSSOAgent.login",
    "com.apple.AppSSODaemon",
    "com.apple.AppleCredentialManagerDaemon",
    "com.apple.CodeSigningHelper",
    "com.apple.CoreAuthentication.daemon",
    "com.apple.CryptoTokenKit.ahp",
    "com.apple.GSSCred",
    "com.apple.Kerberos.digest-service",
    "com.apple.Kerberos.kadmind",
    "com.apple.Kerberos.kcm",
    "com.apple.Kerberos.kdc",
    "com.apple.Kerberos.kpasswdd",
    "com.apple.MRTd",
    "com.apple.MobileFileIntegrity",
    "com.apple.TrustEvaluationAgent.system",
    "com.apple.XProtect.daemon.scan",
    "com.apple.XProtect.daemon.scan.startup",
    "com.apple.alf",
    "com.apple.alwaysonexclavesd",
    "com.apple.applekeystored",
    "com.apple.biomed",
    "com.apple.biometrickitd",
    "com.apple.configureLocalKDC",
    "com.apple.csrutil.report",
    "com.apple.endpointsecurity.endpointsecurityd",
    "com.apple.gkreport",
    "com.apple.gssd",
    "com.apple.kcproxy",
    "com.apple.kuncd",
    "com.apple.mobile.keybagd",
    "com.apple.ocspd",
    "com.apple.online-auth-agent.xpc",
    "com.apple.sandboxd",
    "com.apple.security.agent.login",
    "com.apple.security.agent.login.00000000-0000-0000-0000-0000000186A1",
    "com.apple.security.authhost",
    "com.apple.security.authhost.00000000-0000-0000-0000-0000000186A1",
    "com.apple.security.authtrampoline",
    "com.apple.security.cryptexd",
    "com.apple.security.syspolicy",
    "com.apple.securityd.system",
    "com.apple.systemkeychain",
    "com.apple.taskgated",
    "com.apple.taskgated-helper",
    "com.apple.tccd.system",
    "com.apple.trustd",
    "com.apple.trustdFileHelper",
    "com.apple.xpc.roleaccountd",
    "com.apple.security.cloudkeychainproxy3",
  ],
  "🗣️  Siri & Dictation": [
    "com.apple.assistant_cdmd",
    "com.apple.assistantd",
    "com.apple.corespeechd",
    "com.apple.siriknowledged",
    "com.apple.Siri.agent",
    "com.apple.shazamd",
    "com.apple.speech.speechsynthesisd.arm64",
    "com.apple.speech.speechsynthesisd.x86_64",
    "com.apple.speech.synthesisserver",
    "com.apple.speech.speechdatainstallerd",
    "com.apple.DictationIM",
    "com.apple.corespeechd_system",
    "com.apple.siri.acousticsignature",
    "com.apple.assistant_service",
    "com.apple.siriactionsd",
    "com.apple.SiriTTSTrainingAgent",
    "com.apple.sirittsd",
    "com.apple.siri.context.service",
    "com.apple.speech.speechsynthesisd",
    "com.apple.SpeechRecognitionCore.brokerd",
  ],
  "⚙️  System Core": [
    "com.apple.accounts.dom",
    "com.apple.AddressBook.abd",
    "com.apple.AddressBook.AssistantService",
    "com.apple.atrun",
    "com.apple.coredatad",
    "com.apple.coreservicesd",
    "com.apple.csuseragent",
    "com.apple.datastored",
    "com.apple.AEServer",
    "com.apple.email.maild",
    "com.apple.jetsamproperties.Mac",
    "com.apple.kcgend",
    "com.apple.linkd",
    "com.apple.loginwindow.LWWeeklyMessageTracer",
    "com.apple.MailServiceAgent",
    "com.apple.Notes.datastore",
    "com.apple.pluginkit.pkreporter",
    "com.apple.runningboardd",
    "com.apple.lsd",
    "com.apple.loginwindow",
    "com.apple.logind",
    "com.apple.opendirectoryd",
    "com.apple.notifyd",
    "com.apple.distnoted",
    "com.apple.cfprefsd",
    "com.apple.contactsd",
    "com.apple.syncdefaultsd",
    "com.apple.syncservices.SyncServer",
    "com.apple.systemsettingsagent",
    "com.apple.toolkitd",
    "com.apple.uikitsystemapp",
    "com.apple.UserEventAgent-CryptexContainer",
    "com.apple.UserEventAgent-LoginWindow",
    "com.apple.usernoted",
    "com.apple.usernotificationsd",
    "com.apple.warmd_agent",
    "com.apple.xpc.smd",
    "com.apple.mds",
    "com.apple.timed",
    "com.apple.deleted_helper",
    "com.apple.recentsd",
    "com.apple.xpc.otherbsd",
    "com.apple.timezoneupdates.tznotify",
    "com.apple.cfprefsd.xpc.agent",
    "com.apple.xpc.loginitemregisterd",
    "com.apple.coreservices.useractivityd",
    "com.apple.cache_delete",
    "com.apple.UserEventAgent-Aqua",
    "com.apple.backgroundtaskmanagement.agent",
    "com.apple.coreservices.sharedfilelistd",
    "com.apple.containermanagerd",
    "com.apple.accountsd",
    "com.apple.coreservices.uiagent",
    "com.apple.distnoted.xpc.agent",
    "com.apple.AppleQEMUGuestAgent",
    "com.apple.ContainerMigrationService",
    "com.apple.DASDelegateService",
    "com.apple.UserEventAgent-System",
    "com.apple.Virtualization.AppleVirtualPlatformHIDBridge",
    "com.apple.backgroundtaskmanagementd",
    "com.apple.bsd.dirhelper",
    "com.apple.cfprefsd.xpc.daemon",
    "com.apple.containermanagerd.system",
    "com.apple.corerepaird",
    "com.apple.coreservices.appleevents",
    "com.apple.coreservices.launchservicesd",
    "com.apple.dasd",
    "com.apple.devicerecoveryd",
    "com.apple.distnoted.xpc.daemon",
    "com.apple.dspluginhelperd",
    "com.apple.dynamic_pager",
    "com.apple.efilogin-helper",
    "com.apple.erasecontentsettingshelperd",
    "com.apple.loginwindow.E4B99820-2E63-4075-99ED-7E1B4FCAC597",
    "com.apple.memory-maintenance",
    "com.apple.metadata.mds",
    "com.apple.metadata.mds.index",
    "com.apple.metadata.mds.index.readonly",
    "com.apple.metadata.mds.scan",
    "com.apple.metadata.mds.spindump",
    "com.apple.misagent",
    "com.apple.mobile.storage_mounter",
    "com.apple.mobile.storage_mounter_proxy",
    "com.apple.mobile.usermanagerd",
    "com.apple.mobileactivationd",
    "com.apple.mobilegestalt.xpc",
    "com.apple.preferences.timezone.admintool",
    "com.apple.recoveryos-lockout-service",
    "com.apple.sessionlogoutd",
    "com.apple.startupdiskhelper",
    "com.apple.sysmond",
    "com.apple.systemadministration.writeconfig",
    "com.apple.systempreferences.cacheAssistant",
    "com.apple.timezoneupdates.tzd",
    "com.apple.tmp_cleaner",
    "com.apple.tzlinkd",
    "com.apple.warmd",
    "com.apple.watchdogd",
    "com.apple.xtyped",
    "com.vix.cron",
    "com.apple.helpd",
    "com.apple.hiservices-xpcservice",
    "com.apple.mdworker.mail",
    "com.apple.mdworker.shared",
    "com.apple.mdworker.single",
    "com.apple.metadata.mdbulkimport",
    "com.apple.pluginkit.pkd",
    "com.apple.usermanagerhelper",
    "com.apple.WorkflowKit.ShortcutsViewService",
    "com.apple.metadata.mdflagwriter"
  ],
  "✍️  Text & Input": [
    "com.apple.CharacterPicker.FileService",
    "com.apple.CharacterPicker.RemoteGenerationViewService",
    "com.apple.DataDetectorsLocalSources",
    "com.apple.fontd.useragent",
    "com.apple.FontRegistryUIAgent",
    "com.apple.FontValidator",
    "com.apple.naturallanguaged",
    "com.apple.languaged",
    "com.apple.applespell",
    "com.apple.FontWorker",
    "com.apple.localizationswitcherd",
    "com.apple.languageassetd",
    "com.apple.textcomposerd",
    "com.apple.TextInputMenuAgent",
    "com.apple.keyboardservicesd",
    "com.apple.ATS.FontValidator",
    "com.apple.TextInputSwitcher",
    "com.apple.imklaunchagent",
    "com.apple.textunderstandingd",
    "com.apple.DataDetectorsSourceAccess",
    "com.apple.fontmover",
    "com.apple.handwritingd",
    "com.apple.DictionaryServiceHelper",
    "com.apple.translationd",
  ],
  "🧩 Third-Party": [
    "com.appfactory.core",
    "com.google.GoogleUpdater.wake.system",
    "com.google.keystone.agent",
    "com.google.keystone.daemon",
    "com.google.keystone.user.agent",
    "com.google.keystone.user.xpcservice",
    "com.docker.helper",
    "com.docker.socket",
    "com.docker.vmnetd",
    "com.adobe.GC.AGM",
    "com.adobe.GC.Scheduler-1.0",
    "Adobe_Genuine_Software_Integrity_Service",
    "com.google.keystone.xpcservice",
    "com.microsoft.update.agent",
    "com.microsoft.autoupdate.helper",
    "com.1password.1password-launcher",
    "2BUA8C4S2C.com.agilebits.onepassword7-helper",
    "com.macpaw.CleanMyMac-setapp.HealthMonitor",
    "com.postgresapp.Postgres2LoginHelper",
    "com.figma.daemon",
    "homebrew.mxcl.redis",
    "us.zoom.updater",
    "us.zoom.updater.login.check",
    "us.zoom.ZoomDaemon",
  ],
  "🖥️  User Interface & Windowing": [
    "com.apple.appkit.xpc.ColorSampler",
    "com.apple.AquaAppearanceHelper",
    "com.apple.AquaAppearanceHelper.agent",
    "com.apple.Dock",
    "com.apple.FolderActionsDispatcher",
    "com.apple.FollowUpUI",
    "com.apple.LinkedNotesUIService",
    "com.apple.liveactivitiesd",
    "com.apple.menuextra.battery.helper",
    "com.apple.notificationcenterui",
    "com.apple.nowplayingtouchui",
    "com.apple.OSDUIHelper",
    "com.apple.PIPAgent",
    "com.apple.PosterBoard",
    "com.apple.quicklook.ui.helper",
    "com.apple.screencaptureui.agent",
    "com.apple.ScriptMenuApp",
    "com.apple.ServicesUIAgent",
    "com.apple.SpacesTouchBarAgent.app",
    "com.apple.Spotlight",
    "com.apple.SystemUIServer",
    "com.apple.TextInputUI.xpc.CursorUIViewService",
    "com.apple.UserNotificationCenterAgent-LoginWindow",
    "com.apple.wallpaper",
    "com.apple.WindowManager",
    "com.apple.WindowServer",
    "com.apple.Dock.agent",
    "com.apple.SystemUIServer.agent",
    "com.apple.quicklook.ThumbnailsAgent",
    "com.apple.quicklook",
    "com.apple.donotdisturbd",
    "com.apple.chronod",
    "com.apple.AirPlayXPCHelper",
    "com.apple.mediaremoted",
    "com.apple.MENotificationService",
    "com.apple.Finder",
    "com.apple.mediaremoteagent",
    "com.apple.iconservices.iconservicesagent",
    "com.apple.wallpaper.agent",
    "com.apple.UserPictureSyncAgent",
    "com.apple.WindowManager.agent",
    "com.apple.noticeboard.agent",
    "com.apple.UserNotificationCenterAgent",
    "com.apple.controlcenter",
    "com.apple.talagent",
    "com.apple.carboncore.csnameddata",
    "com.apple.controlstrip",
    "com.apple.pbs",
    "com.apple.AirPlayUIAgent",
    "com.apple.notificationcenterui.agent",
    "com.apple.DesktopServicesHelper",
    "com.apple.UserNotificationCenter",
    "com.apple.iconservices.iconservicesd",
    "com.apple.mobile.notification_proxy",
    "com.apple.noticeboard.state",
    "com.apple.wallpaper.export",
    "com.apple.progressd",
    "com.apple.tipsd",
    "com.apple.MessageUIMacHelperService",
    "com.apple.ViewBridgeAuxiliary",
    "com.apple.screencaptureui"
  ],
  "☀️  Weather": [
    "com.apple.weatherd",
    "com.apple.weather.menu",
  ],
  "❓ Undocumented": [
    "com.apple.ctcategories.service",
     "com.apple.IFCStart", 
     "com.apple.corercd", 
     "com.apple.filesystems.doubleagentd",
     "com.apple.griddatad",
     "com.apple.internal.aupbregistrarservice",
     "com.apple.lskdd",
     "com.apple.multiversed",
     "com.apple.pfd",
     "com.apple.powerd.swd",
     "com.apple.relatived",
     "com.apple.systemstatusd",
     "com.apple.tracd",
     "com.apple.ucupdate.plist",
     "com.apple.xartstorageremoted",
     "com.apple.xpc.uscwoap",
     "com.apple.mobile.NRDUpdated",
     "com.apple.replicatord",
  ]
}

# Sources checked against the installed macOS manuals/configuration on 2026-11-10.
# Impact statements remain estimates unless the source explicitly documents them.
METADATA_SOURCES = {
    "com.apple.triald": "/System/Library/LaunchAgents/com.apple.triald.plist (Trial activities)",
    "com.apple.triald.system": "/System/Library/LaunchDaemons/com.apple.triald.system.plist (program identity)",
    "com.apple.DwellControl": "https://support.apple.com/guide/mac-help/mchl437b47b0/mac (Dwell feature)",
    "com.apple.watchlistd": "man 8 watchlistd",
    "com.apple.uarpd": "man 8 uarpd",
    "com.apple.uarphidd": "/System/Library/LaunchDaemons/com.apple.uarphidd.plist (program identity)",
    "com.apple.uarpassetmanagerd": "/System/Library/LaunchDaemons/com.apple.uarpassetmanagerd.plist (program identity)",
}

# --- Live Data Functions ---

def get_uid() -> int:
    """Gets the UID of the current user, accounting for sudo."""
    # When running with sudo, we want the original user's UID, not root's
    if 'SUDO_UID' in os.environ:
        return int(os.environ['SUDO_UID'])
    return os.getuid()

def service_rows(output: str) -> Dict[str, str]:
    """Read only the launchctl services table, never endpoints or other tables."""
    match = re.search(r"^\s*services = \{\s*$(.*?)^\s*\}", output, re.MULTILINE | re.DOTALL)
    if not match:
        return {}
    return {row.group(2): row.group(1) for row in re.finditer(
        r"^\s*(\d+|-)\s+[-\d]+\s+(\S+)\s*$", match.group(1), re.MULTILINE)}


def parse_launchctl_print_output(output: str) -> Tuple[set, Dict[str, str]]:
    """Read loaded labels and persistent overrides, including override-only labels."""
    names = set(service_rows(output))
    states = {}
    block = re.search(r"disabled services = \{([^}]*)\}", output, re.DOTALL)
    if block:
        for name, status in re.findall(r'"([^"\n]+)"\s*=>\s*(enabled|disabled|true|false)', block.group(1)):
            states[name] = "disabled" if status in ("disabled", "true") else "enabled"
    return names | set(states), states


def read_service_definitions(directories) -> Dict[str, Dict]:
    """Read configuration evidence; a plist alone does not prove a loaded job."""
    definitions = {}
    for directory in directories:
        try:
            paths = sorted(Path(directory).glob("*.plist"))
        except OSError:
            continue
        for path in paths:
            try:
                data = plistlib.loads(path.read_bytes())
                if not isinstance(data, dict) or not isinstance(data.get("Label"), str):
                    continue
                args = data.get("ProgramArguments")
                program = data.get("Program") or (args[0] if isinstance(args, list) and args else "")
                definitions[data["Label"]] = {
                    "plist_path": str(path), "program": str(program),
                    "default_disabled": data.get("Disabled", False) if isinstance(data.get("Disabled", False), bool) else None,
                }
            except (OSError, ValueError, TypeError, plistlib.InvalidFileException, ExpatError):
                continue
    return definitions


def get_service_details(service_name: str, service_type: str, statuses: Dict[str, str],
                        pids: Dict[str, str], *, loaded=True, default_disabled=None,
                        overrides_known=True) -> Dict:
    """Keep runtime state, launch policy, and metadata confidence separate."""
    if service_name in statuses:
        enabled_status = statuses[service_name]
        policy_source = "Saved launchctl override"
    elif not overrides_known or default_disabled is None:
        enabled_status = "unknown"
        policy_source = "No verified launch policy"
    else:
        enabled_status = "disabled" if default_disabled else "enabled"
        policy_source = "Plist default (no saved override)"
    status = ("running" if service_name in pids else
              "disabled" if enabled_status == "disabled" else
              "loaded" if loaded else "not loaded")
    stored = SERVICE_DATABASE.get(service_name)
    return {
        "status": status, "enabled_status": enabled_status,
        "loaded": loaded, "pid": pids.get(service_name),
        "policy_source": policy_source,
        "description": stored["description"] if stored else "No verified description is available for this service.",
        "impact": stored["impact"] if stored else "The effects of disabling this service have not been verified.",
        "metadata_source": METADATA_SOURCES.get(service_name) or (
            "Historical local database; description and impact not independently verified" if stored else
            "No checked source available"),
        "type": service_type,
    }


def get_live_services(console: Console) -> Dict[str, Dict[str, Dict]]:
    """Connects to the system to get a list of all services, their status, and categorizes them."""
    # Ensure all possible categories are initialized
    categorized_services = OrderedDict((category, {}) for category in CATEGORIZATION_MAP.keys())
    categorized_services["🧩 Third-Party"] = {}
    categorized_services["❓ Undocumented"] = {}

    uid = get_uid()
    discovered = {}
    try:
        home = Path(pwd.getpwuid(uid).pw_dir)
    except KeyError:
        home = None
    daemon_definitions = read_service_definitions([
        "/System/Library/LaunchDaemons", "/Library/LaunchDaemons"])
    agent_definitions = read_service_definitions([
        "/System/Library/LaunchAgents", "/Library/LaunchAgents",
        *([home / "Library/LaunchAgents"] if home else [])])
    for domain in ("system", f"gui/{uid}", f"user/{uid}"):
        prefix = []  # Reading launchd domains does not require sudo.
        try:
            result = subprocess.run(prefix + ["launchctl", "print", domain],
                                    capture_output=True, text=True)
            if result.returncode:
                console.print(Text(f"Could not read {domain}: {result.stderr.strip()}", style="yellow"))
                continue
            names, statuses = parse_launchctl_print_output(result.stdout)
            rows = service_rows(result.stdout)
            pids = {name: pid for name, pid in rows.items() if pid.isdigit() and int(pid) > 0}
            overrides = subprocess.run(prefix + ["launchctl", "print-disabled", domain],
                                       capture_output=True, text=True)
            if overrides.returncode:
                console.print(Text(f"Could not read overrides for {domain}: {overrides.stderr.strip()}", style="yellow"))
            else:
                override_names, states = parse_launchctl_print_output(overrides.stdout)
                names.update(override_names)
                statuses.update(states)
            for name in sorted(names):
                definitions = daemon_definitions if domain == "system" else agent_definitions if domain.startswith("gui/") else {}
                definition = definitions.get(name, {})
                details = get_service_details(
                    name, "daemon" if domain == "system" else "agent", statuses, pids,
                    loaded=name in rows, default_disabled=definition.get("default_disabled"),
                    overrides_known=overrides.returncode == 0)
                details.update(domain=domain, label=name, **definition)
                discovered.setdefault(name, []).append(details)
        except OSError as error:
            console.print(Text(f"Could not read {domain}: {error}", style="yellow"))
    for name, instances in sorted(discovered.items()):
        for details in instances:
            # Keep identical labels in separate domains independently actionable.
            key = name if len(instances) == 1 else f"{name} ({details['domain']})"
            categorized_services[categorize_service(name)][key] = details
    return OrderedDict((cat, services) for cat, services in categorized_services.items() if services)

def categorize_service(service_name: str) -> str:
    """Categorizes a service based on the CATEGORIZATION_MAP."""
    for category, service_list in CATEGORIZATION_MAP.items():
        if service_name in service_list:
            return category
    if not service_name.startswith(("com.apple.", "application.com.apple.")):
        return "🧩 Third-Party"
    return "❓ Undocumented"

def set_service_enabled(service, domain, enabled):
    """Apply an override in the discovered domain and verify the actual result."""
    prefix = ["sudo", "-n"] if domain == "system" and os.geteuid() != 0 else []
    target = f"{domain}/{service}"

    def run(action, argument):
        return subprocess.run(prefix + ["launchctl", action, argument], capture_output=True, text=True)

    try:
        # Prevent demand/KeepAlive relaunch before removing the loaded job.
        action = "enable" if enabled else "disable"
        result = run(action, target)
        if result.returncode:
            return False, f"{action} {target}: {result.stderr.strip() or result.stdout.strip()} (exit {result.returncode})"
        bootout = None if enabled else run("bootout", target)
        overrides = run("print-disabled", domain)
        if overrides.returncode:
            return False, f"Cannot verify override: {overrides.stderr.strip()}"
        _, states = parse_launchctl_print_output("disabled services = {" + overrides.stdout + "}")
        expected = "enabled" if enabled else "disabled"
        if states.get(service) != expected:
            return False, f"{target} is not verified as {expected}."
        if not enabled:
            loaded = run("print", target)
            # ESRCH (113) and launchctl's exact missing-service diagnostic distinguish
            # an unloaded job from a permission or domain lookup failure.
            missing = loaded.returncode == 113 and "Could not find service" in loaded.stderr
            if not missing:
                detail = "Service is still loaded." if loaded.returncode == 0 else loaded.stderr.strip()
                if bootout.returncode:
                    detail += f" bootout: {bootout.stderr.strip()} (exit {bootout.returncode})"
                return False, detail
        return True, ""
    except OSError as error:
        return False, str(error)


def bootout_and_disable(service, uid):
    return set_service_enabled(service, f"gui/{uid}", False)


def bootout_and_disable_system_daemon(service):
    return set_service_enabled(service, "system", False)


class ServiceManagerTUI:
    """A terminal UI application for managing macOS services."""

    def __init__(self, services_data: Dict):
        self.console = Console()
        self.services_data = services_data
        self.categories = list(self.services_data.keys())
        self.active_category_index = 0
        self.active_service_index = 0
        self.view_mode = "categories"
        self.exit_app = False
        self.category_scroll_offset = 0
        self.service_scroll_offset = 0
        self.uid = get_uid()
        # Define the sort order for statuses
        self.status_sort_order = {"running": 0, "loaded": 1, "enabled": 1, "not loaded": 2, "disabled": 3}

    @property
    def viewport_height(self) -> int:
        try:
            return max(1, self.console.height - 10)
        except Exception:
            return 15

    def _adjust_viewport(self, list_type: str):
        if list_type == 'category':
            active_index, offset_attr, total_items = self.active_category_index, 'category_scroll_offset', len(self.categories)
        else:
            active_index, offset_attr, total_items = self.active_service_index, 'service_scroll_offset', len(self.get_current_services())
        
        viewport_height = self.viewport_height
        current_offset = getattr(self, offset_attr)

        if active_index < current_offset:
            setattr(self, offset_attr, active_index)
        elif active_index >= current_offset + viewport_height:
            setattr(self, offset_attr, active_index - viewport_height + 1)
        
        if total_items <= viewport_height:
            setattr(self, offset_attr, 0)

    def get_current_services(self) -> List[str]:
        """Returns the list of services in the active category, sorted by status then name."""
        if not self.categories or self.active_category_index >= len(self.categories):
            return []
        category_name = self.categories[self.active_category_index]
        services_in_cat = self.services_data.get(category_name, {})
        
        # Sort using the new 3-tier status logic
        return sorted(
            services_in_cat.keys(),
            key=lambda s: (self.status_sort_order.get(services_in_cat[s]['status'], 99), s)
        )

    def read_key(self) -> str:
        # (Same as previous version)
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            char = sys.stdin.read(1)
            if char == '\x1b':
                seq = sys.stdin.read(2)
                if seq == '[A': return "up"
                if seq == '[B': return "down"
                if seq == '[D': return "left"
                if seq == '[C': return "right"
            if char in ['\r', '\n']: return "enter"
            return char
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def handle_input(self, key: str):
        # (Same as previous version, but now interacts with sorted list)
        if key == "q":
            self.exit_app = True
            return

        if self.view_mode == "categories":
            if key == "up": self.active_category_index = max(0, self.active_category_index - 1)
            elif key == "down": self.active_category_index = min(len(self.categories) - 1, self.active_category_index + 1)
            elif key == "enter":
                if self.get_current_services():
                    self.view_mode = "services"
                    self.active_service_index = 0
            self._adjust_viewport('category')
        
        elif self.view_mode == "services":
            current_services = self.get_current_services()
            if key in ["b", "left"]: self.view_mode = "categories"
            elif key == "up": self.active_service_index = max(0, self.active_service_index - 1)
            elif key == "down":
                if current_services: self.active_service_index = min(len(current_services) - 1, self.active_service_index + 1)
            elif key == " ":
                if current_services:
                    service_name = current_services[self.active_service_index]
                    category_name = self.categories[self.active_category_index]
                    info = self.services_data[category_name][service_name]
                    # Toggle logic remains simple: if it's disabled, set pending to enabled, otherwise set to disabled.
                    current_status = info.get("pending_status", info.get("enabled_status", info["status"]))
                    info["pending_status"] = "enabled" if current_status == "disabled" else "disabled"
            elif key == "enter": return "apply"
            self._adjust_viewport('service')

    def draw_layout(self) -> Panel:
        # (Same as previous version)
        layout = Layout()
        layout.split(Layout(self.draw_header(), size=3), Layout(name="main"), Layout(self.draw_footer(), size=3))
        main_view = Layout()
        main_view.split_row(self.draw_service_list() if self.view_mode == "services" else self.draw_category_list(), self.draw_details_view())
        layout["main"].update(main_view)
        return Panel(layout, border_style="dim")

    def draw_header(self) -> Panel:
        # (Same as previous version)
        return Panel(Text("macOS Service Manager", justify="center"), style="bold white on blue")

    def draw_footer(self) -> Panel:
        # (Same as previous version)
        if self.view_mode == "categories": instructions = "[b]↑/↓[/b]: Navigate | [b]Enter[/b]: Select | [b]Q[/b]: Quit"
        else: instructions = "[b]↑/↓[/b]: Navigate | [b]Space[/b]: Toggle | [b]Enter[/b]: Apply Changes | [b]←/B[/b]: Back"
        return Panel(Text.from_markup(instructions, justify="center"), title="Controls")

    def draw_category_list(self) -> Panel:
        # (Same as previous version)
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column()
        available_height = self.viewport_height
        start, end = self.category_scroll_offset, min(self.category_scroll_offset + available_height, len(self.categories))
        for i in range(start, end):
            category, count = self.categories[i], len(self.services_data.get(self.categories[i], {}))
            style = "black on green" if i == self.active_category_index else ""
            table.add_row(Text(f"{category} ({count})", style=style))
        return Panel(table, title="Categories", border_style="blue")

    def draw_service_list(self) -> Panel:
        """Draws the list of services with 3-tier status icons."""
        services = self.get_current_services()
        category_name = self.categories[self.active_category_index]
        table = Table(show_header=False, box=None, padding=(0, 0), show_edge=False)
        table.add_column(width=3)  # For icon
        table.add_column()  # For name

        available_height = self.viewport_height
        start = self.service_scroll_offset
        end = min(start + available_height, len(services))

        for i in range(start, end):
            name = services[i]
            info = self.services_data[category_name][name]
            display_status = info["status"]
            
            if "pending_status" in info and info["pending_status"] != info.get("enabled_status", info["status"]):
                status_icon, status_style = "🔄", "yellow"
            elif display_status == "running":
                status_icon, status_style = "🟢", "green"
            elif display_status in ("enabled", "loaded"):
                status_icon, status_style = "🟡", "green"
            elif display_status == "disabled":
                status_icon, status_style = "🔴", "red"
            else:
                status_icon, status_style = "⚪", "dim"

            style = "black on yellow" if i == self.active_service_index else ""
            table.add_row(Text(f" {status_icon}", style=status_style), Text(f" {name}", style=style))

        title = f"Services in {category_name}"
        return Panel(table, title=title, border_style="blue")

    def draw_details_view(self) -> Panel:
        """Draws the details view with 3-tier status text."""
        if self.view_mode == "categories":
            return Panel(Text("\nSelect a category to view services.", justify="center", style="dim"), title="Details", border_style="green")

        services = self.get_current_services()
        if not services:
            return Panel(Text("No services in this category.", justify="center", style="dim"), title="Details", border_style="green")

        if self.active_service_index >= len(services): self.active_service_index = len(services) - 1
        service_name = services[self.active_service_index]
        info = self.services_data[self.categories[self.active_category_index]][service_name]

        details_text = Text()
        details_text.append("Service:\n", style="bold yellow").append(f"{service_name}\n\n")
        details_text.append("Type: ", style="bold yellow").append(f"{info['type'].capitalize()}\n\n")

        if info.get("domain"):
            details_text.append("Domain: ", style="bold yellow").append(f"{info['domain']}\n")
        if "loaded" in info:
            evidence = ("Loaded in launchd" if info["loaded"] else
                        "Saved override; not loaded" if info.get("plist_path") else
                        "Override only; installation not confirmed")
            details_text.append("Discovery: ", style="bold yellow").append(f"{evidence}\n")
        if info.get("plist_path"):
            details_text.append("Configuration: ", style="bold yellow").append(f"{info['plist_path']}\n")
        if info.get("program"):
            details_text.append("Program: ", style="bold yellow").append(f"{info['program']}\n")
        if info.get("pid"):
            details_text.append("PID: ", style="bold yellow").append(f"{info['pid']}\n")

        # Display current status
        live_status = info['status']
        status_styles = {"running": "green", "loaded": "green", "enabled": "green", "disabled": "red"}
        details_text.append("Status: ", style="bold yellow").append(f"{live_status.capitalize()}\n", style=status_styles.get(live_status, "default"))
        
        if "policy_source" in info:
            policy = info.get("enabled_status", "unknown").capitalize()
            details_text.append("Launch policy: ", style="bold yellow").append(f"{policy} — {info['policy_source']}\n")
        elif live_status == "running" and info.get("enabled_status") == "disabled":
            details_text.append("Launch override: Disabled (process still running)\n", style="yellow")

        # Display pending status change
        pending_status = info.get('pending_status')
        if pending_status and pending_status != info.get("enabled_status", live_status):
            pending_color = "green" if pending_status == "enabled" else "red"
            details_text.append("Pending: ", style="bold yellow").append(f"{pending_status.capitalize()} (press Enter to apply)\n", style=pending_color)

        details_text.append("\nDescription:\n", style="bold yellow").append(f"{info['description']}\n\n")
        source = info.get("metadata_source") or "Historical local database; description and impact not independently verified"
        details_text.append("Source: ", style="bold yellow").append(f"{source}\n\n", style="dim")
        impact_text = info["impact"]
        impact_style = "bold red" if "CRITICAL" in impact_text.upper() else "default"
        details_text.append("Impact of Disabling (estimate):\n", style="bold yellow").append(impact_text, style=impact_style)

        return Panel(details_text, title="Details", border_style="green")

    def confirm_and_apply(self, live):
        changes = [(s, i) for c in self.services_data.values() for s, i in c.items() if "pending_status" in i and i["pending_status"] != i.get("enabled_status", i["status"])]

        if not changes:
            self.console.print(Panel(Text("No changes to apply.", justify="center")))
            time.sleep(1.5)
            return

        self.console.print(Panel(self.generate_command_table(changes), title="[bold yellow]Confirm Changes"))
        self.console.print(Panel(Text("Press 'y' to apply, any other key to cancel.", justify="center")))
        key = self.read_key()

        warnings = []
        if key.lower() == "y":
            with Progress(console=self.console, transient=False) as progress:
                task = progress.add_task("[cyan]Applying changes...", total=len(changes))
                for service, info in changes:
                    action_str = info["pending_status"] # Will be "enabled" or "disabled"
                    command_action = "enable" if action_str == "enabled" else "disable"
                    domain = info.get("domain", "system" if info["type"] == "daemon" else f"gui/{self.uid}")
                    success, error = set_service_enabled(info.get("label", service), domain, command_action == "enable")
                    if success:
                        info["status"] = info["pending_status"]
                        info["enabled_status"] = info["pending_status"]
                        del info["pending_status"]
                    else:
                        warnings.append(f"{service} [{domain}]: {error}")
                    progress.update(task, advance=1, description=f"[cyan]{'Verified' if success else 'Failed'} {service}")

            if warnings:
                warning_text = "\n".join(warnings)
                self.console.print(Panel(Text(f"Some services may not have been fully disabled or stopped:\n\n{warning_text}", justify="left", style="yellow"), title="[bold red]Warning"))
                self.console.print("Press any key to continue.")
                self.read_key()
            else:
                self.console.print(Panel(Text("✅ Changes applied successfully. Rescanning services...", justify="center"), style="green"))
                time.sleep(2)
            self.services_data = get_live_services(self.console)
            self.categories = list(self.services_data)
            self.active_category_index = min(self.active_category_index, max(0, len(self.categories) - 1))
            self.active_service_index = 0
            self.service_scroll_offset = 0
            if not self.categories:
                self.exit_app = True
        else:
            for _, info in changes: del info["pending_status"]
            self.console.print(Panel(Text("❌ Changes cancelled.", justify="center"), style="red"))
            time.sleep(1.5)

    def generate_command_table(self, changes: List[Tuple[str, Dict]]) -> Table:
        # (Same as previous version, but logic simplified)
        table = Table(title="Commands to be Executed", expand=True)
        table.add_column("Action", style="cyan", justify="right")
        table.add_column("Service Target", style="magenta")
        for service, info in changes:
            action = "disable" if info["pending_status"] == "disabled" else "enable"
            domain = info.get("domain", "system" if info["type"] == "daemon" else f"gui/{self.uid}")
            target = f"{domain}/{info.get('label', service)}"
            cmd_prefix = "sudo " if info["type"] == "daemon" else ""
            table.add_row(f"{cmd_prefix}launchctl {action}", target)
            if action == "disable":
                table.add_row(f"{cmd_prefix}launchctl bootout", target)
        return table

    def run(self):
        # (Main loop logic modified slightly for re-scan)
        if not sys.stdin.isatty():
            self.console.print("[bold red]This application requires an interactive terminal.[/]")
            return
            
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            with Live(self.draw_layout(), screen=True, transient=True, auto_refresh=False) as live:
                while not self.exit_app:
                    action = self.handle_input(self.read_key())
                    
                    if action == "apply":
                        live.stop()
                        self.confirm_and_apply(live) # This method now handles the rescan
                        if self.exit_app:
                            break
                        live.start(refresh=True)
                    
                    live.update(self.draw_layout(), refresh=True)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        self.console.clear()
        self.console.print("[bold cyan]Exiting Service Manager. Goodbye![/]")


def check_sip_status() -> bool:
    # (Same as previous version)
    try:
        result = subprocess.run(["csrutil", "status"], capture_output=True, text=True, check=True)
        return "System Integrity Protection status: enabled" in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True

if __name__ == "__main__":
    # (Same as previous version)
    if os.geteuid() != 0:
        console = Console()
        console.print("[bold red]Error:[/] This script must be run with 'sudo' to manage system services.")
        console.print("Please run as: sudo .venv/bin/python3 manage-services.tui.py")
        sys.exit(1)

    console = Console()
    if check_sip_status():
        console.print(Panel("[bold yellow]Warning:[/] System Integrity Protection (SIP) is [red]enabled[/].\n\n"
                            "Disabling most system daemons will fail. You can browse services, "
                            "but applying changes to system daemons will likely have no effect.",
                            title="SIP Enabled"))
        console.print("Continuing in 5 seconds...")
        time.sleep(5)

    live_services_data = get_live_services(console)
    if not live_services_data:
        console.print("[bold red]Could not retrieve any services. Exiting.[/]")
        sys.exit(1)

    app = ServiceManagerTUI(live_services_data)
    app.run()