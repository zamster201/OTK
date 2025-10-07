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
from PIL import Image  # Assuming Pillow; fallback to savefig if needed

class OTK(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OTK (Obsidian Tool Kit)")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(450, 350)
        self.agents = self.load_agents()
        self.active_agent = "Architect"
        self.submit_count = {agent: 0 for agent in self.agents}
        self.start_time = datetime.now()
        self.build_ui()
        self.prime_pump()  # Ritual: Recap unresolved on launch

    def load_agents(self):
        config_file = 'otk_agents.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        defaults = {
            'Architect': {'color': 'orange', 'prompt': 'CTS: Architect {input}'},
            'Reflexion': {'color': 'pink', 'prompt': 'Reflect on {input}'},
            'RFP Scout': {'color': 'blue', 'prompt': 'Scout RFPs for {input}'},
            'Docs': {'color': 'white', 'prompt': 'Docs query: {input}'}
        }
        with open(config_file, 'w') as f:
            yaml.dump(defaults, f)
        return defaults

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Context Switcher
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
                btn.clicked.connect(self.quick_runbook)
            elif btn_text == 'Quit':
                btn.clicked.connect(self.quit_app)
            else:
                btn.clicked.connect(lambda checked, text=btn_text: self.statusBar().showMessage(f"Launched {text}"))
            tools_layout.addWidget(btn)
        self.tools_layout = tools_layout
        layout.addLayout(tools_layout)

        # Prompt Bay (Idea Capture Focus)
        bay_label = QLabel("Prompt Bay (Creative Ideas: Auto-tag bursts)")
        layout.addWidget(bay_label)
        self.prompt_edit = QLineEdit()
        self.prompt_edit.returnPressed.connect(self.on_prompt_submit)
        self.prompt_edit.textChanged.connect(self.on_prompt_change)
        self.start_time = datetime.now()
        layout.addWidget(self.prompt_edit)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | Active: Architect")

    def on_prompt_change(self):
        text = self.prompt_edit.text()
        now = datetime.now()
        typing_speed = len(text) / max((now - self.start_time).total_seconds(), 1)
        if typing_speed < 10:
            self.status_bar.showMessage("Biofeedback: Slow typing—log idea to runbook?")
            self.dim_tools()
        self.start_time = now

        if any(word in text.upper() for word in ['IDEA', 'CREATIVE', 'BRAINSTORM']):
            self.status_bar.showMessage("Idea Mode: Auto-tagging for creative capture")

        if 'RFP' in text.upper():
            rfp_index = list(self.agents.keys()).index('RFP Scout')
            self.switcher.setCurrentIndex(rfp_index)
            self.switch_context('RFP Scout')
            self.status_bar.showMessage("Swarm: Routed to RFP Scout")

    def on_prompt_submit(self):
        agent_name = list(self.agents.keys())[self.switcher.currentIndex()]
        self.switch_context(agent_name)
        input_text = self.prompt_edit.text()
        full_prompt = self.agents[agent_name]['prompt'].format(input=input_text)
        self.submit_count[agent_name] += 1
        if self.submit_count[agent_name] > 5:
            next_agent = list(self.agents.keys())[(list(self.agents.keys()).index(agent_name) + 1) % len(self.agents)]
            self.switch_context(next_agent)
            self.status_bar.showMessage(f"Fatigue: Rotated to {next_agent}")

        print(f"Local LLM: {full_prompt}")
        self.status_bar.showMessage(f"Submitted to {agent_name}: {full_prompt[:50]}...")
        self.log_to_ce(full_prompt, agent_name, is_idea='IDEA' in input_text.upper())
        self.prompt_edit.clear()
        self.undim_tools()

    def switch_context(self, agent_name):
        self.active_agent = agent_name
        self.prompt_edit.setText(self.agents[agent_name]['prompt'].format(input="Your idea..."))
        self.status_bar.showMessage(f"Switched to {agent_name}")
        for i in range(self.switcher.count()):
            tab_widget = self.switcher.widget(i)
            btn = tab_widget.layout().itemAt(0).widget()
            agent_key = list(self.agents.keys())[i]
            color = self.agents[agent_key]['color'] if agent_name == agent_key else 'lightgray'
            btn.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

    def quick_runbook(self):
        # Mini predictive reflection for creative capture
        unresolved = self.parse_ce_unresolved()
        branches = self.generate_what_if(unresolved)
        contrarian = self.get_contrarian("Current open threads")
        summary = f"Quick Runbook: {unresolved} open | Branches: {branches} | Contrarian: {contrarian}"
        self.log_to_ce(summary, self.active_agent)
        self.status_bar.showMessage("Runbook snippet logged → CE")

    def prime_pump(self):
        unresolved = self.parse_ce_unresolved()
        if unresolved > 0:
            recap = f"Prime: {unresolved} unresolved threads from last session. Fork paths?"
            self.status_bar.showMessage(recap)
            # Could TTS this; stub as status for now

    def generate_what_if(self, unresolved):
        # Simple heuristic: Simulate branches based on silos
        if unresolved == 0:
            return "All clear—dive into new ideas."
        branches = [
            "What if: Tackle CTS refactor first? Unblocks 2 RFPs.",
            "What if: Quick Windows util audit? Surfaces 1 hidden leverage.",
            "What if: RFP scout burst? Chains to 3 creative integrations."
        ]
        return " | ".join(branches[:min(3, unresolved)])

    def get_contrarian(self, context):
        # Stub: Local reflection tax; replace with Grok API call
        # e.g., requests.post('https://api.x.ai/v1/chat/completions', json={'model': 'grok-beta', 'messages': [{'role': 'user', 'content': f'Contrarian angle on: {context}'}]})
        return f"Risk: {context} might create unintended silos—test with a quick A/B?"

    def parse_ce_unresolved(self):
        ce_file = 'otk_ce_index.md'
        if not os.path.exists(ce_file):
            return 0
        with open(ce_file, 'r') as f:
            content = f.read()
        lines = [line for line in content.split('\n') if '- [ ]' in line]  # Unchecked tasks
        return len(lines)

    def dim_tools(self):
        for i in range(self.tools_layout.count()):
            widget = self.tools_layout.itemAt(i).widget()
            if widget.text() not in ['Quick Log', 'Quit']:
                widget.hide()

    def undim_tools(self):
        for i in range(self.tools_layout.count()):
            self.tools_layout.itemAt(i).widget().show()

    def quit_app(self):
        self.generate_reflection_artifact()
        self.close()

    def generate_reflection_artifact(self):
        # Point #2: Predictive loop + runbook export
        unresolved = self.parse_ce_unresolved()
        what_if = self.generate_what_if(unresolved)
        contrarian = self.get_contrarian(f"{unresolved} open threads in {self.active_agent}")
        summary = f"Session Reflection [{datetime.now().strftime('%Y-%m-%d %H:%M')}]: {what_if} | Contrarian: {contrarian} | Total submits: {sum(self.submit_count.values())}"

        # Log to Obsidian CE (Dataview-ready: tags, links for graph)
        self.log_to_ce(summary, self.active_agent)

        # Viz: Simple graph for Bayesian edges (export PNG to vault)
        fig, ax = plt.subplots(figsize=(5, 3))
        agents = list(self.agents.keys())
        weights = [self.submit_count[a] for a in agents]  # Edge weights
        colors = [self.agents[a]['color'] for a in agents]
        bars = ax.bar(agents, weights, color=colors)
        ax.set_ylabel('Activity Weight')
        ax.set_title('Session Runbook Graph')
        for bar, w in zip(bars, weights):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, str(w), ha='center')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('otk_reflection_graph.png', dpi=100, bbox_inches='tight')
        plt.close()
        self.status_bar.showMessage("Reflection artifact (MD + PNG) → Obsidian vault")

    def log_to_ce(self, content, agent, is_idea=False):
        ce_file = 'otk_ce_index.md'
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        tags = '#creative #idea' if is_idea else '#task'
        links = '[[CTS]] [[RFP]]' if 'CTS' in content or 'RFP' in content else ''
        weight = str(self.submit_count.get(agent, 0))  # For graph edges
        entry = f"\n- [ ] [{timestamp}] {content} | agent: {agent} | weight: {weight} {tags} {links}\n"
        with open(ce_file, 'a') as f:
            f.write(entry)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    otk = OTK()
    otk.show()
    sys.exit(app.exec())