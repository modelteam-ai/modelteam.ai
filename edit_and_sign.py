import argparse
import json
import sys

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWidget, QLabel, QRadioButton, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QButtonGroup, QMessageBox, QFrame, QApplication)

from modelteam.modelteam_utils.constants import USER, REPO, STATS, SKILLS

RELEVANT = "Relevant"
NOT_RELEVANT = "Not Relevant"
TOP_SECRET = "Top Secret"

explanation = ("\nThese are the skills that our models predicted after analyzing your code contributions. "
               "These skills will further be scored by another model on the server side."
               "Please select the appropriate choice for each skill to help us improve our model.\n"
               "\n1. Relevant: Keep the skill in your profile."
               "\n2. Not Relevant: Will be removed at the server side."
               "\n3. Top Secret: Dont send this to the server.")


class App(QWidget):
    def __init__(self, email, repocsv, explanation, items, choice_file):
        super().__init__()

        self.email = email
        self.repocsv = repocsv
        self.items = items
        self.choice_file = choice_file
        self.explanation = explanation
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Data Selector")
        self.setStyleSheet("background-color: #333333; color: white;")
        layout = QVBoxLayout()

        # Top frame for logo and display fields
        top_frame = QHBoxLayout()
        layout.addLayout(top_frame)

        # Add logo image (PNG)
        pixmap = QPixmap("images/modelteam_logo.png")
        logo_label = QLabel()
        logo_label.setPixmap(pixmap)
        top_frame.addWidget(logo_label)

        header_frame = QVBoxLayout()
        layout.addLayout(header_frame)

        email_label = QLabel(f"Email: {self.email}")
        email_label.setStyleSheet("color: white;")
        header_frame.addWidget(email_label)

        repo_csv_label = QLabel(self.explanation)
        repo_csv_label.setWordWrap(True)
        repo_csv_label.setStyleSheet("color: white;")
        header_frame.addWidget(repo_csv_label)

        # Scroll area for items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #333333;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(5)
        scroll_area.setWidget(scroll_content)
        self.choices = {}
        for item in self.items:
            self.add_choice_widget(scroll_layout, item)

        layout.addWidget(scroll_area)
        self.save_button = QPushButton("Save Choices")
        self.save_button.clicked.connect(self.save_choices)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self.show()

    def add_choice_widget(self, layout, item):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(10, 0, 10, 0)

        label = QLabel(item)
        label.setFixedWidth(200)
        label.setWordWrap(True)
        frame_layout.addWidget(label)

        button_group = QButtonGroup()

        keep_radio = QRadioButton(RELEVANT)
        keep_radio.setChecked(True)
        keep_radio.toggled.connect(self.check_filled)
        button_group.addButton(keep_radio)
        frame_layout.addWidget(keep_radio)

        not_relevant_radio = QRadioButton(NOT_RELEVANT)
        not_relevant_radio.toggled.connect(self.check_filled)
        button_group.addButton(not_relevant_radio)
        frame_layout.addWidget(not_relevant_radio)

        remove_conf_radio = QRadioButton(TOP_SECRET)
        remove_conf_radio.toggled.connect(self.check_filled)
        button_group.addButton(remove_conf_radio)
        frame_layout.addWidget(remove_conf_radio)

        self.choices[item] = button_group

        layout.addWidget(frame)

    def check_filled(self):
        if all(group.checkedButton() for group in self.choices.values()):
            self.save_button.setEnabled(True)
        else:
            self.save_button.setEnabled(False)

    def save_choices(self):
        choices_dict = {item: group.checkedButton().text() for item, group in self.choices.items()}
        with open(self.choice_file, 'w') as f:
            json.dump(choices_dict, f)
        QMessageBox.information(self, "Save Choices", "Choices saved successfully!")


def edit_profile(profile_jsonl, choices_file):
    with open(profile_jsonl, "r") as f:
        repos = []
        skills = []
        for line in f:
            json_line = json.loads(line)
            email = json_line[USER]
            repos.append(json_line[REPO])
            skills.extend(json_line[STATS][SKILLS].keys())
        app = QApplication(sys.argv)
        ex = App(email, ",".join(repos), explanation, sorted(skills), choices_file)
        return app.exec_()


def apply_choices(profile_jsonl, choices_file, edited_file):
    pass


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
        apply_choices(args.profile_jsonl, choices_file, edited_file)
        # encrypt_compress_file(args.profile_jsonl, encrypted_file, args.user_key)
    else:
        print("Changes were not saved. Exiting... Please run the script again.")
        sys.exit(1)
