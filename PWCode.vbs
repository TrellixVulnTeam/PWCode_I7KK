set WshShell = WScript.CreateObject("WScript.Shell" )
set FSO = WScript.CreateObject("Scripting.FileSystemObject")

SCRIPTPATH = Left(WScript.ScriptFullName, Len(WScript.ScriptFullName) - Len(WScript.ScriptName)) & "bin\"
PYTHON_BIN=SCRIPTPATH & "vendor\windows\python\pythonw.exe"
JAVA_BIN=SCRIPTPATH & "vendor\windows\jre\bin\javaw.exe"
OJDBC10=SCRIPTPATH & "vendor\jars\ojdbc10.jar"
PWCODE_BIN=SCRIPTPATH & "pwcode.py"
WIM_BIN=SCRIPTPATH & "vendor\windows\wimlib\wimlib-imagex.exe"
JARS=SCRIPTPATH & "vendor\jars\sqlworkbench.jar"
cmd = PYTHON_BIN & " " & PWCODE_BIN

paths = Array(PYTHON_BIN, JAVA_BIN, OJDBC10, WIM_BIN, JARS)

Installed = vbTrue
For Each path In paths
    If Not FSO.FileExists(path) Then
		  Installed = vbFalse
    End If
Next


WshShell.CurrentDirectory = SCRIPTPATH
If Not Installed Then
  Answer = Msgbox("Missing dependencies! Download now?", vbYesNo+vbCritical, "PWCode Installer")
  If Answer = vbYes Then
    WshShell.run("powershell -executionpolicy bypass -noexit -file vendor\windows\download_deps.ps1")
  End If
Else
  ' WScript.Echo cmd
  ' WAIT: Find method for waiting for completion of powershell script so that pwcode can be launched immediately after install
  wshShell.Run cmd, 1
End If









