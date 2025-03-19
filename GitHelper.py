import os
import subprocess
import sys
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, \
    QListWidget, QLabel, QComboBox, QTextEdit, QListWidgetItem, QSpinBox, QDialog, QCheckBox

from edit_skills import run_edit_and_sign
from setup_utils import run_model_team_git_parser, get_profile_path_file_name

button_style = """
    QPushButton {
        background-color: #0078D4;  /* Nice blue shade */
        color: white;
        font-size: 14px;
        font-weight: bold;
        border-radius: 6px;
        padding: 8px 16px;
        border: 2px solid #005A9E;
    }
    QPushButton:hover {
        background-color: #005A9E;
    }
    QPushButton:pressed {
        background-color: #004578;
    }
    QPushButton:disabled {
        background-color: #C8C8C8;
        color: #6A6A6A;
        border: 2px solid #979797;
    }
"""


class GitHelperTool(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('modelteam Git Stats Helper')
        self.setStyleSheet("background-color: #333333; color: white;")
        self.setGeometry(100, 100, 800, 800)

        # Initialize variables
        self.git_repos = []
        self.selected_repos = []
        self.current_user = self.get_git_user_email()
        # default path, user's home directory
        self.input_path = os.path.expanduser("~")
        self.num_years = 5

        # Layouts
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Widgets
        self.path_label = QLabel(
            "Parent directory to scan for Git repos. You can pick and choose which repos to include in your profile.\n(Choose home directory if you want to get all git repos)", self)
        self.path_input = QLabel(self)

        self.browse_button = QPushButton('1. Browse', self)
        self.browse_button.clicked.connect(self.browse_directory)
        self.browse_button.setMaximumSize(250, 50)
        # set button color to blue
        self.browse_button.setStyleSheet(button_style)
        self.repo_list_label = QLabel("Pick repos to add to your profile", self)
        self.repo_list = QListWidget(self)

        self.scan_authors_button = QPushButton('2. Scan Git Email IDs', self)
        self.scan_authors_button.clicked.connect(self.scan_for_authors)
        self.scan_authors_button.setStyleSheet(button_style)
        self.scan_authors_button.setMaximumSize(250, 50)
        self.scan_authors_button.setEnabled(False)

        self.author_label = QLabel("Select an Author", self)
        self.author_combo = QComboBox(self)
        self.author_note = QLabel("If you have multiple git email IDs, run multiple times to build profile one by one", self)

        self.num_years_label = QLabel("Number of years", self)
        self.num_years_input = QSpinBox(self)
        self.num_years_input.setRange(1, 100)  # Set min/max range
        self.num_years_input.setValue(self.num_years)
        self.num_years_input.valueChanged.connect(lambda x: setattr(self, 'num_years', x))

        self.run_button = QPushButton('3. Generate User Git Stats', self)

        self.force_rerun = QCheckBox("Cleanup and Force Re-run", self)
        self.force_rerun.setChecked(False)

        self.run_button.setStyleSheet(button_style)
        self.run_button.clicked.connect(self.run_git_command)
        self.run_button.setMaximumSize(250, 50)
        self.run_button.setEnabled(False)

        self.output_terminal = QTextEdit(self)
        self.output_terminal.setReadOnly(True)
        # Add logo image (PNG)
        pixmap = QPixmap(os.path.join("images", "modelteam_logo.png"))
        logo_label = QLabel()
        logo_label.setPixmap(pixmap)

        # Layout arrangement
        # path and browse button in same row
        self.layout.addWidget(logo_label)
        self.input_layout = QVBoxLayout()
        self.input_layout.addWidget(self.path_label)
        self.path_layout = QHBoxLayout()
        self.path_layout.addWidget(self.browse_button)
        self.path_layout.addWidget(self.path_input)
        self.input_layout.addLayout(self.path_layout)
        self.layout.addLayout(self.input_layout)
        self.layout.addWidget(self.repo_list_label)
        self.layout.addWidget(self.repo_list)
        self.layout.addWidget(self.scan_authors_button)
        self.author_layout = QHBoxLayout()
        self.author_layout.addWidget(self.author_label, 2)
        self.author_layout.addWidget(self.author_combo, 8)
        self.layout.addLayout(self.author_layout)
        self.layout.addWidget(self.author_note)
        self.num_years_layout = QHBoxLayout()
        self.num_years_layout.addWidget(self.num_years_label, 2)
        self.num_years_layout.addWidget(self.num_years_input, 8)
        self.layout.addLayout(self.num_years_layout)
        self.run_layout = QHBoxLayout()
        self.run_layout.addWidget(self.run_button)
        self.run_label = QLabel("<- This will continue in command line...", self)
        self.run_layout.addWidget(self.run_label)
        self.run_layout.addWidget(self.force_rerun)
        self.layout.addLayout(self.run_layout)
        self.layout.addWidget(self.output_terminal)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", directory=self.input_path)
        if directory:
            self.path_input.setText(f"({directory})")
            self.input_path = directory
            self.find_git_repos()

    def find_git_repos(self):
        """Find all Git repositories in the provided path."""
        self.git_repos = []
        self.selected_repos = []
        self.author_combo.clear()
        self.repo_list.clear()

        for root, dirs, files in os.walk(self.input_path):
            print("Scanning for Git repositories in " + root)
            if '.git' in dirs:
                repo_path = root
                self.git_repos.append(repo_path)
                item = QListWidgetItem(repo_path)  # Create a list item for the repo
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)  # Make it checkable
                item.setCheckState(Qt.Checked)  # Default to checked
                self.repo_list.addItem(item)  # Add item to the list
                dirs[:] = []  # Don't recurse into subdirectories
            else:
                dirs[:] = [d for d in dirs if not d.startswith('.')]

        if not self.git_repos:
            self.output_terminal.append("No Git repositories found.")
        else:
            self.scan_authors_button.setEnabled(True)

    def scan_for_authors(self):
        """Scan the selected repositories and populate the authors combo box."""
        selected_repos = []

        for i in range(self.repo_list.count()):
            item = self.repo_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_repos.append(item.text())

        self.selected_repos = selected_repos

        if not selected_repos:
            self.output_terminal.append("Please select at least one repository.")
            return

        authors = self.find_authors()

        self.author_combo.clear()
        self.author_combo.addItems(authors[:20])  # Display only the first 10 authors
        self.run_button.setEnabled(True)

    def find_authors(self):
        """Find authors from the selected repositories."""
        authors = {}
        since_date = (datetime.now() - timedelta(days=365 * self.num_years)).strftime('%Y-%m-%d')

        for repo in self.selected_repos:
            try:
                # Change directory to the repository and get the authors' emails
                result = subprocess.check_output(
                    ['git', 'log', '--since', since_date, '--pretty=format:%ae', '--abbrev-commit'], cwd=repo)
                author_list = result.decode("utf-8").splitlines()
                deduped_authors = list(set(author_list))
                for author in deduped_authors:
                    if not author:
                        continue
                    if author in authors:
                        authors[author] += 1
                    else:
                        authors[author] = 1
            except subprocess.CalledProcessError:
                continue
        authors.pop(self.current_user, None)  # Remove the current user from the list
        sorted_authors = sorted(authors.keys(), key=lambda x: (-authors[x], x.lower()))
        if self.current_user:
            sorted_authors.insert(0, self.current_user)
        return sorted_authors

    def get_git_user_email(self):
        """Get the current Git user email."""
        try:
            result = subprocess.check_output(["git", "config", "--global", "user.email"], stderr=subprocess.STDOUT)
            return result.decode("utf-8").strip()
        except subprocess.CalledProcessError:
            return ""

    def run_git_command(self):
        """Run the Git command using the selected repos and author."""
        selected_author = self.author_combo.currentText()

        if not self.selected_repos or not selected_author:
            self.output_terminal.append("Please select at least one repository and an author.")
            return
        self.accept()

    def get_selected_data(self):
        selected_author = self.author_combo.currentText()
        return self.selected_repos, selected_author, self.num_years, self.force_rerun.isChecked()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet("QListWidget { font-size: 12px; border: 1px solid white; } "
                      "QLabel { font-size: 12px; font-weight: bold; } "
                      "QTextEdit { font-size: 12px; border: 1px solid white; } "
                      "QSpinBox { font-size: 14px; border: 1px solid white; } "
                      "QComboBox { font-size: 14px; border: 1px solid white; }")
    window = GitHelperTool()
    if window.exec_() == QDialog.Accepted:
        selected_repos, selected_author, num_years, force_rerun = window.get_selected_data()
        tmp_repo_file_name = os.path.join(os.getcwd(), "repo_list_autogen.txt")
        with open(tmp_repo_file_name, "w") as f:
            for repo in selected_repos:
                f.write(repo + "\n")
        profile_path_file = get_profile_path_file_name(selected_author)
        if os.path.exists(profile_path_file):
            os.remove(profile_path_file)
        output_path = run_model_team_git_parser(tmp_repo_file_name, selected_author, int(num_years), False, None,
                                                force_rerun)
        with open(profile_path_file, "w") as f:
            f.write(output_path)
        if output_path:
            run_edit_and_sign(output_path, selected_author, False, False)
    else:
        print("Dialog closed... error")
