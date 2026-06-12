Set WShell = CreateObject("WScript.Shell")
WShell.Run "C:\Users\bryan\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe C:\Users\bryan\Downloads\nfse-automation-setup\nfse-automation\app.py", 0, False

WScript.Sleep 1000

Do
    WScript.Sleep 2000
    On Error Resume Next
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", "http://localhost:5000/health", False
    http.Send
    If http.Status = 200 Then
        WShell.Run "http://localhost:5000", 1, False
        Exit Do
    End If
    On Error GoTo 0
Loop
