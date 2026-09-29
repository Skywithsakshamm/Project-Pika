"""
PySide6 Native Windows Desktop Floating Assistant for Selvie.
Provides a sleek, frameless, transparent overlay with system tray integration and Ctrl+Space hotkey.
"""
import sys
import os
import threading
import time
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, QUrl, Slot, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

from config.settings import settings
from backend.automation.hotkey import global_hotkey

def run_uvicorn_backend():
    """Run FastAPI uvicorn server in a separate background thread."""
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, log_level="warning")

class FloatingAssistantWindow(QMainWindow):
    def __init__(self, target_url: str):
        super().__init__()
        self.target_url = target_url
        self.drag_position = QPoint()

        # Frameless, transparent, always on top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # WebEngine View
        self.browser = QWebEngineView(self)
        self.browser.page().setBackgroundColor(QColor(0, 0, 0, 0)) # transparent background

        # Enable audio capture & autoplay
        page_settings = self.browser.settings()
        page_settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        page_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        page_settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)

        self.setCentralWidget(self.browser)

        # Initial Dimensions & Screen Positioning (Bottom right or top right floating)
        self.resize(460, 720)
        self._position_on_screen()

        # Load UI
        self.browser.load(QUrl(self.target_url))

        # Setup System Tray
        self._setup_tray()

        # Setup Global Hotkey Callback
        global_hotkey.start(callback=self._on_hotkey_triggered)

    def _position_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        margin_x = 40
        margin_y = 60
        x = screen.width() - self.width() - margin_x
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        avatar_path = str(settings.ASSETS_DIR / "selvie_avatar.jpg")
        if os.path.exists(avatar_path):
            self.tray.setIcon(QIcon(avatar_path))
            self.setWindowIcon(QIcon(avatar_path))
        else:
            self.tray.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_ComputerIcon))

        menu = QMenu()
        show_action = menu.addAction("Show / Hide Selvie (Ctrl+Space)")
        show_action.triggered.connect(self.toggle_visibility)

        listen_action = menu.addAction("Start Voice Listening")
        listen_action.triggered.connect(self.trigger_listening)

        menu.addSeparator()
        quit_action = menu.addAction("Quit Selvie")
        quit_action.triggered.connect(self._quit_application)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Selvie AI Desktop Assistant")
        self.tray.show()
        self.tray.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_hotkey_triggered(self):
        """Called from Win32 background thread when Ctrl+Space is pressed."""
        QTimer.singleShot(0, self._handle_hotkey_main_thread)

    def _handle_hotkey_main_thread(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.trigger_listening()

    def trigger_listening(self):
        """Invoke voice recognition inside the web UI."""
        self.browser.page().runJavaScript(
            "if (window.selvieToggleListening) { window.selvieToggleListening(); }"
        )

    def _quit_application(self):
        global_hotkey.stop()
        QApplication.quit()

    # Window drag handling
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

def main():
    # 1. Start FastAPI backend in background thread
    t = threading.Thread(target=run_uvicorn_backend, daemon=True)
    t.start()
    time.sleep(1.0) # Wait brief moment for backend to bind

    # 2. Launch PySide6 GUI
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep tray alive

    url = f"http://127.0.0.1:{settings.PORT}"
    window = FloatingAssistantWindow(url)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
