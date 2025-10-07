import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QTextEdit,
                               QPushButton, QVBoxLayout, QWidget, QLabel)
from PySide6.QtCore import Qt
import yaml  # For agent config
import os

class CommandDeck(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CommandDeck")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(400, 300)
        self.agents = self.load_agents()
        self.build_ui()

    def load_agents(self):
        with open('agents.yaml', 'r') as f:
            return yaml.safe_load(f)  # e.g., {'CTS_Architect': {'prompt': 'High-level design for {input}'}}

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Prompt Bay
        prompt_label = QLabel("Prompt Bay")
        layout.addWidget(prompt_label)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.textChanged.connect(self.on_prompt_change)
        layout.addWidget(self.prompt_edit)

        # Context Switcher (simple buttons for now)
        switcher = QTabWidget()
        for agent_name in self.agents:
            btn = QPushButton(agent_name)
            btn.clicked.connect(lambda checked, name=agent_name: self.switch_context(name))
            switcher.addTab(QWidget(), agent_name)  # Placeholder tabs
        layout.addWidget(switcher)

        # Thread Updater
        update_btn = QPushButton("Pulse Update → CE")
        update_btn.clicked.connect(self.update_thread)
        layout.addWidget(update_btn)

    def on_prompt_change(self):
        text = self.prompt_edit.toPlainText()
        # Simple inference: Route to agent if keyword match
        if 'RFP' in text:
            self.statusBar().showMessage("Routing to RFP_Scout...")

    def switch_context(self, agent_name):
        template = self.agents[agent_name]['prompt']
        self.prompt_edit.setText(template.format(input="Your idea here"))
        # TODO: Load from Obsidian vault via plugin hook

    def update_thread(self):
        # Append to ce_index.md
        with open('ce_index.md', 'a') as f:
            f.write(f"\n- [{os.popen('date').read().strip()}] {self.prompt_edit.toPlainText()}\n")
        self.statusBar().showMessage("Logged to CE!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    deck = CommandDeck()
    deck.show()
    sys.exit(app.exec())