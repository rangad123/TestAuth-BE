
!define APPNAME "TesterAlly-Installer"
!define INSTALLDIR "$PROGRAMFILES\${APPNAME}"

OutFile "TesterAlly.exe"
InstallDir ${INSTALLDIR}

Section "Install"
    SetOutPath "$INSTDIR"

    ; Copy only launcher.exe and manage.exe
    File "D:\Demo\TestAuth-BE\dist\run.exe"
    File "D:\Demo\TestAuth-BE\dist\manage.exe"
    File "D:\Demo\TestAuth-BE\.env"

    ; Create shortcut on Desktop
    CreateShortcut "$DESKTOP\TesterAllyApp.lnk" "$INSTDIR\run.exe"

    ; Run the launcher after installation
    ExecShell "" "$INSTDIR\run.exe"

    ; Write uninstall information
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Delete shortcut
    Delete "$DESKTOP\TesterAllyApp.lnk"

    ; Remove installed directory
    RMDir /r "$INSTDIR"

    ; Remove uninstaller
    Delete "$INSTDIR\Uninstall.exe"
SectionEnd

