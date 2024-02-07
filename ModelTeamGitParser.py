import argparse
import json
import os
import random
import re

from .utils.constants import ADDED, DELETED, TIME_SERIES, LANG, LIBS, COMMITS, TOUCH_COUNT, START_TIME, \
    IMPORTS_ADDED, END_TIME, IMPORTS_IN_FILE, MIN_LINES_ADDED, SIGNIFICANT_CONTRIBUTION, REFORMAT_CHAR_LIMIT, \
    SIGNIFICANT_CONTRIBUTION_CHAR_LIMIT, TOO_BIG_TO_ANALYZE_LIMIT, TOO_BIG_TO_ANALYZE, \
    SIGNIFICANT_CONTRIBUTION_LINE_LIMIT, MAX_DIFF_SIZE, STATS, USER, REPO, REPO_PATH
from .utils.utils import get_file_extension, run_commandline_command, timestamp_to_yyyy_mm, \
    get_num_chars_changed, get_language_parser

TRAIN_FLAG = False
ONE_MONTH = 30 * 24 * 60 * 60
ONE_WEEK = 7 * 24 * 60 * 60
THREE_MONTH = 3 * 30 * 24 * 60 * 60

debug = False


class ModelTeamGitParser:
    def __init__(self):
        self.keep_only_public_libraries = True

    @staticmethod
    def add_to_time_series_stats(commits, file_extension, yyyy_mm, key, inc_count):
        if file_extension not in commits[LANG]:
            commits[LANG][file_extension] = {}
            commits[LANG][file_extension][TIME_SERIES] = {}
        if yyyy_mm not in commits[LANG][file_extension][TIME_SERIES]:
            commits[LANG][file_extension][TIME_SERIES][yyyy_mm] = {}
        if key not in commits[LANG][file_extension][TIME_SERIES][yyyy_mm]:
            commits[LANG][file_extension][TIME_SERIES][yyyy_mm][key] = inc_count
        else:
            commits[LANG][file_extension][TIME_SERIES][yyyy_mm][key] += inc_count

    def get_commits_for_each_user(self, repo_path, username=None):
        """
        Get the list of commits for each user in the given repo. If username is None, then get commits for all users
        :param repo_path:
        :param username:
        :return:
        """
        commits = {}
        command = self.get_commit_log_command(repo_path, username)
        result = run_commandline_command(command)
        if result:
            lines = result.strip().split('\n')
            for line in lines:
                (author_email, commit_timestamp, commit_hash) = line.split('\x01')
                # ignore if email is empty
                if not author_email:
                    continue
                if author_email not in commits:
                    commits[author_email] = {}
                    commits[author_email][COMMITS] = []
                commits[author_email][COMMITS].append((commit_hash, int(commit_timestamp)))
        return commits

    def get_commit_log_command(self, repo_path, username):
        return f'git -C {repo_path} log --pretty=format:"%ae%x01%ct%x01%H"  --author="{username}"'

    def update_line_num_stats(self, repo_path, commit_hash, user_commit_stats, yyyy_mm):
        # Get the line stats for each file in the given commit
        command = f'git -C {repo_path} show --numstat --diff-filter=d {commit_hash}'
        result = run_commandline_command(command)
        file_line_stats = {}  # Dictionary to store file line stats
        if result:
            file_stats = result.strip().split('\n')
            for stats in file_stats:
                parts = stats.split('\t')
                # ignore lines if it doesnt start with a number
                if not stats or not stats[0].isdigit():
                    continue
                if len(parts) != 3:
                    print(f"Error parsing line stats {repo_path} - {commit_hash} - {stats}", flush=True)
                    continue
                added_lines, deleted_lines, file_path = stats.split('\t')
                # ignore if these are not valid numbers
                if not added_lines.isdigit() or not deleted_lines.isdigit() or added_lines + deleted_lines == 0:
                    continue
                # handle renames /home/{ xyx => abc }/test.py -> /home/abc/test.py
                if "=>" in file_path:
                    pattern = re.compile(r"(.*){.* => (.*)}(.*)")
                    file_path = pattern.sub(r"\1\2\3", file_path)
                file_extension = get_file_extension(file_path)
                parser = get_language_parser(file_extension, None, file_path, self.keep_only_public_libraries)
                if not parser:
                    continue
                added = int(added_lines)
                deleted = int(deleted_lines)
                if file_extension not in user_commit_stats[LANG]:
                    user_commit_stats[LANG][file_extension] = {}
                    user_commit_stats[LANG][file_extension][TIME_SERIES] = {}
                language = user_commit_stats[LANG][file_extension]
                self.add_to_time_series_stats(user_commit_stats, file_extension, yyyy_mm, ADDED, added)
                self.add_to_time_series_stats(user_commit_stats, file_extension, yyyy_mm, DELETED, deleted)
                if added > MIN_LINES_ADDED:
                    if START_TIME not in language:
                        language[START_TIME] = yyyy_mm
                    elif language[START_TIME] > yyyy_mm:
                        language[START_TIME] = yyyy_mm
                    if END_TIME not in language:
                        language[END_TIME] = yyyy_mm
                    elif language[END_TIME] < yyyy_mm:
                        language[END_TIME] = yyyy_mm
                    file_line_stats[f"{repo_path}/{file_path}"] = [added, deleted]
        return file_line_stats

    def generate_user_profiles(self, repo_path, user_stats, labels, username):
        user_commits = self.get_commits_for_each_user(repo_path, username)
        if user_commits:
            for user in user_commits.keys():
                self.process_user(labels, repo_path, user, user_commits, user_stats)
        else:
            print(f"No commits found for {username}")

    def process_user(self, labels, repo_path, user, user_commits, user_stats):
        commits = user_commits[user]
        if user not in user_stats:
            user_stats[user] = {}
        user_commit_stats = user_stats[user]
        user_commit_stats[LANG] = {}
        # iterate through each commit from oldest to newest
        sorted_commits = sorted(commits[COMMITS], key=lambda x: x[1])
        for commit in sorted_commits:
            self.process_commit(commit, user_commit_stats, labels, repo_path, user)

    @staticmethod
    def aggregate_library_helper(import_type, commits, file_extension, libraries, yyyy_mm):
        if file_extension not in commits[LANG]:
            commits[LANG][file_extension] = {}
        if LIBS not in commits[LANG][file_extension]:
            commits[LANG][file_extension][LIBS] = {}
        if import_type not in commits[LANG][file_extension][LIBS]:
            commits[LANG][file_extension][LIBS][import_type] = {}
        for library in libraries:
            libraries_added = commits[LANG][file_extension][LIBS][import_type]
            if library not in libraries_added:
                libraries_added[library] = {
                    TOUCH_COUNT: 1,
                    TIME_SERIES: [yyyy_mm]
                }
            else:
                libraries_added[library][TOUCH_COUNT] += 1
                if yyyy_mm not in libraries_added[library][TIME_SERIES]:
                    libraries_added[library][TIME_SERIES].append(yyyy_mm)

    def eval_code_model(self, original_diff, time_period):
        # TODO use ml model to predict the change
        return 0
        pass

    @staticmethod
    def get_newly_added_snippets(git_diff):
        """
        Given a git diff, return the newly added snippets. These snippets should be continuous chunks of code that got added
        It can be a new function. It should be a minimum of 5 lines of code
        :param git_diff:
        :return:
        """
        lines = git_diff.split('\n')
        snippets = []
        snippet = []
        for line in lines:
            if line.startswith('+'):
                snippet.append(line[1:])  # remove '+' sign
            else:
                if len(snippet) >= 5:  # minimum lines of code
                    snippets.append('\n'.join(snippet))
                snippet = []  # reset snippet
        # check for the last snippet
        if len(snippet) >= 5:
            snippets.append('\n'.join(snippet))
        return snippets

    def get_commit_history_for_a_file(self, repo_path, filename, commit_hash):
        command = f"""git -C {repo_path} log --numstat --pretty=format:"%x01%ae%x01%ct%x01%H" {commit_hash}^.. -- {filename}"""
        result = run_commandline_command(command)
        if not result:
            return None
        file_history_stats = result.strip().split('\n')
        commit_history = []
        author_email = None
        commit_timestamp = 0
        c_hash = None
        for line in file_history_stats:
            if line.startswith('\x01'):
                parts = line.split('\x01')
                author_email = parts[1]
                commit_timestamp = int(parts[2])
                c_hash = parts[3]
            elif line.endswith(filename):
                parts = line.split('\t')
                if parts[0] == '-':
                    continue
                added = int(parts[0])
                commit_history.append((author_email, commit_timestamp, added, c_hash))
        if commit_history:
            commit_history = sorted(commit_history, key=lambda x: x[1])
        return commit_history

    def break_diff_and_process_each_file(self, commit_hash, git_diff, repo_path, file_line_stats, user_commit_stats,
                                         labels, yyyy_mm, curr_user, src_prefix, dest_prefix):
        file_diffs = re.split(fr'diff --git {src_prefix}/', git_diff)

        for file_diff in file_diffs[1:]:  # ignore the first element
            file_lines = file_diff.split('\n')
            file_name = file_lines[0].strip().split(f" {dest_prefix}/")[1]
            filename_with_path = f"{repo_path}/{file_name}"
            if filename_with_path not in file_line_stats:
                # Not a big change, so ignoring
                continue
            file_extension = get_file_extension(filename_with_path)
            file_diff_content = "\n".join(file_lines[5:])  # ignore the first 5 lines. They are usually not code
            parser = get_language_parser(file_extension, file_diff_content, filename_with_path,
                                         self.keep_only_public_libraries)
            if not parser:
                # Not a supported language, so ignoring
                continue
            if file_name not in labels[LIBS] and os.path.isfile(f"{repo_path}/{file_name}"):
                library_names = parser.get_library_names(include_all_libraries=True)
                if library_names:
                    labels[LIBS][file_name] = library_names
            if len(file_diff) > TOO_BIG_TO_ANALYZE_LIMIT:
                # Any single file diff with more than 20000 chars changed is too big to analyze
                self.add_to_time_series_stats(user_commit_stats, file_extension, yyyy_mm, TOO_BIG_TO_ANALYZE, 1)
                continue
            lines_added = file_line_stats[filename_with_path][0]
            lines_deleted = file_line_stats[filename_with_path][1]
            if lines_added < SIGNIFICANT_CONTRIBUTION_LINE_LIMIT:
                # Not a significant contribution
                continue
            num_chars_changed = get_num_chars_changed(file_diff_content)
            if num_chars_changed < REFORMAT_CHAR_LIMIT:
                self.add_to_time_series_stats(user_commit_stats, file_extension, yyyy_mm, ADDED, -1 * lines_added)
                self.add_to_time_series_stats(user_commit_stats, file_extension, yyyy_mm, DELETED, -1 * lines_deleted)
                continue
            # Set of files with significant contribution for each month
            if num_chars_changed > SIGNIFICANT_CONTRIBUTION_CHAR_LIMIT:
                self.add_to_time_series_stats(user_commit_stats, file_extension, yyyy_mm, SIGNIFICANT_CONTRIBUTION, 1)
                self.process_sig_contrib(commit_hash, curr_user, file_diff_content, file_extension, file_name, labels,
                                         repo_path, user_commit_stats, yyyy_mm)
                if file_name in labels[LIBS]:
                    self.aggregate_library_helper(IMPORTS_IN_FILE, user_commit_stats, file_extension,
                                                  labels[LIBS][file_name], yyyy_mm)
                library_names = parser.get_library_names(include_all_libraries=False)
                if library_names:
                    self.aggregate_library_helper(IMPORTS_ADDED, user_commit_stats, file_extension, library_names,
                                                  yyyy_mm)

    def process_sig_contrib(self, commit_hash, curr_user, file_diff_content, file_extension, file_name, labels,
                            repo_path, user_commit_stats, yyyy_mm):
        snippets = self.get_newly_added_snippets(file_diff_content)
        if snippets:
            index = 0
            for snippet in snippets:
                index += 1
                # TODO: Eval model to predict skills and other quality scores
            print(f"Found {len(snippets)} snippets in {file_name}", flush=True)

    def deep_analysis_of_a_commit(self, repo_path, commit_hash, file_line_stats, user_commit_stats, labels, yyyy_mm,
                                  curr_user):
        src_prefix = random.randint(0, 1000)
        dest_prefix = random.randint(0, 1000)
        # Analyze the actual code changes in the given commit
        file_list = ""
        for file in file_line_stats.keys():
            file_list += f'"{file}" '
        command = f'git -C {repo_path} show --src-prefix={src_prefix}/ --dst-prefix={dest_prefix}/ {commit_hash} -- {file_list}'
        git_diff = run_commandline_command(command)
        if git_diff:
            self.break_diff_and_process_each_file(commit_hash, git_diff, repo_path, file_line_stats, user_commit_stats,
                                                  labels, yyyy_mm, curr_user, src_prefix, dest_prefix)

    def process_commit(self, commit, user_commit_stats, labels, repo_path, curr_user):
        commit_hash = commit[0]
        commit_timestamp = commit[1]
        yyyy_mm = timestamp_to_yyyy_mm(commit_timestamp)
        file_list_with_sig_change = self.update_line_num_stats(repo_path, commit_hash, user_commit_stats, yyyy_mm)
        if file_list_with_sig_change:
            # check if total lines added is < 5000 in all the files
            total_lines_added = 0
            for file in file_list_with_sig_change.keys():
                total_lines_added += file_list_with_sig_change[file][0]
            if total_lines_added < MAX_DIFF_SIZE:
                # Any single commit with more than 5000 lines changed is too big to analyze
                self.deep_analysis_of_a_commit(repo_path, commit_hash, file_list_with_sig_change, user_commit_stats,
                                               labels, yyyy_mm, curr_user)

    def process_single_repo(self, repo_path, output_path, username):
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(f"{output_path}/stats", exist_ok=True)
        user_stats_output_file_name = f"""{output_path}/stats/{repo_path.replace("/", "_")}.jsonl"""
        user_profiles = {}
        repo_level_data = {LIBS: {}}
        self.generate_user_profiles(repo_path, user_profiles, repo_level_data, username)
        # TODO: Email validation, A/B profiles
        if user_profiles:
            # Store hash to file
            with open(user_stats_output_file_name, "w") as f:
                repo_name = repo_path.split("/")[-1]
                for user in user_profiles:
                    f.write("{")
                    f.write(f"\"{REPO_PATH}\": ")
                    f.write(f"{json.dumps(repo_path)}, ")
                    f.write(f"\"{REPO}\": ")
                    f.write(f"{json.dumps(repo_name)}, ")
                    f.write(f"\"{USER}\": ")
                    f.write(f"{json.dumps(user)}, \"{STATS}\": {json.dumps(user_profiles[user])}")
                    f.write("}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse Git Repositories')
    parser.add_argument('--input_path', type=str, help='Path to the input folder containing git repos')
    parser.add_argument('--output_path', type=str, help='Path to the output folder')
    parser.add_argument('--user_email', type=str, help='User email, if present will generate stats only for that user')

    args = parser.parse_args()
    input_path = args.input_path
    output_path = args.output_path
    username = args.user_email

    if not input_path or not output_path or not username:
        print("Invalid arguments")
        exit(1)

    cnt = 0
    # iterate through all the folders in base_path and use it as repo_path
    sorted_folders = sorted(os.listdir(input_path))
    git_parser = ModelTeamGitParser()
    for folder in sorted_folders:
        if os.path.isdir(f"{input_path}/{folder}") and os.path.isdir(f"{input_path}/{folder}/.git"):
            print(f"Processing {folder}", flush=True)
            repo_path = f"{input_path}/{folder}"
            run_commandline_command(f"git -C {repo_path} pull")
            git_parser.process_single_repo(repo_path, output_path, username)
        else:
            print(f"Skipping {folder}")
    print(f"Processed {cnt} out of {len(sorted_folders)}")
