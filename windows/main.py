import os

if os.name == "nt":
    from pyside_ui import MiniOSHelperQtApp
else:
    from ui import MiniOSHelperApp


def main():
    if os.name == "nt":
        MiniOSHelperQtApp.run_app()
    else:
        app = MiniOSHelperApp()
        app.run(None)


if __name__ == "__main__":
    main()
