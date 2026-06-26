Set WShell = CreateObject("WScript.Shell")
Set http = CreateObject("MSXML2.XMLHTTP")
Dim alreadyRunning
alreadyRunning = False
On Error Resume Next
http.Open "GET", "http://localhost:5000/health", False
http.Send
If http.Status = 200 Then
    alreadyRunning = True
End If
On Error GoTo 0
If Not alreadyRunning Then
    PYTHON_EXE = "C:\Users\bryan\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe"
    INSTALL_DIR = "C:\nfse-automation"

    ' Run updater.py with a hard timeout (45s) so a hung network call
    ' never blocks the app from launching with whatever code is on disk.
    Set cmdShell = WShell.Exec("""" & PYTHON_EXE & """ """ & INSTALL_DIR & "\updater.py""")

    startTime = Timer
    Do
        WScript.Sleep 500
        If cmdShell.Status = 1 Then
            Exit Do
        End If
        If Timer - startTime > 45 Then
            On Error Resume Next
            cmdShell.Terminate
            On Error GoTo 0
            Exit Do
        End If
    Loop

    WShell.Run """" & PYTHON_EXE & """ """ & INSTALL_DIR & "\app.py""", 0, False
    WScript.Sleep 1000
    Do
        WScript.Sleep 2000
        On Error Resume Next
        Set http = CreateObject("MSXML2.XMLHTTP")
        http.Open "GET", "http://localhost:5000/health", False
        http.Send
        If http.Status = 200 Then
            Exit Do
        End If
        On Error GoTo 0
    Loop
End If
WShell.Run "http://localhost:5000", 1, False
