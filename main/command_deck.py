import sys, json, os, datetime, webbrowser, subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QGridLayout, QLabel
)
from PySide6.QtCore import QTimer, Qt, QPropertyAnimation, QRect
from PySide6.QtGui import QIcon, QShortcut, QKeySequence

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
LAYOUT_FILE = BASE_DIR / "data" / "OTK.json"
QSS_FILE = BASE_DIR / "styles" / "cognition_mode.qss"
LIGHT_QSS_FILE = BASE_DIR / "styles" / "cognition_mode_light.qss"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "OTK_usage.log"
CE_LOG_FILE = BASE_DIR.parents[1] / "Cognition_Engine" / "logs" / "ce_session_log.jsonl"

# Global toast stack
toast_stack = []


class CommandDeck(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OTK")
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.is_dark = True
        self.load_stylesheet()
        LOG_DIR.mkdir(exist_ok=True)
        self.build_ui()

        # Add theme toggle button
        self.toggle_btn = QPushButton("🌙")
        self.toggle_btn.setToolTip("Toggle Light/Dark Theme")
        self.toggle_btn.clicked.connect(self.toggle_theme)
        self.layout.addWidget(self.toggle_btn, 99, 0, 1, 3)

    def load_stylesheet(self):
        qss_file = QSS_FILE if self.is_dark else LIGHT_QSS_FILE
        if qss_file.exists():
            with open(qss_file, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.toggle_btn.setText("🌙" if self.is_dark else "☀️")
        self.load_stylesheet()
        Toast(self, f"Theme: {'Dark' if self.is_dark else 'Light'}", self.is_dark)

    def build_ui(self):
        try:
            with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
                layout = json.load(f)
        except Exception as e:
            print(f"Error loading layout: {e}")
            return

        for button in layout:
            btn = QPushButton(button["label"])
            btn.setToolTip(button.get("tooltip", ""))

            # Optional icon support
#            icon_path = BASE_DIR / "resources" / "icons" / button.get("icon", "")
#            if icon_path.exists():
#                btn.setIcon(QIcon(str(icon_path)))

            # Click handler
            btn.clicked.connect(lambda _, b=button: self.handle_click(b))
            self.layout.addWidget(btn, button.get("row", 0), button.get("col", 0))

            # Optional shortcut support
            if "shortcut" in button:
                shortcut = QShortcut(QKeySequence(button["shortcut"]), self)
                shortcut.activated.connect(lambda b=button: self.handle_click(b))

    def log_action(self, button, status="OK"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Flat text log
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"{timestamp} | {button['slot_id']} | {button['type']} | {status}\n")

        # CE structured log
        event = {
            "timestamp": timestamp,
            "source": "OTK",
            "slot_id": button.get("slot_id"),
            "label": button.get("label"),
            "type": button.get("type"),
            "payload": button.get("payload"),
            "status": status
        }
        try:
            CE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CE_LOG_FILE, "a", encoding="utf-8") as ce_log:
                ce_log.write(json.dumps(event) + "\n")
        except Exception as e:
            with open(LOG_FILE, "a", encoding="utf-8") as log:
                log.write(f"{timestamp} | CE_LOG_FAIL | {e}\n")

    def handle_click(self, button):
        action_type = button["type"]
        target = button["payload"]

        try:
            if action_type == "prompt":
                full_path = BASE_DIR / target
                if not full_path.exists():
                    raise FileNotFoundError(f"Prompt not found: {target}")
                with open(full_path, "r", encoding="utf-8") as f:
                    text = f.read()
                QApplication.clipboard().setText(text)
                Toast(self, f"✅ Copied: {button['label']}", self.is_dark)

            elif action_type == "note":
                full_path = BASE_DIR / target
                if not full_path.exists():
                    raise FileNotFoundError(f"Note not found: {target}")
                os.startfile(full_path)
                Toast(self, f"📄 Opened: {button['label']}", self.is_dark)

            elif action_type == "macro":
                full_path = BASE_DIR / target
                if not full_path.exists():
                    raise FileNotFoundError(f"Script not found: {target}")
                os.system(f'python "{full_path}"')
                Toast(self, f"▶️ Ran: {button['label']}", self.is_dark)

            elif action_type == "url":
                webbrowser.open(target)
                Toast(self, f"🌐 Opened: {button['label']}", self.is_dark)

            elif action_type == "exec":
                subprocess.Popen([target], shell=True)
                Toast(self, f"⚙️ Launched: {button['label']}", self.is_dark)

            elif action_type == "log":
                note = {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "OTK",
                    "slot_id": button.get("slot_id"),
                    "label": button.get("label"),
                    "type": "log",
                    "message": target
                }
                with open(CE_LOG_FILE, "a", encoding="utf-8") as ce_log:
                    ce_log.write(json.dumps(note) + "\n")
                Toast(self, f"📝 Logged: {target}", self.is_dark)

            else:
                Toast(self, f"⚠️ Unknown action: {action_type}", self.is_dark, duration=4000)

            self.log_action(button, "OK")

        except Exception as e:
            self.log_action(button, f"FAIL: {e}")
            Toast(self, f"❌ Failed: {button['label']}", self.is_dark, duration=4000)


class Toast(QLabel):
    def __init__(self, parent, message, dark=True, duration=2000):
        super().__init__(parent)
        global toast_stack

        # Style by theme
        bg = "rgba(50, 50, 50, 220)" if dark else "rgba(240, 240, 240, 220)"
        color = "white" if dark else "black"
        self.setText(message)
        self.setStyleSheet(f"""
            background-color: {bg};
            color: {color};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
        """)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.adjustSize()

        # Compute stacked position
        parent_rect = parent.geometry()
        index = len(toast_stack)
        x = parent_rect.width() - self.width() - 20
        y = parent_rect.height() - self.height() - 20 - (index * (self.height() + 10))
        self.setGeometry(QRect(x, y, self.width(), self.height()))
        toast_stack.append(self)

        # Fade in
        self.setWindowOpacity(0.0)
        self.show()
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        # Auto close
        QTimer.singleShot(duration, self.fade_out)

    def fade_out(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.cleanup)
        self.anim.start()

    def cleanup(self):
        global toast_stack
        if self in toast_stack:
            toast_stack.remove(self)
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommandDeck()
    window.resize(600, 400)
    window.show()
    sys.exit(app.exec())
