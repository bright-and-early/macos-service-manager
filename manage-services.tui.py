#!/usr/bin/env python3
# pylint: disable=line-too-long

import os
import re
import subprocess
import sys
import termios
import time
import tty
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table
from rich.text import Text

# --- Service Details Database ---
# This dictionary contains the detailed research on each service.
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
    "description": "An accessibility feature allowing pointer control using head or eye tracking.",
    "impact": "Dwell Control functionality will be disabled.",
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
    "description": "A helper process for the analytics daemon, likely involved in gathering system-level logs.",
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
    "description": "A support daemon for the Apple TV app, likely managing the 'Up Next' watchlist.",
    "impact": "The 'Up Next' feature in the TV app may not sync or update correctly.",
  },
  "com.apple.triald.system": {
    "description": "Manages trial periods for applications from the Mac App Store.",
    "impact": "App trials may not function correctly or their status may not be tracked.",
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
    "description": "Potentially related to managing the 'sleep' or suspended state of applications.",
    "impact": "Unknown, but could affect app lifecycle management.",
  },
  "com.apple.storekitagent": {
    "description": "Agent for StoreKit, handling in-app purchases and interactions with the App Store.",
    "impact": "In-app purchases will not work.",
  },
  "com.apple.appplaceholdersyncd": {
    "description": "Syncs app placeholders, likely for restoring apps on a new device.",
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
    "description": "A helper agent for Time Machine that assists with backup scheduling and management, possibly showing menu bar status.",
    "impact": "Time Machine backups may not run automatically or may encounter errors. Status updates may not be shown.",
  },
  "com.apple.mbsystemadministration": {
    "description": "Handles system administration tasks related to Mobile Backup (mb), a component of the Time Machine backup system.",
    "impact": "Disabling this could interfere with Time Machine's ability to properly manage backup sets.",
  },
  "com.apple.mbfloagent": {
    "description": "A flow agent for Mobile Backup (Time Machine), possibly managing data transfer.",
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
    "description": "A tool for managing the 'Volume Shadow' database, used for Time Machine local snapshots.",
    "impact": "Time Machine's local snapshots may not function correctly."
  },
  "com.apple.mbusertrampoline": {
    "description": "A 'trampoline' service for Mobile Backup (Time Machine), likely for launching processes with the correct permissions.",
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
    "description": "The daemon for remote control services, including the legacy iTunes Remote.",
    "impact": "You will not be able to control this Mac with remote control applications."
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
    "description": "Likely a 'Boot OS' reporter for diagnostics.",
    "impact": "The system will not be able to report on issues that occur early in the boot process."
  },
  "com.apple.boswatcher": {
    "description": "Likely a 'Boot OS' watcher for diagnostics.",
    "impact": "Similar to `bosreporter`, this is likely for monitoring the early boot process."
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
    "description": "'Security Event Logging Daemon,' likely.",
    "impact": "The system may not be able to log security-related events."
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
    "description": "A version of `diskimagesiod` with an unclear purpose ('spb').",
    "impact": "May affect the functionality of disk images."
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
    "description": "Daemon for saving game progress, likely with iCloud.",
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
    "description": "Likely related to Apple Arcade's 'Frames Per Second' (FPS) or game services.",
    "impact": "May impact Apple Arcade game performance or features."
  },
  "com.apple.gamepolicyd": {
    "description": "A daemon that enforces policies related to games.",
    "impact": "May affect game performance or features."
  },
  # Hardware & Drivers
  "com.apple.IOUserDockChannelSerial-0x10000...": {
    "description": "A user-space driver (DriverKit) that manages serial communication channels for accessories connected via a dock or other multifunction adapter.",
    "impact": "Will break specific dock-connected accessories that rely on serial communication. Terminating this service has been reported to cause kernel panics and system instability.",
  },
  "com.apple.airportd": {
    "description": "The core daemon that manages Wi-Fi hardware and connections.",
    "impact": "CRITICAL: Wi-Fi will be completely disabled and you will not be able to connect to any wireless networks.",
  },
  "com.apple.appleh13camerad": {
    "description": "A low-level daemon that directly interfaces with the Image Signal Processor (ISP) and Apple Neural Engine (ANE) for the built-in camera on H13-generation hardware.",
    "impact": "The built-in FaceTime/iSight camera will not function. This is a hardware-specific driver.",
  },
  "com.apple.appleh16camerad": {
    "description": "A low-level daemon that directly interfaces with the Image Signal Processor (ISP) and Apple Neural Engine (ANE) for the built-in camera on H16-generation hardware.",
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
    "description": "A core audio mixer/multiplexer daemon that appears to handle complex routing and combining of audio streams. It is prone to high memory usage when bugs are present.",
    "impact": "Disabling this would likely cause severe audio malfunctions, possibly breaking all audio input or output. HIGH RISK.",
  },
  "com.apple.cameracaptured": {
    "description": "A high-level daemon that manages and arbitrates access to camera hardware, preventing conflicts between applications.",
    "impact": "Applications will be unable to access the camera, as the service for managing capture sessions will be unavailable.",
  },
  "com.apple.cmio.IOSScreenCaptureAssistant": {
    "description": "A helper daemon that enables the feature to record or display an attached iPhone or iPad's screen on the Mac using applications like QuickTime Player.",
    "impact": "You will not be able to record or view your iOS/iPadOS device's screen on your Mac.",
  },
  "com.apple.cmio.VCAssistant": {
    "description": "A helper daemon for the Core Media I/O (CMIO) framework, likely assisting with video conferencing functionalities such as stream optimization.",
    "impact": "Features within FaceTime and other video calling apps may be degraded or fail entirely.",
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
    "description": "A generically named 'Device Interface Daemon'. Its specific function is not documented.",
    "impact": "Unknown. Disabling this service is not recommended as its function and dependencies are not clear, and it could affect hardware stability.",
  },
  "com.apple.displaypolicyd": {
    "description": "The Display Policy Daemon. Enforces high-level policies for displays and GPUs, most notably automatic graphics switching on dual-GPU Macs.",
    "impact": "On dual-GPU Macs, may break power-saving graphics switching. On all Macs, its failure during boot can prevent the system from starting up.",
  },
  "com.apple.driverkit.AppleUserHIDDrivers-0...": {
    "description": "A core user-space driver (DriverKit) for Human Interface Devices (HID). This is the modern driver for many keyboards, mice, and trackpads.",
    "impact": "CRITICAL: Some or all input devices will stop working, potentially rendering the system uncontrollable. Termination can lead to kernel panics.",
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
  "com.apple.liquidddetectiond": {
    "description": "The Liquid Damage Detection Daemon. A diagnostic service introduced in macOS Sonoma that monitors and logs liquid exposure events in the Mac's ports.",
    "impact": "The OS will not record liquid damage events. This has no impact on functionality and may be desirable for privacy.",
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
    "description": "A helper for the Core Media I/O framework that assists with legacy VDC (Video Digitizer Component) cameras.",
    "impact": "Some older webcams may not function correctly."
  },
  "com.apple.cmio.iOSScreenCaptureAssistant": {
    "description": "A helper for capturing the screen of an iOS device.",
    "impact": "You will not be able to record the screen of a connected iPhone or iPad."
  },
  "com.apple.corekdld": {
    "description": "Core Kernel Driver Loader daemon.",
    "impact": "May cause issues with loading kernel drivers."
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
    "description": "A host daemon for an 'EOS' service, which is likely related to a camera or imaging device.",
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
    "description": "A daemon for detecting liquid in the ports of the Mac.",
    "impact": "The system will not be able to warn you about liquid in the ports, potentially preventing damage."
  },
  "com.apple.nfcd": {
    "description": "The daemon for Near Field Communication (NFC).",
    "impact": "If your Mac has an NFC reader, it will not function. Not relevant for most Macs."
  },
  "com.apple.oahd": {
    "description": "'Over-the-Air Helper Daemon,' likely for wireless updates of accessories like AirPods.",
    "impact": "Firmware updates for wireless accessories may fail."
  },
  "com.apple.oahd-root-helper": {
    "description": "A root helper for `oahd`.",
    "impact": "Privileged operations for wireless accessory updates may fail."
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
    "description": "Cloud Managed File Sync Agent, likely related to iCloud file syncing.",
    "impact": "iCloud file syncing may be impaired.",
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
    "description": "Manages iCloud-related user notifications.",
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
    "description": "The daemon for the 'Find My Mac' feature.",
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
    "description": "Likely related to sharing the Content Caching service over a tethered connection (e.g., via USB to an iOS device).",
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
    "description": "Likely related to handling encrypted components during a software update.",
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
    "description": "A mechanism for `ManagedClient` that likely handles specific management tasks.",
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
    "description": "A daemon related to MDM, with an unclear specific purpose ('tesla').",
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
    "description": "A proxy service for certain network connections.",
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
    "description": "Manages network routing decisions, possibly for features like Wi-Fi Assist.",
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
    "description": "Likely related to the Data Plane Development Kit (DPDK) for high-performance networking.",
    "impact": "High-performance networking features may not work. Not relevant for most users."
  },
  "com.apple.eapolcfg_auth": {
    "description": "A tool for configuring EAP (Extensible Authentication Protocol) over LAN (EAPOL), used in 802.1X network authentication.",
    "impact": "You will not be able to configure 802.1X network settings."
  },
  "com.apple.mDNSResponder.reloaded": {
    "description": "A signal to `mDNSResponder` that it has been reloaded.",
    "impact": "Not a standalone service."
  },
  "com.apple.mDNSResponderHelper.reloaded": {
    "description": "A signal to the `mDNSResponderHelper` that it has been reloaded.",
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
    "description": "A daemon for 'Wi-Fi Velocity,' which likely handles network roaming and handoff.",
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
  "com.apple.Safari.SafeBrowse.Service": {
    "description": "Service for Google Safe Browse to protect against malicious websites.",
    "impact": "You will not be warned about fraudulent or malicious websites in Safari.",
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
    "description": "A daemon for OS-level predictions, likely for performance optimizations.",
    "impact": "The system may be less efficient at predicting user behavior to optimize performance."
  },
  "com.apple.uarpassetmanagerd": {
    "description": "A daemon for managing assets for 'Universal Augmented Reality Platform' (UARP).",
    "impact": "Augmented reality features may not work correctly."
  },
  "com.apple.uarpd": {
    "description": "The daemon for 'Universal Augmented Reality Platform' (UARP).",
    "impact": "Augmented reality features may not work correctly."
  },
  "com.apple.uarphidd": {
    "description": "A daemon for HID (Human Interface Device) interactions with UARP.",
    "impact": "Augmented reality features that require user input may not work."
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
  "com.apple.MRTD": {
    "description": "MRT-d stands for Malware Removal Tool daemon. It is a background process that checks for and removes known malware.",
    "impact": "Disabling this service will stop Apple's built-in anti-malware scanner from running, potentially leaving the system more vulnerable.",
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
    "description": "Daemon for handling secure backups, likely of keychain data.",
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
    "description": "Daemon for fraud detection, likely related to Apple Pay and Store transactions.",
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
    "description": "A helper process for the CryptoTokenKit framework, likely related to authentication with hardware tokens.",
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
    "description": "Likely related to 'Always On' features for secure enclaves.",
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
    "impact": "CRITICAL: Contacts will not sync or be available to other apps. Disabling is known to cause the App Store and other applications to freeze or crash.",
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
    "description": "A legacy agent for MobileMe iDisk services.",
    "impact": "Not relevant for modern macOS."
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
    "description": "A daemon that 'warms up' applications by pre-loading them into memory.",
    "impact": "Application launch times may be slower."
  },
  "com.apple.watchdogd": {
    "description": "A watchdog daemon that monitors the system for hangs and forces a restart if necessary.",
    "impact": "The system may hang indefinitely instead of automatically restarting, requiring a manual power cycle."
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
    "description": "Daemon for understanding text content, likely for data detection or suggestions.",
    "impact": "Features that detect data like dates or addresses in text may fail.",
  },
  "com.apple.DataDetectorsSourceAccess": {
    "description": "Allows applications to access the data detectors framework, which recognizes dates, locations, and other data types in text.",
    "impact": "Data detection features in applications like Mail and Messages will not work."
  },
  "com.apple.fontmover": {
    "description": "A tool for moving fonts, likely for legacy compatibility.",
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
    "impact": "CRITICAL: Do Not Disturb and Focus modes will not work. Disabling is known to break Notification Center and system responsiveness.",
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
    "description": "A notification service, possibly for 'Mobile Experience' or menu extras.",
    "impact": "Certain system or app notifications may not be delivered.",
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
    "description": "An agent that assists the WindowServer in managing windows.",
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
    "description": "A proxy for notifications, likely for compatibility with iOS-style notifications.",
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
    "description": "Related to Internet File Client (IFC) services, potentially for legacy internet file sharing protocols. Its specific role is not well-documented.",
    "impact": "May affect legacy file sharing functionalities. The exact impact is unclear due to lack of documentation."
  },
  "com.apple.corercd": {
    "description": "The function of this service is not well-documented, but the name suggests a role in remote control or core services.",
    "impact": "The precise impact of this service being missing is unknown. It could potentially affect remote control functionalities or other core system operations."
  },
  "com.apple.filesystems.doubleagentd": {
    "description": "A service with a non-obvious name, 'doubleagentd', related to file systems. Its exact purpose is not documented.",
    "impact": "The impact of this service's absence is unknown due to a lack of public information."
  },
  "com.apple.griddatad": {
    "description": "The purpose of this service is not clearly documented, but the name suggests it might be related to data services for a grid-based system or UI element.",
    "impact": "The impact of this service being missing is unknown."
  },
  "com.apple.internal.aupbregistrarservice": {
    "description": "An internal service likely related to the registration of audio unit plugins. The 'aupb' part is not standard and its function is not publicly documented.",
    "impact": "May cause issues with the registration or functioning of audio unit plugins, particularly non-standard ones."
  },
  "com.apple.lskdd": {
    "description": "A daemon whose name suggests a connection to a 'Local Security' framework, but the 'kdd' part is not well-understood. Its function is not documented.",
    "impact": "The impact of this service's absence is unknown but could potentially relate to local security policies or key distribution."
  },
  "com.apple.multiversed": {
    "description": "A daemon whose name suggests it is related to file versioning or alternative file systems, but its exact function is not publicly documented.",
    "impact": "The impact is unclear, but it might affect features related to file versions or backups."
  },
  "com.apple.pfd": {
    "description": "The name suggests a 'Policy File Daemon,' but its specific domain and function are not documented.",
    "impact": "The impact of this service being missing is unknown."
  },
  "com.apple.powerd.swd": {
    "description": "A 'software' daemon related to power management. Its specific role in addition to the main `powerd` is not documented.",
    "impact": "May impact specific software-related power management features. The exact impact is unknown."
  },
  "com.apple.relatived": {
    "description": "A daemon whose name suggests a role in relative positioning or location, but its function is not documented.",
    "impact": "The impact is unknown, but it could be related to location services or spatial awareness features."
  },
  "com.apple.systemstatusd": {
    "description": "A daemon that appears to monitor various aspects of the system's status, but its specific responsibilities and consumers are not well-documented.",
    "impact": "The impact is unclear, but its absence could affect how the system or certain applications respond to changes in system state."
  },
  "com.apple.tracd": {
    "description": "The name suggests a 'Trace Daemon' for diagnostic purposes, but its specific function is not documented.",
    "impact": "The system may lose some of its diagnostic tracing capabilities."
  },
  "com.apple.ucupdate.plist": {
    "description": "An update service with the unknown 'UC' designation. Its purpose is not documented.",
    "impact": "The impact of this service being missing is unknown, but it could relate to a specific component's update mechanism."
  },
  "com.apple.xartstorageremoted": {
    "description": "A remote storage service for an unknown framework or component referred to as 'XArt.' Its function is not documented.",
    "impact": "The impact is unknown."
  },
  "com.apple.xpc.uscwoap": {
    "description": "An XPC service with an un-decipherable name. Its purpose is not documented.",
    "impact": "The impact of this service being missing is unknown."
  },
  "com.apple.mobile.NRDUpdated": {
    "description": "Likely related to 'Network Resource Discovery' updates.",
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
        "description": "A daemon for generative experiences, likely related to new on-device AI and ML features.",
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
        "description": "A file replication service, likely used for syncing data between devices or with iCloud.",
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
        "description": "A daemon that likely manages recent and suggested destinations in Apple Maps.",
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
    # --- Previously Researched Apple Services ---
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
}

CATEGORIZATION_MAP = {
  "♿️ Accessibility": [
    "com.apple.accessibility.MotionTrackingAgent",
    "com.apple.accessibility.axassetsd",
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
    "com.apple.appstored",
    "com.apple.commerce",
    "com.apple.passd",
    "com.apple.financed",
    "com.apple.watchlistd",
    "com.apple.triald.system",
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
    "com.apple.bluetoothd",
    "com.apple.nearbyd",
    "com.apple.rapportd",
    "com.apple.sidecar-relay",
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
            "com.apple.imautomatichistorydeletionagent", "com.apple.sidecar-hid-relay",
  ],
  "🕵️  Diagnostics & Logging": [
    "com.apple.logd",
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
    "com.apple.usbctelemetryd",
  ],
  "👪 Family & ScreenTime": [
    "com.apple.familycontrols.useragent",
    "com.apple.familycircled",
    "com.apple.ScreenTimeAgent",
    "com.apple.parentalcontrols.check",
    "com.apple.FamilyControlsAgent",
    "com.apple.familycontrols",
            "com.apple.familynotificationd", "com.apple.UsageTrackingAgent",
  ],
  "💽 Filesystem & Storage": [
    "com.apple.fseventsd",
    "com.apple.diskarbitrationd",
    "com.apple.storagekitd",
    "com.apple.corestorage.corestoraged",
    "com.apple.hdiejectd",
    "com.apple.nfsd",
    "com.apple.smbd",
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
  ],
  "🎮 Game Center": [
    "com.apple.gamed",
    "com.apple.GameController.gamecontrolleragentd",
    "com.apple.gamesaved",
    "com.apple.GamePolicyAgent",
    "com.apple.GameController.gamecontrollerd",
    "com.apple.fpsd.arcadeservice",
    "com.apple.gamepolicyd",
  ],
  "🔌 Hardware & Drivers": [
    "com.apple.IOUserDockChannelSerial-0x10000...",
    "com.apple.airportd",
    "com.apple.appleh13camerad",
    "com.apple.appleh16camerad",
    "com.apple.audio.AudioComponentRegistrar",
    "com.apple.audio.coreaudiod",
    "com.apple.audio.isolated.historicalaudiod",
    "com.apple.audio.isolated.micactivityd",
    "com.apple.audio.systemsoundserverd",
    "com.apple.audiomxd",
    "com.apple.cameracaptured",
    "com.apple.cmio.IOSScreenCaptureAssistant",
    "com.apple.cmio.VCAssistant",
    "com.apple.cmio.uvcassistantextension",
    "com.apple.colorsync.displayservices",
    "com.apple.colorsyncd",
    "com.apple.corebrightnessd",
    "com.apple.ctkd",
    "com.apple.deviceinterfaced",
    "com.apple.displaypolicyd",
    "com.apple.driverkit.AppleUserHIDDrivers-0...",
    "com.apple.hidd",
    "com.apple.ifdreader",
    "com.apple.iomfb_bics_daemon",
    "com.apple.iomfb_fdr_loader",
    "com.apple.kernelmanagerd",
    "com.apple.liquidddetectiond",
    "com.apple.nand.aspcarry",
    "com.apple.nand_task_scheduler",
    "com.apple.powerd",
    "com.apple.retimerd",
    "com.apple.scsid",
    "com.apple.sysextd",
    "com.apple.thermald",
    "com.apple.touchbarserver",
    "com.apple.SafeEjectGPUAgent",
    "com.apple.cmio.LaunchCMIOUserExtensionsAgent",
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
    "com.apple.wifiFirmwareLoader",
    "org.cups.cupsd",
            "com.apple.iokit.IOServiceAuthorizeAgent", "com.apple.cvmsCompAgent",
  ],
  "🏠 HomeKit": [
    "com.apple.homed",
    "com.apple.homeenergyd",],
  "☁️  iCloud & CloudKit": [
    "com.apple.cloudd",
    "com.apple.bird",
    "com.apple.cloudphotod",
    "com.apple.icloud.findmydeviced",
    "com.apple.icloud.searchpartyd",
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
            "com.apple.icloud.searchpartyuseragent", "com.apple.icloud.fmfd", "com.apple.icloudmailagent",
  ],
  "📦 Installation & Updates": [
    "com.apple.installd",
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
    "com.apple.ManagedClient",
    "com.apple.RemotePairTool",
    "com.apple.ManagedClientAgent.agent",
    "com.apple.ManagedSettingsAgent",
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
    "com.apple.mDNSResponder",
    "com.apple.configd",
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
  ],
  "🗺️  Maps & Location": [
    "com.apple.locationd",
    "com.apple.geod",
    "com.apple.routined",
    "com.apple.Maps.mapspushd",
    "com.apple.countryd",
    "com.apple.navd",
    "com.apple.maps.destinationd",
    "com.apple.CoreRoutine.helperservice"
  ],
  "⚡️ Power Management": [
      "com.apple.powerd",
      "com.apple.PerfPowerServices",
      "com.apple.PerfPowerServicesExtended",
      "com.apple.PowerUIAgent",
      "com.apple.peakpowermanagerd",
      "com.apple.powerexperienced",
  ],
  "🖼️  Photos & Media": [
    "com.apple.photoanalysisd",
    "com.apple.photolibraryd",
    "com.apple.mediaanalysisd",
    "com.apple.mediastream.mstreamd",
    "com.apple.AMPArtworkAgent",
    "com.apple.avconferenced",
    "com.apple.amp.mediasharingd",
    "com.apple.AMPLibraryAgent",
    "com.apple.tonelibraryd",
    "com.apple.rcd",
    "com.apple.musicd",
  ],
  "🧠 Proactive & Intelligence": [
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
    "com.apple.uarpassetmanagerd",
    "com.apple.uarpd",
    "com.apple.uarphidd",
        "com.apple.duetexpertd", "com.apple.generativeexperiencesd", "com.apple.intelligenceflowd",
        "com.apple.knowledgeconstructiond", "com.apple.ContextStoreAgent", "com.apple.intelligencecontextd",
        "com.apple.biomesyncd",
  ],
  "🌐 Safari & WebKit": [
    "com.apple.SafariHistoryServiceAgent",
    "com.apple.SafariBookmarksSyncAgent",
    "com.apple.Safari.PasswordBreachAgent",
    "com.apple.Safari.SafeBrowse.Service",
    "com.apple.SafariNotificationAgent",
    "com.apple.SafariLaunchAgent",
    "com.apple.Safari.History",
    "com.apple.webkit.webpushd",
    "com.apple.webprivacyd",
    "com.apple.webinspectord",
    "com.apple.swcd",
  ],
  "🔒 Security & Keychain": [
    "com.apple.securityd",
    "com.apple.tccd",
    "com.apple.syspolicyd",
    "com.apple.authd",
    "com.apple.MRTD",
    "com.apple.cryptexd",
    "com.apple.lockd",
    "com.apple.devicecheckd",
    "com.apple.MRTa",
    "com.apple.trustd.agent",
    "com.apple.TrustedPeersHelper",
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
    "com.apple.assistantd",
    "com.apple.corespeechd",
    "com.apple.siriknowledged",
    "com.apple.Siri.agent",
    "com.apple.shazamd",
    "com.apple.speech.speechsynthesisd.x86_64",
    "com.apple.speech.synthesisserver",
    "com.apple.speech.speechdatainstallerd",
    "com.apple.DictationIM",
    "com.apple.corespeechd_system",
    "com.apple.siri.acousticsignature",
       "com.apple.assistant_service", "com.apple.siriactionsd", "com.apple.SiriTTSTrainingAgent",
        "com.apple.sirittsd", "com.apple.siri.context.service", "com.apple.speech.speechsynthesisd",
        "com.apple.SpeechRecognitionCore.brokerd",
  ],
  "⚙️  System Core": [
    "com.apple.coreservicesd",
    "com.apple.runningboardd",
    "com.apple.lsd",
    "com.apple.loginwindow",
    "com.apple.logind",
    "com.apple.opendirectoryd",
    "com.apple.notifyd",
    "com.apple.distnoted",
    "com.apple.cfprefsd",
    "com.apple.contactsd",
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
    "com.vix.cron",
      "com.apple.helpd", "com.apple.hiservices-xpcservice", "com.apple.mdworker.mail",
        "com.apple.mdworker.shared", "com.apple.mdworker.single", "com.apple.metadata.mdbulkimport",
        "com.apple.pluginkit.pkd", "com.apple.usermanagerhelper", "com.apple.WorkflowKit.ShortcutsViewService",
        "com.apple.FolderActionsDispatcher", "com.apple.metadata.mdflagwriter"
  ],
  "✍️  Text & Input": [
    "com.apple.naturallanguaged",
    "com.apple.languaged",
    "com.apple.applespell",
    "com.apple.FontWorker",
    "com.apple.localizationswitcherd",
    "com.apple.languageassetd",
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
  ],
  "🧩 Third-Party": [
    "com.google.keystone.user.agent",
    "com.google.keystone.user.xpcservice",
    "com.docker.helper",
    "com.docker.socket",
    "com.docker.vmnetd",
    "com.adobe.GC.AGM",
    "com.adobe.GC.Scheduler-1.0",
    "Adobe_Genuine_Software_Integrity_Service",
    "com.microsoft.update.agent",
    "com.microsoft.autoupdate.helper",
    "com.1password.1password-launcher",
    "2BUA8C4S2C.com.agilebits.onepassword7-helper",
    "com.macpaw.CleanMyMac-setapp.HealthMonitor",
    "com.postgresapp.Postgres2LoginHelper",
    "com.figma.daemon",
    "homebrew.mxcl.redis",
  ],
  "🖥️  User Interface & Windowing": [
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
     "com.apple.progressd", "com.apple.tipsd", "com.apple.MessageUIMacHelperService",
        "com.apple.ViewBridgeAuxiliary", "com.apple.screencaptureui"
  ],
  "☀️ Weather": [
    "com.apple.weatherd",
    "com.apple.weather.menu",
  ],
  "❓ Undocumented": [
     "com.apple.IFCStart", "com.apple.corercd", "com.apple.filesystems.doubleagentd",
        "com.apple.griddatad", "com.apple.internal.aupbregistrarservice", "com.apple.lskdd",
        "com.apple.multiversed", "com.apple.pfd", "com.apple.powerd.swd",
        "com.apple.relatived", "com.apple.systemstatusd", "com.apple.tracd",
        "com.apple.ucupdate.plist", "com.apple.xartstorageremoted", "com.apple.xpc.uscwoap",
        "com.apple.mobile.NRDUpdated", "com.apple.replicatord",
  ]
}

# --- Live Data Functions ---

def get_uid() -> int:
    """Gets the UID of the current user."""
    return os.getuid()

def parse_launchctl_print_output(output: str) -> Tuple[set, Dict[str, str]]:
    """Parses the output of `launchctl print` to get service names and disabled statuses."""
    service_names = set()
    disabled_status = {}

    service_pattern = re.compile(r"^\s*[\d-]+\s+[\d-]+\s+([a-zA-Z0-9\._-]+)\s*$", re.MULTILINE)
    for match in service_pattern.finditer(output):
        service_names.add(match.group(1))

    disabled_section_match = re.search(r"disabled services = {([^}]+)}", output, re.DOTALL)
    if disabled_section_match:
        disabled_block = disabled_section_match.group(1)
        disabled_pattern = re.compile(r'"([^"]+)"\s*=>\s*(enabled|disabled)')
        for match in disabled_pattern.finditer(disabled_block):
            service_name, status = match.groups()
            disabled_status[service_name] = status
            service_names.add(service_name)

    return service_names, disabled_status

def get_service_details(service_name: str, service_type: str, statuses: Dict[str, str], pids: Dict[str, str]) -> Optional[Dict]:
    """Gets live status and combines it with stored metadata from the database."""
    status = "unknown"

    # Determine the 3-tier status: Running > Enabled > Disabled
    if service_name in pids:
        status = "Running"
    elif statuses.get(service_name) == 'disabled':
        status = "Disabled"
    else:
        # Covers both explicitly enabled and default-enabled services
        status = "Enabled"

    stored_info = SERVICE_DATABASE.get(
        service_name,
        {
            "description": "No detailed information in the local database for this service.",
            "impact": "The impact of disabling this service is unknown. Proceed with caution.",
        },
    )

    return {
        "status": status,
        "description": stored_info["description"],
        "impact": stored_info["impact"],
        "type": service_type,
    }


def get_live_services(console: Console) -> Dict[str, Dict[str, Dict]]:
    """Connects to the system to get a list of all services, their status, and categorizes them."""
    # Ensure all possible categories are initialized
    categorized_services = OrderedDict((category, {}) for category in CATEGORIZATION_MAP.keys())
    categorized_services["🧩 Third-Party"] = {}
    categorized_services["❓ Undocumented"] = {}

    uid = get_uid()

    all_daemon_names = set()
    all_agent_names = set()
    daemon_pids = {}
    agent_pids = {}
    disabled_daemons = {}
    disabled_agents = {}

    with Progress(console=console, transient=True) as progress:
        task = progress.add_task("[cyan]Discovering system services...", total=4)

        try:
            daemons_raw = subprocess.run(
                ["sudo", "launchctl", "list"], capture_output=True, text=True, check=True
            ).stdout
            for line in daemons_raw.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    all_daemon_names.add(parts[2])
                    if parts[0] != "-":
                        daemon_pids[parts[2]] = parts[0]
        except Exception: pass
        progress.update(task, advance=1, description="[cyan]Parsed system daemons...")

        try:
            print_system_raw = subprocess.run(
                ["sudo", "launchctl", "print", "system/"], capture_output=True, text=True, check=True
            ).stdout
            names, statuses = parse_launchctl_print_output(print_system_raw)
            all_daemon_names.update(names)
            disabled_daemons.update(statuses)
        except Exception: pass
        progress.update(task, advance=1, description="[cyan]Analyzed system overrides...")

        try:
            agents_raw = subprocess.run(
                ["launchctl", "list"], capture_output=True, text=True, check=True
            ).stdout
            for line in agents_raw.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    all_agent_names.add(parts[2])
                    if parts[0] != "-":
                        agent_pids[parts[2]] = parts[0]
        except Exception: pass
        progress.update(task, advance=1, description="[cyan]Parsed user agents...")

        try:
            print_user_raw = subprocess.run(
                ["launchctl", "print", f"user/{uid}"], capture_output=True, text=True, check=True
            ).stdout
            names, statuses = parse_launchctl_print_output(print_user_raw)
            all_agent_names.update(names)
            disabled_agents.update(statuses)
        except Exception: pass
        progress.update(task, advance=1, description="[cyan]Analyzed user overrides...")

    all_services = sorted(list(all_daemon_names.union(all_agent_names)))
    
    with Progress(console=console, transient=True) as progress:
        fetch_task = progress.add_task("[green]Categorizing services...", total=len(all_services))
        for name in all_services:
            is_daemon = name in all_daemon_names
            service_type = "daemon" if is_daemon else "agent"
            details = get_service_details(
                name,
                service_type,
                disabled_daemons if is_daemon else disabled_agents,
                daemon_pids if is_daemon else agent_pids
            )
            if details:
                category = categorize_service(name)
                categorized_services[category][name] = details
            progress.update(fetch_task, advance=1)

    return OrderedDict([(cat, servs) for cat, servs in categorized_services.items() if servs])

def categorize_service(service_name: str) -> str:
    """Categorizes a service based on the CATEGORIZATION_MAP."""
    for category, service_list in CATEGORIZATION_MAP.items():
        if service_name in service_list:
            return category
    if "com.apple" not in service_name:
        return "🧩 Third-Party"
    return "❓ Undocumented"

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
        self.status_sort_order = {"Running": 0, "Enabled": 1, "Disabled": 2}

    @property
    def viewport_height(self) -> int:
        try:
            return self.console.height - 8
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
                    current_status = info.get("pending_status", info["status"])
                    info["pending_status"] = "Enabled" if current_status == "Disabled" else "Disabled"
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
            display_status = info.get("pending_status", info["status"])
            
            if "pending_status" in info and info["pending_status"] != info["status"]:
                status_icon, status_style = "🔄", "yellow"
            elif display_status == "Running":
                status_icon, status_style = "🟢", "green"
            elif display_status == "Enabled":
                status_icon, status_style = "🟡", "green"
            else:  # Disabled
                status_icon, status_style = "🔴", "red"

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

        # Display current status
        live_status = info['status']
        status_styles = {"Running": "green", "Enabled": "green", "Disabled": "red"}
        details_text.append("Status: ", style="bold yellow").append(f"{live_status}\n", style=status_styles.get(live_status, "default"))
        
        # Display pending status change
        pending_status = info.get('pending_status')
        if pending_status and pending_status != live_status:
            pending_color = "green" if pending_status == "Enabled" else "red"
            details_text.append("Pending: ", style="bold yellow").append(f"{pending_status} (press Enter to apply)\n", style=pending_color)

        details_text.append("\nDescription:\n", style="bold yellow").append(f"{info['description']}\n\n")
        impact_text = info["impact"]
        impact_style = "bold red" if "CRITICAL" in impact_text.upper() else "default"
        details_text.append("Impact of Disabling:\n", style="bold yellow").append(impact_text, style=impact_style)

        return Panel(details_text, title="Details", border_style="green")

    def confirm_and_apply(self, live):
        changes = [(s, i) for c in self.services_data.values() for s, i in c.items() if "pending_status" in i and i["pending_status"] != i["status"]]

        if not changes:
            live.update(Panel(Text("No changes to apply.", justify="center")))
            time.sleep(1.5)
            return

        live.update(Panel(self.generate_command_table(changes), title="[bold yellow]Confirm Changes"))
        self.console.print(Panel(Text("Press 'y' to apply, any other key to cancel.", justify="center")))
        key = self.read_key()

        if key.lower() == "y":
            with Progress(console=self.console, transient=False) as progress:
                task = progress.add_task("[cyan]Applying changes...", total=len(changes))
                for service, info in changes:
                    action_str = info["pending_status"] # Will be "Enabled" or "Disabled"
                    command_action = "enable" if action_str == "Enabled" else "disable"
                    
                    target_domain = f"system/{service}" if info["type"] == "daemon" else f"gui/{self.uid}/{service}"
                    command = (["sudo", "launchctl", command_action, target_domain] if info["type"] == "daemon" else ["launchctl", command_action, target_domain])
                    
                    subprocess.run(command, capture_output=True, text=True, check=False)

                    # Update the base status after applying
                    # A service might not become "Running" immediately after being enabled, so we set it to "Enabled".
                    info["status"] = "Enabled" if command_action == "enable" else "Disabled"
                    del info["pending_status"]
                    progress.update(task, advance=1, description=f"[cyan]{command_action.capitalize()}d {service}")

            live.update(Panel(Text("✅ Changes applied successfully. Rescanning services...", justify="center"), style="green"))
            time.sleep(2)
            # Rescan to reflect accurate running state
            self.services_data = get_live_services(self.console)
        else:
            for _, info in changes: del info["pending_status"]
            live.update(Panel(Text("❌ Changes cancelled.", justify="center"), style="red"))
            time.sleep(1.5)

    def generate_command_table(self, changes: List[Tuple[str, Dict]]) -> Table:
        # (Same as previous version, but logic simplified)
        table = Table(title="Commands to be Executed", expand=True)
        table.add_column("Action", style="cyan", justify="right")
        table.add_column("Service Target", style="magenta")
        for service, info in changes:
            action = "disable" if info["pending_status"] == "Disabled" else "enable"
            target = f"system/{service}" if info["type"] == "daemon" else f"gui/{self.uid}/{service}"
            cmd_prefix = "sudo " if info["type"] == "daemon" else ""
            table.add_row(f"{cmd_prefix}launchctl {action}", target)
        return table

    def run(self):
        # (Main loop logic modified slightly for re-scan)
        if not sys.stdin.isatty():
            self.console.print("[bold red]This application requires an interactive terminal.[/]")
            return
            
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            with Live(self.draw_layout(), screen=True, transient=True, refresh_per_second=20) as live:
                while not self.exit_app:
                    action = self.handle_input(self.read_key())
                    
                    if action == "apply":
                        live.stop()
                        self.confirm_and_apply(live) # This method now handles the rescan
                        live.start()
                    
                    live.update(self.draw_layout())
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
        console.print("Please run as: sudo python3 your_script_name.py")
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