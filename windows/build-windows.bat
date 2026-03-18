@echo off
setlocal

py -m pip install --upgrade pip pyinstaller
py -m pip install PySide6
py -m pip install psutil
py -m pip install Pillow

if not exist "app_icon.ico" (
  py -c "from PIL import Image, ImageDraw; im=Image.new('RGBA',(256,256),(55,122,255,255)); d=ImageDraw.Draw(im); d.rounded_rectangle((24,24,232,232), radius=48, fill=(26,40,75,255)); d.rectangle((118,56,138,200), fill=(255,255,255,255)); d.rectangle((72,112,184,132), fill=(255,255,255,255)); im.save('app_icon.ico', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"
)

py -m PyInstaller --noconfirm --clean MiniOSHelper.spec

echo.
echo Build complete. Output: dist\MiniOSHelper\
endlocal
