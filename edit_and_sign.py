import argparse
import json
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

from modelteam.modelteam_utils.constants import USER, REPO, STATS, SKILLS
from modelteam.modelteam_utils.crypto_utils import encrypt_compress_file

RELEVANT = "Relevant"
NOT_RELEVANT = "Not Relevant"
TOP_SECRET = "Top Secret"

explanation = ("\nThese are the skills that our models predicted after analyzing your code contributions. "
               "These skills will further be scored by another model on the server side."
               "Please select the appropriate choice for each skill to help us improve our model.\n"
               "\n1. Relevant: Keep the skill in your profile."
               "\n2. Not Relevant: Will be removed at the server side."
               "\n3. Top Secret: Dont send this to the server.")


class App:
    def __init__(self, root, email, repocsv, skill_list, choices_file):
        self.root = root
        self.root.title("Edit Profile")

        # Configure dark theme colors
        self.root.configure(background='#333333')
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use a style that supports customization (e.g., 'clam', 'alt', 'default')

        # Define custom colors
        dark_bg = '#333333'
        light_fg = 'white'

        self.style.configure('.', background=dark_bg, foreground=light_fg)
        self.style.map('.', background=[('selected', '#444444')])

        # Top frame for logo and display fields
        top_frame = ttk.Frame(root, style='TFrame', padding=(10, 10, 10, 0))
        top_frame.pack(fill='x')

        # Add logo image (JPEG)
        image = Image.open("images/modelteam_logo.png")
        self.logo = ImageTk.PhotoImage(image)
        logo_label = ttk.Label(top_frame, image=self.logo)
        logo_label.pack(side='left', padx=10)

        # Header frame for email and RepoCSV
        header_frame = ttk.Frame(root, style='TFrame', padding=(10, 10, 10, 0))
        header_frame.pack(fill='x')

        email_label = ttk.Label(header_frame, text=f"Email: {email}", style='TLabel')
        email_label.pack(side='top', anchor='w')

        repo_csv_label = ttk.Label(header_frame, text=f"RepoCSV: {repocsv}", style='TLabel')
        repo_csv_label.pack(side='top', anchor='w')

        repo_csv_label = ttk.Label(header_frame, text=explanation, style='TLabel', wraplength=600)
        repo_csv_label.pack(side='top', anchor='w')
        # Main frame for items and choices
        main_frame = ttk.Frame(root, style='TFrame')
        main_frame.pack(padx=10, pady=10, expand=True, fill='both')

        self.canvas = tk.Canvas(main_frame, background=dark_bg)
        self.scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style='TFrame')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.choices = {}

        for item in skill_list:
            self.add_choice_widget(self.scrollable_frame, item)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.save_button = ttk.Button(root, text="Save Choices", command=self.save_choices)
        self.save_button.pack(pady=10)

        # Save email and RepoCSV for later use
        self.email = email
        self.repocsv = repocsv

    def add_choice_widget(self, frame, item):
        item_frame = ttk.Frame(frame, style='TFrame')
        item_frame.pack(fill='x', pady=5)

        label = ttk.Label(item_frame, text=item)
        label.pack(side='left', padx=5)

        var = tk.StringVar(value="Relevant")
        self.choices[item] = var

        keep_radio = ttk.Radiobutton(item_frame, text="Relevant", variable=var, value="Relevant",
                                     command=self.check_filled)
        not_relevant_radio = ttk.Radiobutton(item_frame, text="Not Relevant", variable=var, value="Not Relevant",
                                             command=self.check_filled)
        remove_conf_radio = ttk.Radiobutton(item_frame, text="Top Secret", variable=var,
                                            value="Top Secret", command=self.check_filled)

        keep_radio.pack(side='left', padx=5)
        not_relevant_radio.pack(side='left', padx=5)
        remove_conf_radio.pack(side='left', padx=5)

    def check_filled(self):
        if all(var.get() != "" for var in self.choices.values()):
            self.save_button.config(state='normal')
        else:
            self.save_button.config(state='disabled')

    def save_choices(self):
        choices_dict = {item: var.get() for item, var in self.choices.items()}
        with open(choices_file, 'w') as f:
            json.dump(choices_dict, f)
        messagebox.showinfo("Save Choices", "Choices saved successfully!")


def edit_profile(profile_jsonl, choices_file):
    with open(profile_jsonl, "r") as f:
        repos = []
        skills = []
        for line in f:
            json_line = json.loads(line)
            email = json_line[USER]
            repos.append(json_line[REPO])
            skills.extend(json_line[STATS][SKILLS].keys())
        root = tk.Tk()
        app = App(root, email, ",".join(repos), skills, choices_file)
        root.mainloop()


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
    edit_profile(args.profile_jsonl, choices_file)
    apply_choices(args.profile_jsonl, choices_file, edited_file)
    encrypt_compress_file(args.profile_jsonl, encrypted_file, args.user_key)
