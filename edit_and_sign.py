import argparse
import datetime
import json
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QTextOption
from PyQt5.QtWidgets import (QWidget, QLabel, QRadioButton, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QButtonGroup, QMessageBox, QFrame, QApplication, QTextBrowser)

from modelteam_utils.constants import USER, REPO, STATS, SKILLS, RELEVANT, NOT_RELEVANT, TOP_SECRET, PROFILES, \
    NR_SKILLS, TIMESTAMP, MT_PROFILE_JSON, PDF_STATS_JSON
from modelteam_utils.crypto_utils import compress_file, generate_hc
from modelteam_utils.utils import filter_skills, sha256_hash
from modelteam_utils.viz_utils import generate_pdf_report


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
        pixmap = QPixmap(os.path.join("images", "modelteam_logo.png"))
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
        toggle = False
        for skill in self.skills:
            self.add_choice_widget(scroll_layout, skill, prev_choices.get(skill, RELEVANT), toggle)
            toggle = not toggle

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
        self.save_button.setStyleSheet("background-color: #ff6600; color: white;")
        self.save_button.clicked.connect(self.save_choices)
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
        label.setFixedWidth(200)
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

    def add_choice_widget(self, layout, skill, def_enabled, toggle_bg_color):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        if toggle_bg_color:
            frame.setStyleSheet("background-color: #444444;")
        frame_layout = QHBoxLayout(frame)
        frame_layout.setContentsMargins(10, 0, 10, 0)

        label = QLabel(skill.title())
        label.setFixedWidth(200)
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
            button_group.addButton(radio)
            radio_layout.addWidget(radio)
            frame_layout.addLayout(radio_layout)
        self.choices[skill] = button_group
        layout.addWidget(frame)

    def save_choices(self):
        choices_dict = {item: group.checkedButton().accessibleName() for item, group in self.choices.items()}
        with open(self.choice_file, 'w') as f:
            json.dump(choices_dict, f)
        QMessageBox.information(self, "Save Choices",
                                "Choices saved successfully! Please check the CLI for full path of the output file.")
        self.close()


def edit_profile(merged_profile, choices_file, cli_mode):
    repos = []
    skills = {}
    email = merged_profile[USER]
    for profile in merged_profile[PROFILES]:
        repos.append(profile[REPO])
        for skill in profile[STATS][SKILLS].keys():
            skills[skill] = max(skills.get(skill, 0), profile[STATS][SKILLS][skill])
    skills = sorted(skills.keys(), key=lambda x: skills[x], reverse=True)
    if cli_mode:
        cli_choices(choices_file, email, repos, skills)
        return 0
    else:
        app = QApplication(sys.argv)
        ex = App(email, ",".join(repos), skills, choices_file)
        return app.exec_()


def cli_choices(choices_file, email, repos, skills):
    print(f"Email: {email}")
    print(f"Repos: {','.join(repos)}")
    print(f"Total Skills: {len(skills)}")
    print("These are the skills that our models predicted after analyzing your code contributions.")
    print("These skills will further be scored by another model on the server side.")
    print("Please select the appropriate choice for each skill to help us improve our model.")
    print("1. Relevant: Keep in profile.")
    print("2. Not Relevant: Mark as not relevant and Remove from profile in the server.")
    print("3. Top Secret: Remove from profile and DON'T even send it to the server.")
    choices_dict = {}
    for skill in skills:
        while True:
            choice = input(f"Skill: {skill.title()}\n1. Relevant\n2. Not Relevant\n3. Top Secret\nEnter choice [1]:\n")
            if not choice:
                choice = "1"
            if choice in ["1", "2", "3"]:
                choices_dict[skill] = [RELEVANT, NOT_RELEVANT, TOP_SECRET][int(choice) - 1]
                break
            else:
                print("Invalid choice. Please enter 1, 2 or 3.")
    with open(choices_file, 'w') as f:
        json.dump(choices_dict, f)


def apply_choices(merged_profile, choices_file, edited_file):
    utc_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    with open(edited_file, "w") as f2:
        with open(choices_file, 'r') as f3:
            choices_dict = json.load(f3)
        non_relevant_skills = [skill for skill in choices_dict if choices_dict[skill] == NOT_RELEVANT]
        top_secret_set = {skill for skill in choices_dict if choices_dict[skill] == TOP_SECRET}
        for profile in merged_profile[PROFILES]:
            stats = profile[STATS]
            filter_skills(stats, {}, top_secret_set)
            profile[NR_SKILLS] = non_relevant_skills
            profile[TIMESTAMP] = utc_now
        merged_profile[TIMESTAMP] = utc_now
        f2.write(json.dumps(merged_profile, indent=2))
    print(f"Edited file saved as {edited_file}\n")


def display_t_and_c(email_id):
    t_and_c = ["\nI certify that,",
               f"\t1. I am the owner of the id {email_id} associated with this profile",
               "\t2. I own the code contributions associated with this id",
               "\t3. I will remove any confidential skills from the profile before submitting"]
    res = input("\n".join(t_and_c) + "\nEnter \"Y\" to proceed: \n")
    return res.lower()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--profile_path", type=str, required=True)
    arg_parser.add_argument("--user_key", type=str, required=True)
    arg_parser.add_argument("--cli_mode", action="store_true", default=False)

    args = arg_parser.parse_args()
    profile_json = os.path.join(args.profile_path, MT_PROFILE_JSON)
    pdf_stats_json = os.path.join(args.profile_path, "tmp-stats", PDF_STATS_JSON)
    file_name_without_extension = profile_json.replace(".json", "")
    choices_file = f"{file_name_without_extension}_choices.json"
    pdf_path = os.path.join(args.profile_path, "pdf")
    with open(profile_json, "r") as f:
        merged_profile = json.load(f)
    if display_t_and_c(merged_profile[USER]) != "y":
        print("Please accept the terms and conditions to proceed.")
        sys.exit(0)
    result = edit_profile(merged_profile, choices_file, args.cli_mode)
    if result == 0 and os.path.exists(choices_file):
        print("Changes were saved. Applying changes...")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        edited_file = os.path.join(args.profile_path, f"mt_stats_{today}.json")
        print(f"Edited file: {edited_file}")
        apply_choices(merged_profile, choices_file, edited_file)
        hc = sha256_hash(generate_hc(edited_file) + args.user_key)
        final_output_file = os.path.join(args.profile_path, f"mt_stats_{today}_{hc}.json.gz")
        compress_file(edited_file, final_output_file)
        generate_pdf_report(edited_file, pdf_stats_json, pdf_path)
        print('*' * 50)
        print("modelteam Profile Ready to Upload... Please upload the following file to https://app.modelteam.ai/jobs")
        print(final_output_file)
        print('*' * 50)
        print(
            "Please note that the final profile will be generated on the server side with another ML model consuming the numbers from the JSON file that you upload.")
    else:
        print("Changes were not saved. Exiting... Please run the script again.")
        sys.exit(1)
