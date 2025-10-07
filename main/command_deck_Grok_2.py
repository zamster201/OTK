import sys
import os
import yaml
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QPushButton,
                               QVBoxLayout, QWidget, QLabel, QStatusBar, QLineEdit)
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from PIL import Image  # Assuming Pillow for PNG export; if not, fallback to savefig

class CommandDeck(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WEN CommandDeck v0.2")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(450, 350)
        self.agents = self.load_agents()
        self.active_agent = "Architect"
        self.submit_count = {agent: 0 for agent in self.agents}  # For fatigue
        self.start_time = datetime.now()  # For biofeedback
        self.build_ui()
        self.recover_flow()

    def load_agents(self):
        config_file = 'agents.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        # Default
        defaults = {
            'Architect': {'color': 'orange', 'prompt': 'CTS: Architect {input}'},
            'Reflexion': {'color': 'pink', 'prompt': 'Reflect on {input}'},
            'RFP Scout': {'color': 'blue', 'prompt': 'Scout RFPs for {input}'},
            'CTS Docs': {'color': 'white', 'prompt': 'Docs query: {input}'}
        }
        with open(config_file, 'w') as f:
            yaml.dump(defaults, f)
        return defaults

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Context Switcher (Tabs with active glow)
        switcher_label = QLabel("Context Switcher")
        layout.addWidget(switcher_label)
        self.switcher = QTabWidget()
        agent_order = list(self.agents.keys())
        for i, agent_name in enumerate(agent_order):
            tab = QWidget()
            btn = QPushButton(agent_name)
            btn.clicked.connect(lambda checked, name=agent_name: self.switch_context(name))
            tab_layout = QVBoxLayout(tab)
            tab_layout.addWidget(btn)
            self.switcher.addTab(tab, agent_name)
            if agent_name == self.active_agent:
                self.switcher.setCurrentIndex(i)
                btn.setStyleSheet("background-color: orange; border-radius: 5px;")
        layout.addWidget(self.switcher)

        # Action Palette
        tools_label = QLabel("Tools & Ambient")
        layout.addWidget(tools_label)
        tools_layout = QVBoxLayout()
        buttons = ['VS Code', 'Quick Log', 'Search', 'Explorer', 'Music', 'Mail', 'News', 'Settings', 'Notepad', 'Browser', 'Quit']
        for btn_text in buttons:
            btn = QPushButton(btn_text)
            if btn_text == 'Quick Log':
                btn.clicked.connect(self.update_thread)
            elif btn_text == 'Quit':
                btn.clicked.connect(self.quit_app)
            else:
                btn.clicked.connect(lambda checked, text=btn_text: self.statusBar().showMessage(f"Launched {text}"))
            tools_layout.addWidget(btn)
        self.tools_layout = tools_layout  # For biofeedback dimming
        layout.addLayout(tools_layout)

        # Prompt Bay
        bay_label = QLabel("Prompt Bay (Voice/Gesture Stub: Thumbs-up to Submit)")
        layout.addWidget(bay_label)
        self.prompt_edit = QLineEdit()
        self.prompt_edit.returnPressed.connect(self.on_prompt_submit)
        self.prompt_edit.textChanged.connect(self.on_prompt_change)
        self.start_time = datetime.now()  # Reset per change for cadence
        layout.addWidget(self.prompt_edit)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | Active: Architect")

    def on_prompt_change(self):
        text = self.prompt_edit.text()
        now = datetime.now()
        typing_speed = len(text) / max((now - self.start_time).total_seconds(), 1)
        if typing_speed < 10:  # Slow typing → context bleed
            self.status_bar.showMessage("Biofeedback: Flow booster suggested (slow typing detected)")
            self.dim_tools()  # Hide non-essentials
        self.start_time = now

        if 'RFP' in text.upper():
            rfp_index = list(self.agents.keys()).index('RFP Scout')
            self.switcher.setCurrentIndex(rfp_index)
            self.switch_context('RFP Scout')  # Sync active_agent
            self.status_bar.showMessage("Swarm: Routed to RFP Scout")

    def on_prompt_submit(self):
        agent_name = list(self.agents.keys())[self.switcher.currentIndex()]
        self.switch_context(agent_name)  # Sync
        input_text = self.prompt_edit.text()
        full_prompt = self.agents[agent_name]['prompt'].format(input=input_text)
        self.submit_count[agent_name] += 1
        if self.submit_count[agent_name] > 5:  # Fatigue rotate
            next_agent = list(self.agents.keys())[(list(self.agents.keys()).index(agent_name) + 1) % len(self.agents)]
            self.switch_context(next_agent)
            self.status_bar.showMessage(f"Fatigue: Rotated to {next_agent}")

        # Hybrid route stub (local print; replace with Mistral/Grok API)
        print(f"Local LLM: {full_prompt}")  # Grunt work
        # e.g., if creative: grok_api_call(full_prompt)

        self.status_bar.showMessage(f"Submitted to {agent_name}: {full_prompt[:50]}...")
        self.log_to_ce(full_prompt, agent_name)
        self.prompt_edit.clear()
        self.undim_tools()

    def switch_context(self, agent_name):
        self.active_agent = agent_name
        self.prompt_edit.setText(self.agents[agent_name]['prompt'].format(input="Your idea..."))
        self.status_bar.showMessage(f"Switched to {agent_name}")
        # Update tab glow
        for i in range(self.switcher.count()):
            tab_widget = self.switcher.widget(i)
            btn = tab_widget.layout().itemAt(0).widget()
            btn.setStyleSheet("background-color: {}; border-radius: 5px;".format(
                self.agents[agent_name]['color'] if agent_name == self.agents[list(self.agents.keys())[i]]['color'] else 'gray' if i == self.switcher.currentIndex() else 'lightgray'))

    def update_thread(self):
        summary = f"Session pulse: Active {self.active_agent}, {sum(self.submit_count.values())} submits"
        self.log_to_ce(summary, self.active_agent)
        self.status_bar.showMessage("Thread updated → CE")

    def recover_flow(self):
        unresolved = self.parse_ce_unresolved()
        what_if = "What if: Prioritize WEN tweak to unblock 2 RFPs?" if unresolved > 0 else ""
        self.status_bar.showMessage(f"Recovery: {unresolved} TODOs | {what_if}")

    def parse_ce_unresolved(self):
        if not os.path.exists('ce_index.md'):
            return 0
        with open('ce_index.md', 'r') as f:
            content = f.read()
        # Simple: count lines without [x] (assume TODO format)
        lines = [line for line in content.split('\n') if '- [' in line and not '[x]' in line]
        return len(lines)

    def dim_tools(self):
        for i in range(self.tools_layout.count()):
            widget = self.tools_layout.itemAt(i).widget()
            if widget.text() not in ['Quick Log', 'Quit']:  # Keep essentials
                widget.hide()

    def undim_tools(self):
        for i in range(self.tools_layout.count()):
            self.tools_layout.itemAt(i).widget().show()

    def quit_app(self):
        self.generate_handoff()
        self.close()

    def generate_handoff(self):
        # Ritual: PNG mindmap of open loops
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.add_patch(patches.Circle((0.5, 0.5), 0.4, color='lightblue'))
        ax.text(0.5, 0.5, f'Open: {self.parse_ce_unresolved()} Threads\nActive: {self.active_agent}', ha='center', va='center')
        for i, agent in enumerate(self.agents.keys()):
            ax.text(0.5 + 0.3 * (i % 2 - 0.5), 0.5 + 0.2 * (i // 2 - 0.5), agent, fontsize=8)
        ax.axis('off')
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img = Image.open(buf)
        img.save('handoff_mindmap.png')
        plt.close()
        self.status_bar.showMessage("Handoff PNG generated")

    def log_to_ce(self, content, agent):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        tags = '#TODO' if 'Scout' not in agent else '#RFP'  # Graph edges
        with open('ce_index.md', 'a') as f:
            f.write(f"\n- [ ] [{timestamp}] {content} | agent: {agent} {tags}\n")  # Unchecked for unresolved

if __name__ == "__main__":
    app = QApplication(sys.argv)
    deck = CommandDeck()
    deck.show()
    sys.exit(app.exec())