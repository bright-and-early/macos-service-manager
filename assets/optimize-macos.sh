# MacOS:

sudo ./createinstallmedia --volmue /Volumes/Install\ macOS\ Sonoma/

# Rust
export RUSTUP_HOME=/opt/Rust/.rustup
export CARGO_HOME=/opt/Rust/.cargo
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- --default-toolchain nightly --component rustc-codegen-cranelift

# brew
/bin/bash -c "$(curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew analytics off
brew install starship zsh-autocomplete zsh-autosuggestions zsh-fast-syntax-highlighting wget zigup git go gopls —cask stolendata-mpv qview
brew install --ignore-dependencies zls cargo-zigbuild

# ~/.zshrc
source /usr/local/share/zsh-autocomplete/zsh-autocomplete.plugin.zsh
source /usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh
source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
eval "$(starship init zsh)"
fpath+=~/.zfunc

rustup completions zsh > ~/.zfunc/_rustup
rustup completions zsh cargo > ~/.zfunc/_cargo


#unlock homebrew 
rm -rf /usr/local/var/homebrew/locks

/var/log
/var/logs
sudo chflags noschg,nouchg . && sudo rm -rf * && sudo chflags schg,uchg .

chsh -s /bin/zsh

sudo mdutil -i off -a
sudo mdutil -i on -a

sudo mdutil -d /System/Volumes/Preboot /opt

# https://dns11.quad9.net/dns-query

sudo launchctl disable gui/501/com.apple.XProtect.agent.scan.startup
sudo launchctl disable gui/501/com.apple.XProtect.agent.scan
sudo launchctl disable system/com.apple.XProtect.daemon.scan
sudo launchctl disable system/com.apple.XProtect.daemon.scan.startup

sudo launchctl disable system/com.apple.PerfPowerServices
sudo launchctl disable system/com.apple.PerfPowerServicesExtended

defaults write com.apple.desktopservices DSDontWriteNetworkStores true

sudo launchctl disable system/com.apple.news.today
sudo launchctl disable system/com.apple.news.todayintents
sudo launchctl disable system/com.apple.news.tag

sudo launchctl disable system/com.apple.HomeWidget
sudo launchctl disable system/com.apple.HomeEnergyWidgetsExtension
launchctl disable user/$(id -u)/com.apple.HomeWidget
launchctl disable user/$(id -u)/com.apple.HomeEnergyWidgetsExtension
sudo launchctl disable gui/$(id -u)/com.apple.HomeWidget
sudo launchctl disable gui/$(id -u)/com.apple.HomeEnergyWidgetsExtension


xcrun simctl delete unavailable

defaults write com.apple.screencapture type heic;killall SystemUIServer

# boot volume in macOS
csrutil disable
csrutil authenticated-root disable
sudo bless --folder /[mountpath]/System/Library/CoreServices --bootefi --create-snapshot

#disable OCSP 
sudo defaults write /Library/Preferences/com.apple.security.revocation.plist OCSPStyle None
sudo defaults write /Library/Preferences/com.apple.security.revocation.plist CRLStyle None
sudo defaults write com.apple.security.revocation.plist OCSPStyle None
sudo defaults write com.apple.security.revocation.plist CRLStyle None

dsenableroot 
csrutil disable; csrutil enable
reboot
Disable Gatekeeper
sudo spctl --master-disable
DevToolsSecurity -enable
sudo pmset -a powernap 0

# Disable the "Are you sure you want to open this application?" dialog
defaults write com.apple.LaunchServices LSQuarantine -bool false
sudo spctl --master-disable

# Disable Disk Image Verification: Verifying ...
defaults write  com.apple.frameworks.diskimages skip-verify -bool true
defaults write  com.apple.frameworks.diskimages skip-verify-locked -bool true
defaults write  com.apple.frameworks.diskimages skip-verify-remote -bool true

sudo rm -rf /Applications/News.app

xcrun simctl delete unavailable
defaults write com.apple.iphonesimulator AllowFullscreenMode -bool YES
defaults write com.apple.dt.Xcode ShowBuildOperationDuration YES
defaults write com.apple.dt.Xcode BuildSystemScheduleInherentlyParallelCommandsExclusively -bool YES

defaults write .GlobalPreferences MultipleSessionsEnabled -bool TRUE

defaults write "Apple Global Domain" MultipleSessionsEnabled -bool true
defaults write com.apple.loginwindow TALLogoutSavesState -bool false
defaults write -g network_enable-l4s -bool true
defaults write com.apple.finder CalculateAllSizes -bool false

