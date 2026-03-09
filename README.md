# Mini OS Helper

GTK4 desktop utility for quick system checks, shortcuts, and notes.

## Features

- Live CPU, RAM, disk, battery, and uptime snapshot
- Quick actions for folders, websites, and shell commands
- Notes tab with persistent local storage
- Rounded GTK4 styling with light/dark preference

## Dependencies

### Runtime

- Python 3.11+
- GTK4 + PyGObject
- `xdg-utils`
- Optional: `psutil` for richer system metrics

### Install dependencies by distro

#### Arch Linux / Nyarch

```bash
sudo pacman -S --needed python python-gobject gtk4 xdg-utils python-psutil
```

#### Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-4.0 xdg-utils python3-psutil
```

#### Fedora

```bash
sudo dnf install -y python3 python3-gobject gtk4 xdg-utils python3-psutil
```

## Run from source

```bash
cd /home/'your username'/Documents/mini-os-helper
python3 main.py
```

## Build AppImage

### Build requirements

```bash
python3 -m pip install --user pyinstaller
```

Install `appimagetool` in `PATH`, or place one of these files in `./tools/`:

- `appimagetool.AppImage`
- `appimagetool-x86_64.AppImage`

### Build command

```bash
cd /home/'your username'/Documents/mini-os-helper
chmod +x build-appimage.sh
./build-appimage.sh
```

The script outputs an `.AppImage` file in the project root.
