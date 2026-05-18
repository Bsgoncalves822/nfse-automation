Set WShell = CreateObject("WScript.Shell")
Set http = CreateObject("MSXML2.XMLHTTP")

' Check if Flask is already running
Dim alreadyRunning
alreadyRunning = False

On Error Resume Next
http.Open "GET", "http://localhost:5000/health", False
http.Send
If http.Status = 200 Then
    alreadyRunning = True
End If
On Error GoTo 0

' Only start Flask if not already running
If Not alreadyRunning Then
    WShell.Run "python C:\nfse-automation\app.py", 0, False
    WScript.Sleep 1000

    ' Wait until Flask is ready
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

' Open browser
WShell.Run "http://localhost:5000", 1, False