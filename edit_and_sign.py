import argparse
import json
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QTextOption
from PyQt5.QtWidgets import (QWidget, QLabel, QRadioButton, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QButtonGroup, QMessageBox, QFrame, QApplication, QTextBrowser)

from modelteam.modelteam_utils.utils import filter_low_score_skills
from modelteam_utils.constants import USER, REPO, STATS, SKILLS, RELEVANT, NOT_RELEVANT, TOP_SECRET


class App(QWidget):
    def __init__(self, email, repocsv, skills, choice_file):
        super().__init__()

        self.email = email
        self.repocsv = repocsv
        self.skills = skills
        self.choice_file = choice_file
        self.choices = {}
        self.init_ui()

    def load_choices(self):
        try:
            with open(self.choice_file, 'r') as f:
                choices_dict = json.load(f)
                return choices_dict
        except FileNotFoundError:
            return {}

    def init_ui(self):
        self.setWindowTitle("Edit Profile")
        self.setStyleSheet("background-color: #333333; color: white;")
        self.setGeometry(100, 100, 800, 800)
        layout = QVBoxLayout()

        # Top frame for logo and display fields
        top_frame = QHBoxLayout()
        layout.addLayout(top_frame)

        # Add logo image (PNG)
        pixmap = QPixmap("images/modelteam_logo.png")
        logo_label = QLabel()
        logo_label.setPixmap(pixmap)
        top_frame.addWidget(logo_label)

        repo_csv_label = QTextBrowser()
        explanation = (
            f"""<html>
<h4><b>Email:</b> {self.email}<br>      
<b>Repos:</b> {self.repocsv}<br>
<b>Total Skills:</b> {len(self.skills)}</h4>
<p style="font-size:12px; ">These are the skills that our models predicted after analyzing your code contributions.
These skills will further be scored by another model on the server side. Please select the appropriate choice for each skill to help us improve our model.</p>
<p style="font-size:14px; ">
1. <b>Relevant</b>: Keep in profile.
<br>2. <b>Not Relevant</b>: Mark as not relevant and Remove from profile in the server.
<br>3. <b>Top Secret</b>: Remove from profile and DON'T even send it to the server.
</p>
</html>
""")
        repo_csv_label.setMaximumHeight(200)
        repo_csv_label.setHtml(explanation)
        repo_csv_label.setWordWrapMode(QTextOption.WordWrap)
        repo_csv_label.setStyleSheet("color: white;")
        layout.addWidget(repo_csv_label)

        # Scroll area for skills
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #333333;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(1)
        scroll_area.setWidget(scroll_content)
        self.add_choice_header(layout)
        layout.setSpacing(1)
        prev_choices = self.load_choices()
        for skill in self.skills:
            self.add_choice_widget(scroll_layout, skill, prev_choices.get(skill, RELEVANT))

        layout.addWidget(scroll_area)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(20, 20, 20, 20)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedWidth(150)
        self.cancel_button.setFixedHeight(30)
        font = self.cancel_button.font()
        font.setBold(True)
        self.cancel_button.setFont(font)
        self.cancel_button.setStyleSheet("background-color: #ff6600; color: white;")
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)
        self.save_button = QPushButton("Save Choices")
        font = self.save_button.font()
        font.setBold(True)
        self.save_button.setFont(font)
        self.save_button.setFixedWidth(150)
        self.save_button.setFixedHeight(30)
        self.save_button.setStyleSheet("background-color: #808080; color: white;")
        self.save_button.clicked.connect(self.save_choices)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.show()

    def add_choice_header(self, layout):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)
        label = QLabel("Skill")
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setFixedWidth(150)
        label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(label)
        names = [RELEVANT, NOT_RELEVANT, TOP_SECRET]
        for name in names:
            header_layout = QHBoxLayout()
            header_layout.setAlignment(Qt.AlignCenter)
            label = QLabel(name)
            font = label.font()
            font.setBold(True)
            label.setFont(font)
            header_layout.addWidget(label)
            frame_layout.addLayout(header_layout)
        layout.addWidget(frame)

    def add_choice_widget(self, layout, skill, def_enabled):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(10, 0, 10, 0)

        label = QLabel(skill.title())
        label.setFixedWidth(150)
        label.setWordWrap(True)
        frame_layout.addWidget(label)

        button_group = QButtonGroup()
        names = [RELEVANT, NOT_RELEVANT, TOP_SECRET]
        for name in names:
            radio_layout = QHBoxLayout()
            radio_layout.setAlignment(Qt.AlignCenter)
            radio = QRadioButton()
            radio.setAccessibleName(name)
            if name == def_enabled:
                radio.setChecked(True)
            radio.toggled.connect(self.check_filled)
            button_group.addButton(radio)
            radio_layout.addWidget(radio)
            frame_layout.addLayout(radio_layout)
        self.choices[skill] = button_group
        layout.addWidget(frame)

    def check_filled(self):
        if all(group.checkedButton() for group in self.choices.values()):
            self.save_button.setEnabled(True)
            self.save_button.setStyleSheet("background-color: #ff6600; color: white;")
        else:
            self.save_button.setEnabled(False)
            self.save_button.setStyleSheet("background-color: #808080; color: white;")

    def save_choices(self):
        choices_dict = {item: group.checkedButton().accessibleName() for item, group in self.choices.items()}
        with open(self.choice_file, 'w') as f:
            json.dump(choices_dict, f)
        QMessageBox.information(self, "Save Choices", "Choices saved successfully!")


def edit_profile(profile_jsonl, choices_file):
    with open(profile_jsonl, "r") as f:
        repos = []
        skills = {}
        for line in f:
            json_line = json.loads(line)
            email = json_line[USER]
            repos.append(json_line[REPO])
            for skill in json_line[STATS][SKILLS].keys():
                skills[skill] = max(skills.get(skill, 0), json_line[STATS][SKILLS][skill])
        skills = sorted(skills.keys(), key=lambda x: skills[x], reverse=True)
        app = QApplication(sys.argv)
        ex = App(email, ",".join(repos), skills, choices_file)
        return app.exec_()


def apply_choices(profile_jsonl, choices_file, edited_file):
    with open(profile_jsonl, "r") as f:
        with open(edited_file, "w") as f2:
            with open(choices_file, 'r') as f3:
                choices_dict = json.load(f3)
            for line in f:
                json_line = json.loads(line)
                stats = json_line[STATS]
                filter_low_score_skills(stats, {}, choices_dict)
                f2.write(json.dumps(json_line) + "\n")
    print(f"Edited file saved as {edited_file}")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--profile_jsonl", type=str, required=True)
    arg_parser.add_argument("--user_key", type=str, required=True)

    args = arg_parser.parse_args()
    file_name_without_extension = args.profile_jsonl.replace(".jsonl", "")
    choices_file = f"{file_name_without_extension}_choices.json"
    edited_file = f"{file_name_without_extension}.edited.jsonl"
    encrypted_file = f"{file_name_without_extension}.enc.gz"
    result = edit_profile(args.profile_jsonl, choices_file)
    if result == 0:
        print("Changes were saved. Applying changes...")
        apply_choices(args.profile_jsonl, choices_file, edited_file)
        # encrypt_compress_file(args.profile_jsonl, encrypted_file, args.user_key)
    else:
        print("Changes were not saved. Exiting... Please run the script again.")
        sys.exit(1)
