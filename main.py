"""
Application Entrypoint for Windows Office Time Widget.
Handles Single Instance Mutex via QLocalServer, High DPI scaling,
Tray Manager, and Qt event loop lifecycle.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from PySide6.QtCore import QIODevice, Qt
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from config import config
from tray_manager import TrayManager
from widget import OfficeTimeWidget

APP_SERVER_NAME = "OfficeTimeWidgetSingleInstanceServer"


class SingleInstanceApplication(QApplication):
    """QApplication subclass that ensures only a single instance runs at a time."""

    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("OfficeTimeWidget")
        self.setOrganizationName("OfficeTime")
        self.setQuitOnLastWindowClosed(False)

        # Set App Icon if exists
        icon_path = Path(__file__).parent / "resources" / "app_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.server: QLocalServer = None
        self.widget: OfficeTimeWidget = None
        self.tray: TrayManager = None

    def check_single_instance(self) -> bool:
        """
        Attempts to connect to an existing local server instance.
        If found, sends a message to raise that instance and returns False.
        Otherwise starts a local server and returns True.
        """
        socket = QLocalSocket()
        socket.connectToServer(APP_SERVER_NAME)
        if socket.waitForConnected(500):
            # Existing instance found! Send wake-up ping
            socket.write(b"WAKE_UP")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            return False

        # Clean up stale socket server if prior crash
        QLocalServer.removeServer(APP_SERVER_NAME)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._handle_new_connection)
        self.server.listen(APP_SERVER_NAME)
        return True

    def _handle_new_connection(self):
        client = self.server.nextPendingConnection()
        if client:
            client.waitForReadyRead(500)
            data = client.readAll().data().decode("utf-8")
            if data == "WAKE_UP" and self.widget:
                self.widget.show()
                self.widget.raise_()
                self.widget.activateWindow()
            client.disconnectFromServer()


def main():
    # Set DPI awareness & rendering attributes
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = SingleInstanceApplication(sys.argv)

    if not app.check_single_instance():
        print("Office Time Widget is already running. Switched to active instance.")
        sys.exit(0)

    # Initialize main widget & system tray
    widget = OfficeTimeWidget()
    tray = TrayManager(widget)

    app.widget = widget
    app.tray = tray

    # Connect Widget state updates to Tray
    widget.state_changed.connect(tray.update_tray_state)

    # Connect Tray menu actions to Widget methods
    def toggle_widget():
        if widget.isVisible() and not widget.isMinimized():
            widget.hide()
        else:
            widget.show()
            widget.raise_()
            widget.activateWindow()

    tray.request_toggle_widget.connect(toggle_widget)
    tray.request_open_reports.connect(widget.open_reports)
    tray.request_open_settings.connect(widget.open_settings)
    tray.request_clock_in.connect(widget._toggle_punch)
    tray.request_clock_out.connect(widget._toggle_punch)
    tray.request_start_break.connect(widget._toggle_break)
    tray.request_end_break.connect(widget._toggle_break)

    def on_export_excel():
        widget.open_reports()
        if widget.report_window:
            widget.report_window._on_export_excel()

    tray.request_export_excel.connect(on_export_excel)
    tray.request_exit.connect(app.quit)

    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
