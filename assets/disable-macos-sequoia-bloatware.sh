#!/bin/zsh

# =============================================================================
# == User-Specific Services (GUI)
# =============================================================================

# 🧠 Siri & Intelligence
TODISABLE_USER+=(
	'com.apple.assistantd'                   # Breaks Siri and Dictation.
	'com.apple.corespeechd'                  # Breaks "Hey Siri" and voice input.
	'com.apple.siriactionsd'                 # Breaks Siri Shortcuts.
	'com.apple.Siri.agent'                   # Breaks the Siri user interface.
	'com.apple.sirittsd'                     # Breaks Siri's voice (Text-to-Speech).
	'com.apple.suggestd'                     # Breaks Spotlight and Safari suggestions.
	'com.apple.studentd'                     # Breaks Classroom student features.
	'com.apple.parsecd'                      # Breaks core engine for Siri suggestions.
	#'com.apple.intelligenceplatformd'        # Breaks many "proactive" OS features.
	#'com.apple.routined'                     # Breaks significant location and routine-based suggestions.
	'com.apple.generativeexperiencesd'       # Breaks future generative AI features in macOS.
)

# ☁️ iCloud & Cloud Services
TODISABLE_USER+=(
	'com.apple.cloudd'                       # Breaks iCloud Drive file syncing.
	'com.apple.cloudphotod'                  # Breaks iCloud Photos syncing.
	'com.apple.CloudSettingsSyncAgent'       # Breaks iCloud sync for system and app settings.
	# 'com.apple.icloudmailagent'              # Breaks iCloud Mail.
	'com.apple.itunescloudd'                 # Breaks Apple Music and iTunes Match library sync.
	'com.apple.security.cloudkeychainproxy3' # Breaks iCloud Keychain password syncing.
)

# 📍 Location & Find My Services
TODISABLE_USER+=(
	'com.apple.CoreLocationAgent'            # Breaks location services for all apps (Maps, Weather).
	'com.apple.findmy.findmylocateagent'     # Breaks the "Find My" feature for this Mac.
	'com.apple.icloud.searchpartyuseragent'  # Breaks offline finding via the crowdsourced Find My network.
)

# 👪 Family & Screen Time
TODISABLE_USER+=(
	#'com.apple.familycircled'                # Breaks all Family Sharing features.
	'com.apple.familycontrols.useragent'     # Breaks Parental Controls.
	'com.apple.ScreenTimeAgent'              # Breaks Screen Time tracking and limits.
)

# 📸 Media, Photos & Entertainment
TODISABLE_USER+=(
	'com.apple.photoanalysisd'               # Breaks Photos app's face/object recognition and search.
	#'com.apple.photolibraryd'                # Breaks the Photos app library manager; can cause corruption.
	'com.apple.gamed'                        # Breaks Game Center.
	'com.apple.newsd'                        # Breaks the Apple News app and widget.
	#'com.apple.avconferenced'                # Breaks FaceTime audio and video.
)

# 🤝 Sharing, Handoff & Connectivity
TODISABLE_USER+=(
	'com.apple.sharingd'                     # Breaks AirDrop, Handoff, and Universal Clipboard.
	'com.apple.rapportd'                     # Breaks communication with other Apple devices (Sidecar, HomePod).
	#'com.apple.sidecar-relay'                # Breaks using an iPad as a second display (Sidecar).
)

# 🖥️ Screen Sharing & QuickLook
TODISABLE_USER+=(
	'com.apple.quicklook.ThumbnailsAgent'    # Breaks file thumbnail generation in Finder.
	'com.apple.quicklook'                    # Breaks the Quick Look feature (spacebar preview).
	'com.apple.screensharing.agent'          # Breaks incoming screen sharing connections.
)

# 📢 Advertising & Analytics
TODISABLE_USER+=(
	#'com.apple.ap.promotedcontentd'          # Breaks ads in App Store and News.
	#'com.apple.triald'                       # Opts you out of Apple's experimental feature trials.
)

# ♿ Accessibility
TODISABLE_USER+=(
	#'com.apple.universalaccessd'             # Breaks all Accessibility features (VoiceOver, Zoom, etc.).
)

# ⚙️ Miscellaneous System Agents
TODISABLE_USER+=(
	'com.apple.homed'                        # Breaks HomeKit for controlling smart home devices.
	#'com.apple.imagent'                      # Breaks iMessage and FaceTime account sign-in.
	#'com.apple.passd'                        # Breaks Wallet & Apple Pay.
	'com.apple.remindd'                      # Breaks the Reminders app and its alerts.
	'com.apple.TMHelperAgent'                # Breaks the Time Machine menu bar icon and helper functions.
	#'com.apple.weatherd'                     # Breaks the Weather app and widget.
)

# Execute the disabling for User services
for agent in "${TODISABLE_USER[@]}"
do
  launchctl bootout gui/501/"${agent}"
  launchctl disable gui/501/"${agent}"
done


# =============================================================================
# == System-Wide Services
# =============================================================================

# 📈 System Analytics & Diagnostics
TODISABLE_SYSTEM+=(
	'com.apple.analyticsd'                 # Stops sending system diagnostic data to Apple.
	'com.apple.wifianalyticsd'               # Stops sending Wi-Fi diagnostic data to Apple.
)

# 💾 Time Machine Backup
TODISABLE_SYSTEM+=(
	'com.apple.backupd'                    # Breaks Time Machine backups entirely.
	'com.apple.backupd-helper'               # Helper for Time Machine; disabling also breaks backups.
)

# 🔎 System-Level Find My & iCloud
TODISABLE_SYSTEM+=(
	#'com.apple.findmymac'                  # Breaks Find My Mac service.
	#'com.apple.icloud.searchpartyd'          # Breaks offline finding capability (crucial for Find My).
)

# ⚙️ Miscellaneous System Services
TODISABLE_SYSTEM+=(
	'com.apple.GameController.gamecontrollerd' # Breaks support for game controllers/gamepads.
	#'com.apple.locationd'                    # System-wide location daemon; breaks all location services.
	#'com.apple.screensharing'                # Breaks screen sharing functionality at the system level.
)


# Execute the disabling for System services
for agent in "${TODISABLE_SYSTEM[@]}"
do
  launchctl bootout system/"${agent}"
  launchctl disable system/"${agent}"
done

echo "Done. A restart may be required for all changes to take effect."