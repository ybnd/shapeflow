@if (@CodeSection == @Batch) @then

@echo off
set PYTHONPATH=%cd%;%PYTHONPATH%
rem Enter the prefill value in the keyboard buffer
CScript //nologo //E:JScript "%~F0" "py %*"
cmd
goto :EOF

@end

WScript.CreateObject("WScript.Shell").SendKeys(WScript.Arguments(0)+"{ENTER}");