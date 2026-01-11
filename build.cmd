@echo off
mkdir bin
mkdir obj
@rem i hate Visual Studio.
call "D:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat"
cd obj
cl.exe ..\engine\*.c /Fe:..\game.exe /I..\include /GA /O2
cd ..