defaults write -g NSAutomaticWindowAnimationsEnabled -bool false
defaults write -g NSWindowResizeTime -float 0.001
defaults write -g NSToolbarFullScreenAnimationDuration -float 0
defaults write -g NSToolbarTitleViewRolloverDelay -float 0
defaults write -g NSDocumentRevisionsWindowTransformAnimation -bool false
defaults write -g QLPanelAnimationDuration -float 0
defaults write -g NSScrollAnimationEnabled -bool false
defaults write -g NSBrowserColumnAnimationSpeedMultiplier -float 0
defaults write -g NSScrollViewRubberbanding -bool false
defaults write com.apple.CrashReporter DialogType none	
defaults write com.apple.finder DisableAllAnimations -bool true
defaults write com.apple.finder AnimateInfoPanes -bool false
defaults Write com.apple.finder AnimateSnapToGrid -bool false
defaults write com.apple.finder FXEnableSlowAnimation -bool false
defaults write com.apple.finder QLEnableSlowMotion -bool false
defaults write com.apple.dock expose-animation-duration -float 0
defaults write com.apple.dock workspaces-swoosh-animation-off -bool YES	
defaults write com.apple.dock launchanim -bool false
defaults write com.apple.dock workspaces-edge-delay -float 0
defaults write com.apple.dock autohide-time-modifier -float 0
defaults write com.apple.dock autohide-delay -float 0
defaults write com.apple.dock springboard-show-duration -float 0
defaults write com.apple.dock springboard-hide-duration -float 0
defaults write com.apple.dock sopringboard-page-duration -float 0

defaults write com.apple.universalaccess reduceTransparency -bool true
sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -deactivate -stop
defaults write com.apple.Terminal FocusFollowsMouse -string YES
defaults write com.apple.finder AppleShowAllFiles true
defaults write com.apple.finder ShowStatusBar -bool true
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true
sudo defaults write /Library/Preferences/com.apple.driver.AppleIRController DeviceEnabled -int 0
sudo defaults write /System/Library/LaunchDaemons/com.apple.mDNSResponder.plist ProgramArguments -array-add "-NoMulticastAdvertisements"
defaults write com.apple.NetworkBrowser BrowseAllInterfaces -bool true
sudo nvram BootAudio=%00
sudo nvram StartupMute=%01


defaults write com.apple.Mail DisableSendAnimations -bool true
defaults write com.apple.Mail DisableReplyAnimations -bool true

defaults write com.apple.Safari WebKitInitialTimedLayoutDelay 0.1
defaults write com.apple.Safari WebKitResourceTimedLayoutDelay 0.1


launchctl unload -w /System/Library/LaunchAgents/com.apple.diagnostics_agent.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.diagnosticextensionsd.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.symptomsd-diag.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.spindump_agent.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.ReportCrash.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.ReportPanic.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.sysdiagnose_agent.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.generativeexperiencesd.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.UsageTrackingAgent.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.parentalcontrols.check.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.photoanalysisd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.financed.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.ensemble.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.ndoagent.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.icloud.searchpartyuseragent.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.assistantd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.transparencyd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.peopled.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.familycircled.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.familycontrols.useragent.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.familynotificationd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.progressd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.macos.studentd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.routined.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.homed.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.homeenergyd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.newsd.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.gamed.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.siriinferenced.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.corespeechd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.siriknowledged.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.siriactionsd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.amsengagementd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.mediaanalysisd.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.ContextStoreAgent.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.FollowUpUI.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.followupd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.suggestd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.lockdownmoded.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.knowledge-agent.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.intelligenceplatformd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.BiomeAgent.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.WiFiVelocityAgent.plist 
launchctl unload -w /System/Library/LaunchAgents/com.apple.triald.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.rapportd-user.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.voicebankingd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.accessibility.axassetsd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.accessibility.heard.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.helpd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.feedbackd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.textunderstandingd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.coreservices.useractivityd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.recentsd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.duetexpertd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.betaenrollmentd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.geoanalyticsd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.inputanalyticsd.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.geodMachServiceBridge.plist
launchctl unload -w /System/Library/LaunchAgents/com.apple.naturallanguaged.plist

sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.ReportCrash.Root.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.ReportMemoryException.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.symptomsd-diag.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.symptomsd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.CrashReporterSupportHelper.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.DumpPanic.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.DumpGPURestart.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.icloud.findmydeviced.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.findmymac.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.findmymacmessenger.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.spindump.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.tailspind.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.SubmitDiagInfo.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.awdd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.rapportd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.diagnosticd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.aslmanager.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.triald.system.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.familycontrols.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.sysdiagnose.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.analyticsd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.wifianalyticsd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.wifivelocityd.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.systemstats.analysis.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.systemstats.daily.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.audioanalyticsd.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.osanalytics.osanalyticshelper.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.watchdogd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.ocspd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.contextstored.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.biomed.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.mobileassetd.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.PerfPowerServices.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.powerlogHelperd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.applessdstatistics.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.icloud.searchpartyd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.GameController.gamecontrollerd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.dprivacyd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.coreduetd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.modelcatalogd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.modelmanagerd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.rtcreportingd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.mediaremoted.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.nearbyd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.sandboxd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.aneuserd.plist 
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.ospredictiond.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.aned.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.periodic-*.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.systemstats.microstackshot_periodic.plist

sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.logd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.syslogd.plist
sudo launchctl unload -w /System/Library/LaunchDaemons/com.apple.newsyslog.plist