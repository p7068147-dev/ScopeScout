
import socket
from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
)
from scopescout.network_discovery import NetworkScanWorker


class DashboardWindow(QMainWindow):
    def __init__(self, interface_name, parent=None):
        super().__init__(parent)
     
        self.interface_name = interface_name
        
        self.scan_worker = None
        self.devices = []

        self.scan_timer = QTimer(self)
        self.scan_timer.setInterval(10_000)
        self.scan_timer.timeout.connect(self.start_scan)

        self.setWindowTitle("ScopeScout — Security Workstation")
        self.resize(1400, 850)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0b1118;
                color: #dce8e8;
                font-family: Arial;
            }

            QLabel {
                color: #dce8e8;
            }

            QPushButton {
                background-color: #14232c;
                color: #42e6ce;
                border: 1px solid #24534f;
                border-radius: 5px;
                padding: 11px;
                text-align: left;
            }

            QPushButton:hover {
                background-color: #1b383c;
                border: 1px solid #42e6ce;
            }

            QFrame#Panel {
                background-color: #111d26;
                border: 1px solid #203943;
                border-radius: 8px;
            }
        """)

        self.create_dashboard()

    def create_dashboard(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # LEFT NAVIGATION
        sidebar = QFrame()
        sidebar.setFixedWidth(235)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(10)

        logo = QLabel("SCOPE SCOUT")
        logo.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #42e6ce;"
        )

        subtitle = QLabel("NETWORK SECURITY WORKSTATION")
        subtitle.setStyleSheet("font-size: 9px; color: #82999e;")

        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(25)

        self.pages = QStackedWidget()

        navigation = [
            ("Overview", self.create_overview),
            ("Network Recon", self.create_recon),
            ("Wi-Fi Inspector", self.create_wifi),
            ("Traffic Analysis", self.create_traffic),
            ("PCAP Lab", self.create_pcap),
            ("Security Audit", self.create_audit),
            ("Reports", self.create_reports),
        ]

        for index, (name, page_builder) in enumerate(navigation):
            button = QPushButton(name)
            button.clicked.connect(
                lambda checked=False, i=index: self.pages.setCurrentIndex(i)
            )

            sidebar_layout.addWidget(button)
            self.pages.addWidget(page_builder())

        sidebar_layout.addStretch()

        interface_label = QLabel(
            f"ACTIVE INTERFACE\n{self.interface_name}"
        )
        interface_label.setStyleSheet(
            "color: #42e6ce; padding: 10px; "
            "border: 1px solid #24534f; border-radius: 5px;"
        )
        sidebar_layout.addWidget(interface_label)

        back_button = QPushButton("← Change interface")
        back_button.clicked.connect(self.return_to_selection)
        sidebar_layout.addWidget(back_button)

        # MAIN CONTENT
        content_layout = QVBoxLayout()
        content_layout.addWidget(self.create_top_bar())
        content_layout.addWidget(self.pages)

        root_layout.addWidget(sidebar)
        root_layout.addLayout(content_layout, 1)

        self.setCentralWidget(root)

    def create_top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(65)

        layout = QHBoxLayout(bar)

        heading = QLabel("SECURITY OPERATIONS CENTER")
        heading.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: #42e6ce;"
        )

        status = QLabel("● INTERFACE SELECTED")
        status.setStyleSheet("color: #42e6ce;")

        layout.addWidget(heading)
        layout.addStretch()
        layout.addWidget(status)

        return bar

    def make_panel(self, title, description):
        panel = QFrame()
        panel.setObjectName("Panel")

        layout = QVBoxLayout(panel)

        heading = QLabel(title)
        heading.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #42e6ce;"
        )

        details = QLabel(description)
        details.setWordWrap(True)
        details.setStyleSheet("color: #91a8ae;")

        layout.addWidget(heading)
        layout.addWidget(details)

        return panel

    def make_page(self, title, description):
        page = QWidget()
        layout = QVBoxLayout(page)

        heading = QLabel(title)
        heading.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #42e6ce;"
        )

        explanation = QLabel(description)
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #91a8ae;")

        layout.addWidget(heading)
        layout.addWidget(explanation)
        layout.addSpacing(15)

        return page, layout

    def create_overview(self):
        page, layout = self.make_page(
            "Network Overview",
            "Live summary of the selected network interface and its environment."
        )

        grid = QGridLayout()
        grid.setSpacing(12)

        panels = [
            ("ACTIVE INTERFACE", self.interface_name),
            ("LOCAL IP ADDRESS", self.get_local_ip()),
            ("PUBLIC IP ADDRESS", "Not checked yet"),
            ("DEFAULT GATEWAY", "Not detected yet"),
            ("CONNECTED DEVICES", "Not scanned yet"),
            ("TRAFFIC STATUS", "Capture not started"),
        ]

        for index, (title, value) in enumerate(panels):
            panel = self.make_panel(title, value)
            grid.addWidget(panel, index // 3, index % 3)

        layout.addLayout(grid)

        topology = self.make_panel(
            "NETWORK TOPOLOGY",
            "The network map will display the selected interface, "
            "gateway and discovered devices after a network scan."
        )
        layout.addWidget(topology)

        events = self.make_panel(
            "SYSTEM EVENT LOG",
            "ScopeScout initialized. Waiting for an operation."
        )
        layout.addWidget(events)

        layout.addStretch()
        return page


    def create_recon(self):
        page, layout = self.make_page(
            "Network Recon",
            "Discover devices on the local network associated with "
            "your selected wireless interface."
        )

        controls = QHBoxLayout()

        self.scan_button = QPushButton("▶  SCAN")
        self.scan_button.clicked.connect(self.start_scan)

        self.auto_scan_checkbox = QCheckBox(
            "Auto Scan — every 10 seconds"
        )
        self.auto_scan_checkbox.setStyleSheet(
            "color: #42e6ce; padding: 8px;"
        )
        self.auto_scan_checkbox.toggled.connect(
            self.toggle_auto_scan
        )

        controls.addWidget(self.scan_button)
        controls.addWidget(self.auto_scan_checkbox)
        controls.addStretch()

        layout.addLayout(controls)

        self.scan_status = QLabel("Ready — waiting for scan.")
        self.scan_status.setStyleSheet("color: #42e6ce;")
        layout.addWidget(self.scan_status)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(6)
        self.device_table.setHorizontalHeaderLabels([
            "IP ADDRESS",
            "MAC ADDRESS",
            "HOSTNAME",
            "VENDOR",
            "STATUS",
            "LAST SEEN",
        ])

        self.device_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.device_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.device_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        self.device_table.itemSelectionChanged.connect(
            self.show_device_details
        )

        self.device_table.setStyleSheet("""
            QTableWidget {
                background-color: #111d26;
                color: #dce8e8;
                gridline-color: #203943;
                border: 1px solid #203943;
            }

            QHeaderView::section {
                background-color: #14232c;
                color: #42e6ce;
                padding: 8px;
                border: 1px solid #203943;
            }

            QTableWidget::item:selected {
                background-color: #24534f;
            }
        """)

        layout.addWidget(self.device_table, 1)

        self.device_details = QLabel(
            "Select a discovered device to inspect its information."
        )
        self.device_details.setWordWrap(True)
        self.device_details.setStyleSheet("""
            background-color: #111d26;
            color: #42e6ce;
            padding: 15px;
            border: 1px solid #203943;
            border-radius: 6px;
        """)

        layout.addWidget(self.device_details)

        return page

    def start_scan(self):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return

        self.scan_button.setEnabled(False)
        self.scan_status.setText(
            f"Scanning local network through {self.interface_name}..."
        )

        self.scan_worker = NetworkScanWorker(self.interface_name)

        self.scan_worker.completed.connect(self.display_devices)
        self.scan_worker.failed.connect(self.scan_failed)
        self.scan_worker.finished.connect(self.scan_finished)

        self.scan_worker.start()

    def scan_finished(self):
        self.scan_button.setEnabled(True)
        self.scan_worker = None

    def scan_failed(self, error):
        self.scan_status.setText(f"Scan failed: {error}")

    def display_devices(self, devices):
        from datetime import datetime

        self.devices = devices
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.device_table.setRowCount(len(devices))

        for row, device in enumerate(devices):
            values = [
                device["ip"],
                device["mac"],
                device["hostname"],
                device["vendor"],
                device["status"],
                timestamp,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(
                    item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )
                self.device_table.setItem(row, column, item)

        self.scan_status.setText(
            f"Scan completed at {timestamp} — "
            f"{len(devices)} device(s) discovered."
        )

    def toggle_auto_scan(self, enabled):
        if enabled:
            self.start_scan()
            self.scan_timer.start()
            self.scan_status.setText(
                "Automatic scanning enabled — interval: 10 seconds."
            )
        else:
            self.scan_timer.stop()
            self.scan_status.setText(
                "Automatic scanning disabled."
            )

    def show_device_details(self):
        row = self.device_table.currentRow()

        if row < 0 or row >= len(self.devices):
            return

        device = self.devices[row]

        self.device_details.setText(
            f"DEVICE INFORMATION\n\n"
            f"IP ADDRESS: {device['ip']}\n"
            f"MAC ADDRESS: {device['mac']}\n"
            f"HOSTNAME: {device['hostname']}\n"
            f"VENDOR: {device['vendor']}\n"
            f"STATUS: {device['status']}"
        )


    def create_wifi(self):
        page, layout = self.make_page(
            "Wi-Fi Inspector",
            "Inspect wireless information exposed by your operating system and adapter."
        )

        layout.addWidget(self.make_panel(
            "WIRELESS NETWORK",
            "SSID: Not queried yet\n"
            "BSSID: Not queried yet\n"
            "Channel: Not queried yet\n"
            "Signal: Not queried yet\n"
            "Security: Not queried yet"
        ))

        layout.addWidget(self.make_panel(
            "ADAPTER CAPABILITIES",
            "Monitor mode and capture support will be checked separately. "
            "Selecting an interface does not guarantee these capabilities."
        ))

        layout.addStretch()
        return page

    def create_traffic(self):
        page, layout = self.make_page(
            "Traffic Analysis",
            "Passively inspect traffic from your own machine or an authorized capture."
        )

        layout.addWidget(self.make_panel(
            "LIVE CAPTURE",
            "Packet capture controls and capture status will appear here."
        ))

        layout.addWidget(self.make_panel(
            "PROTOCOL STATISTICS",
            "Ethernet, IP, TCP, UDP, DNS and other protocol statistics."
        ))

        layout.addWidget(self.make_panel(
            "TRAFFIC FLOW",
            "Source and destination addresses, packet counts and traffic rates."
        ))

        layout.addStretch()
        return page

    def create_pcap(self):
        page, layout = self.make_page(
            "PCAP Lab",
            "Analyze packet capture files that you own or are authorized to inspect."
        )

        layout.addWidget(self.make_panel(
            "OPEN PCAP FILE",
            "File selection and capture parsing will be added here."
        ))

        layout.addWidget(self.make_panel(
            "PACKET INSPECTOR",
            "Inspect packet metadata, protocols and timestamps. "
            "Encrypted HTTPS content will not be treated as readable plaintext."
        ))

        layout.addStretch()
        return page

    def create_audit(self):
        page, layout = self.make_page(
            "Security Audit",
            "Review network and wireless security configuration."
        )

        layout.addWidget(self.make_panel(
            "WIRELESS SECURITY",
            "Review the security type and configuration details exposed by the adapter."
        ))

        layout.addWidget(self.make_panel(
            "NETWORK FINDINGS",
            "Potentially exposed services and configuration concerns will be listed here."
        ))

        layout.addWidget(self.make_panel(
            "RECOMMENDATIONS",
            "Practical recommendations will be generated from actual findings."
        ))

        layout.addStretch()
        return page

    def create_reports(self):
        page, layout = self.make_page(
            "Reports",
            "Export findings from completed ScopeScout operations."
        )

        layout.addWidget(self.make_panel(
            "REPORT EXPORT",
            "JSON, CSV and HTML report generation will be integrated here."
        ))

        layout.addStretch()
        return page

    def get_local_ip(self):
        try:
            # Determine the local address used for the default route.
            # This does not send application data to the destination.
            connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            connection.connect(("192.0.2.1", 80))
            address = connection.getsockname()[0]
            connection.close()
            return address
        except OSError:
            return "Unavailable"

    def return_to_selection(self):
        self.close()

        if self.parent():
            self.parent().show()
