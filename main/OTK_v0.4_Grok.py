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
from PIL import Image

class OTK(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OTK (Obsidian Tool Kit)")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(450, 350)
        self.agents = self.load_agents()
        self.active_agent = "Architect"
        self.submit_count = {agent: 0 for agent in self.agents}
        self.activity_log = []  # For Tracker embeds
        self.start_time = datetime.now()
        self.build_ui()
        self.prime_pump()

    def load_agents(self):
        config_file = 'otk_agents.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        defaults = {
            'Architect': {'color': 'orange', 'prompt': 'Architect {input}'},
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

        bay_label = QLabel("Prompt Bay (Tag #creative for bursts)")
        layout.addWidget(bay_label)
        self.prompt_edit = QLineEdit()
        self.prompt_edit.returnPressed.connect(self.on_prompt_submit)
        self.prompt_edit.textChanged.connect(self.on_prompt_change)
        self.start_time = datetime.now()
        layout.addWidget(self.prompt_edit)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | Active: Architect")

    def on_prompt_change(self):
        text = self.prompt_edit.text()
        now = datetime.now()
        typing_speed = len(text) / max((now - self.start_time).total_seconds(), 1)
        self.activity_log.append({'time': now, 'cadence': typing_speed, 'agent': self.active_agent})
        if typing_speed < 10:
            self.status_bar.showMessage("Activity: Slow cadence—log to Tracker?")
            self.dim_tools()
        self.start_time = now

        is_creative = any(word in text.upper() for word in ['IDEA', 'CREATIVE', 'BRAINSTORM'])
        if is_creative:
            self.status_bar.showMessage("Creativity: Tagged for Excalidraw surfacing")

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
        is_idea = 'IDEA' in input_text.upper()
        self.log_to_ce(full_prompt, agent_name, is_idea)
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
        unresolved = self.parse_ce_unresolved()
        branches = self.generate_what_if(unresolved, prioritize_creative=True)
        contrarian = self.get_contrarian("Current activities")
        activity_summary = f"Cadence avg: {sum([a['cadence'] for a in self.activity_log])/max(len(self.activity_log),1):.1f}"
        summary = f"Runbook: {unresolved} open | {branches} | Contrarian: {contrarian} | {activity_summary}"
        self.log_to_ce(summary, self.active_agent)
        self.export_to_kanban(summary)  # Plugin YAML
        self.status_bar.showMessage("Runbook + Kanban board → Obsidian")

    def prime_pump(self):
        unresolved = self.parse_ce_unresolved()
        creative_unresolved = sum(1 for line in open('otk_ce_index.md', 'r') if '- [ ]' in line and '#creative' in line)
        if unresolved > 0:
            paths = self.generate_what_if(unresolved, prioritize_creative=True, num_paths=3)
            recap = f"Prime: {unresolved} TODOs ({creative_unresolved} creative). Paths: {paths}"
            self.status_bar.showMessage(recap)

    def generate_what_if(self, unresolved, prioritize_creative=False, num_paths=2):
        base_branches = [
            "Tackle CTS refactor? Unblocks 2 RFPs.",
            "Windows util audit? Surfaces 1 leverage.",
            "RFP scout burst? Chains 3 integrations."
        ]
        creative_branches = [
            "Creative fork: Brainstorm WEN hybrid? Sparks 2 novel TODOs.",
            "Idea path: Graft blockchain to CTS? Risks + rewards sim."
        ]
        branches = creative_branches if prioritize_creative else base_branches
        return " | ".join(branches[:num_paths])

    def get_contrarian(self, context):
        return f"Risk: {context} silos creativity—test A/B with devil's advocate?"

    def parse_ce_unresolved(self):
        ce_file = 'otk_ce_index.md'
        if not os.path.exists(ce_file):
            return 0
        with open(ce_file, 'r') as f:
            content = f.read()
        lines = [line for line in content.split('\n') if '- [ ]' in line]
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
        self.export_activity_tracker()
        self.close()

    def generate_reflection_artifact(self):
        unresolved = self.parse_ce_unresolved()
        what_if = self.generate_what_if(unresolved)
        contrarian = self.get_contrarian(f"{unresolved} threads")
        summary = f"Reflection [{datetime.now().strftime('%Y-%m-%d %H:%M')}]: {what_if} | Contrarian: {contrarian}"
        self.log_to_ce(summary, self.active_agent)

        # Graph with creative highlight
        fig, ax = plt.subplots(figsize=(5, 3))
        agents = list(self.agents.keys())
        weights = [self.submit_count[a] for a in agents]
        colors = ['yellow' if w > 3 else self.agents[a]['color'] for a, w in zip(agents, weights)]  # Highlight high activity (creative proxy)
        bars = ax.bar(agents, weights, color=colors)
        ax.set_ylabel('Activity Weight')
        ax.set_title('Runbook Graph (Yellow: Creative Bursts)')
        for bar, w in zip(bars, weights):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, str(w), ha='center')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('otk_reflection_graph.png', dpi=100, bbox_inches='tight')
        plt.close()
        self.status_bar.showMessage("Artifact (Tasks + Graph) → Vault")

    def export_to_kanban(self, content):
        # YAML for Kanban plugin import
        board = {
            'title': 'OTK Runbook',
            'lanes': [
                {'title': 'TODO', 'cards': [f"- [ ] {content} {{due: {{tomorrow}}}} #runbook"]},
                {'title': 'In Progress', 'cards': []},
                {'title': 'Done', 'cards': []}
            ]
        }
        with open('runbook_board.yaml', 'w') as f:
            yaml.dump(board, f)

    def export_activity_tracker(self):
        # Embed for Tracker plugin (e.g., ![[activity_log|300px]])
        with open('activity_log.md', 'w') as f:
            f.write("# Activity Tracker Embed\n")
            for act in self.activity_log:
                f.write(f"- {act['time'].strftime('%H:%M')} | Cadence: {act['cadence']:.1f} | {act['agent']}\n")
        self.status_bar.showMessage("Activity log → Tracker")

    def log_to_ce(self, content, agent, is_idea=False):
        ce_file = 'otk_ce_index.md'
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        tags = '#creative #idea' if is_idea else '#task #activity'
        priority = 'high' if is_idea else 'medium'
        links = '[[Runbooks]] [[Creative Sparks]]' if is_idea else '[[Activity Log]]'
        weight = str(self.submit_count.get(agent, 0))
        entry = f"\n- [ ] {content} | agent: {agent} | weight: {weight} | #priority:{priority} {tags} {links} {{due: {datetime.now().strftime('%Y-%m-%dT%H:%M')}}}\n"
        with open(ce_file, 'a') as f:
            f.write(entry)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    otk = OTK()
    otk.show()
    sys.exit(app.exec())