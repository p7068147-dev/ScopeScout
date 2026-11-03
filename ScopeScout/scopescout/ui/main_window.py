from scopescout.ui.dashboard import DashboardWindow
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
)

from scopescout.platforms.interfaces import (
    discover_interfaces,
    validate_interface,
)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.selected_interface = None

        self.setWindowTitle("ScopeScout")
        self.resize(1000, 650)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #10151b;
            }

            QLabel {
                color: #e4eeee;
            }

            QComboBox {
                background-color: #202a33;
                color: white;
                padding: 12px;
                border: 1px solid #35d5c0;
                border-radius: 6px;
            }

            QPushButton {
                background-color: #173d3a;
                color: #35d5c0;
                padding: 12px;
                border: 1px solid #35d5c0;
                border-radius: 6px;
            }

            QPushButton:disabled {
                background-color: #252b30;
                color: #777777;
                border-color: #444444;
            }
        """)

        self.create_startup_screen()
        self.refresh_interfaces()

    def create_startup_screen(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(70, 60, 70, 60)
        layout.setSpacing(22)

        title = QLabel("SCOPESCOUT")
        title.setStyleSheet(
            "font-size: 34px; font-weight: bold; color: #35d5c0;"
        )

        subtitle = QLabel(
            "NETWORK & WIRELESS SECURITY WORKSTATION"
        )

        heading = QLabel("Select your wireless interface")
        heading.setStyleSheet("font-size: 20px;")

        description = QLabel(
            "Choose the network adapter ScopeScout should use. "
            "An interface must be selected before continuing."
        )
        description.setWordWrap(True)

        self.interface_box = QComboBox()
        self.interface_box.currentIndexChanged.connect(
            self.update_selection
        )

        self.status_label = QLabel(
            "Searching for wireless interfaces..."
        )

        buttons = QHBoxLayout()

        self.refresh_button = QPushButton(
            "Refresh interfaces"
        )
        self.refresh_button.clicked.connect(
            self.refresh_interfaces
        )

        self.continue_button = QPushButton(
            "Continue"
        )
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(
            self.open_dashboard
        )

        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.continue_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(45)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self.interface_box)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addLayout(buttons)

        self.setCentralWidget(central)

    def refresh_interfaces(self):
        self.interface_box.clear()
        self.selected_interface = None
        self.continue_button.setEnabled(False)

        try:
            interfaces = discover_interfaces()

            for interface in interfaces:
                self.interface_box.addItem(
                    f"{interface.name} — {interface.description}",
                    interface.name,
                )

            if interfaces:
                self.status_label.setText(
                    f"Found {len(interfaces)} wireless interface(s)."
                )
                self.interface_box.setCurrentIndex(-1)
            else:
                self.status_label.setText(
                    "No wireless interfaces detected. "
                    "Check your adapter and refresh."
                )

        except Exception as error:
            self.status_label.setText(
                f"Interface discovery failed: {error}"
            )

    def update_selection(self):
        name = self.interface_box.currentData()

        self.selected_interface = name
        self.continue_button.setEnabled(
            bool(name)
        )

        if name:
            self.status_label.setText(
                f"Selected interface: {name}"
            )

    def open_dashboard(self):
        name = self.selected_interface

        if not name or not validate_interface(name):
            self.status_label.setText(
                "Interface unavailable. Please select again."
            )
            self.refresh_interfaces()
            return

        self.dashboard = DashboardWindow(
            interface_name=name,
            parent=self,
        )

        self.dashboard.show()
        self.hide()