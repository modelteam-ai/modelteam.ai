import argparse
import configparser
import datetime
import json
import os
import random
import re
import sys

import torch

from modelteam_utils.constants import (ADDED, DELETED, TIME_SERIES, LANGS, LIBS, COMMITS, START_TIME,
                                       END_TIME, MIN_LINES_ADDED, SIGNIFICANT_CONTRIBUTION, REFORMAT_CHAR_LIMIT,
                                       TOO_BIG_TO_ANALYZE_LIMIT, TOO_BIG_TO_ANALYZE,
                                       SIGNIFICANT_CONTRIBUTION_LINE_LIMIT, MAX_DIFF_SIZE, STATS, USER, REPO, REPO_PATH,
                                       SCORES, SIG_CODE_SNIPPETS,
                                       SKILLS, FILE, IMPORTS, T5_CHUNK_CHAR_LIMIT, VERSION, PROFILES, PHC, TIMESTAMP)
from modelteam_utils.constants import SKILL_PREDICTION_LIMIT, LIFE_OF_PY_PREDICTION_LIMIT, C2S, LIFE_OF_PY, \
    MODEL_TYPES, I2S
from modelteam_utils.crypto_utils import generate_hc
from modelteam_utils.utils import break_code_snippets_to_chunks, filter_skills
from modelteam_utils.utils import eval_llm_batch_with_scores, init_model, get_model_list
from modelteam_utils.utils import get_file_extension, run_commandline_command, timestamp_to_yyyy_mm, \
    get_num_chars_changed, get_language_parser, normalize_docstring
from modelteam_utils.utils import sha256_hash, anonymize, load_repo_user_list, get_repo_user_key

TRAIN_FLAG = False
ONE_MONTH = 30 * 24 * 60 * 60
ONE_WEEK = 7 * 24 * 60 * 60
THREE_MONTH = 3 * 30 * 24 * 60 * 60

debug = False
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

TMP_MAX_YYYY_MM = "tmp_max_yyyy_mm"


class ModelTeamGitParser:
    def __init__(self, config):
        self.keep_only_public_libraries = True
        self.config = config

    @staticmethod
    def add_to_time_series_stats(commits, file_extension, yyyy_mm, key, inc_count):
        if file_extension not in commits[LANGS]:
            commits[LANGS][file_extension] = {}
            commits[LANGS][file_extension][TIME_SERIES] = {}
        if yyyy_mm not in commits[LANGS][file_extension][TIME_SERIES]:
            commits[LANGS][file_extension][TIME_SERIES][yyyy_mm] = {}
        if key not in commits[LANGS][file_extension][TIME_SERIES][yyyy_mm]:
            commits[LANGS][file_extension][TIME_SERIES][yyyy_mm][key] = inc_count
        else:
            commits[LANGS][file_extension][TIME_SERIES][yyyy_mm][key] += inc_count

    def get_commits_for_each_user(self, repo_path, min_months, num_months, usernames=set()):
        """
        Get the list of commits for each user in the given repo. If username is None, then get commits for all users
        :param repo_path:
        :param usernames:
        :return:
        """
        commits = {}
        command = self.get_commit_log_command(repo_path, usernames, num_months)
        result = run_commandline_command(command)
        if result:
            lines = result.strip().split('\n')
            user_months = {}
            for line in lines:
                (author_email, commit_timestamp, commit_hash) = line.split('\x01')
                # TODO: Check if this is needed
                if usernames and author_email not in usernames:
                    print(f"ERROR: EmailID mismatch. Given email {usernames} but found {author_email}")
                    continue
                # ignore if email is empty
                if not author_email:
                    continue
                if author_email not in commits:
                    commits[author_email] = {}
                    commits[author_email][COMMITS] = []
                if author_email not in user_months:
                    user_months[author_email] = set()
                user_months[author_email].add(timestamp_to_yyyy_mm(int(commit_timestamp)))
                commits[author_email][COMMITS].append((commit_hash, int(commit_timestamp)))
            for user in user_months:
                if len(user_months[user]) < min_months:
                    del commits[user]
        return commits

    @staticmethod
    def get_commit_log_command(repo_path, usernames, num_months):
        if usernames:
            usernames_pattern = " ".join([f"--author={user}" for user in usernames])
            return f'git -C {repo_path} log --pretty=format:"%ae%x01%ct%x01%H"  {usernames_pattern} --since="{num_months} months ago"'
        else:
            return f'git -C {repo_path} log --pretty=format:"%ae%x01%ct%x01%H" --since="{num_months} months ago"'

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
                if file_extension not in user_commit_stats[LANGS]:
                    user_commit_stats[LANGS][file_extension] = {}
                    user_commit_stats[LANGS][file_extension][TIME_SERIES] = {}
                language = user_commit_stats[LANGS][file_extension]
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

    def is_allowed_user(self, repo_name, user):
        global allowed_users
        if allowed_users:
            key = get_repo_user_key(repo_name, user)
            return key in allowed_users
        # If allowed_users is empty, then all users are allowed
        return True

    def generate_user_profiles(self, repo_path, user_stats, labels, usernames, repo_name, min_months, num_months):
        user_commits = self.get_commits_for_each_user(repo_path, min_months, num_months, usernames)
        ignored_users = 0
        if user_commits:
            for user in user_commits.keys():
                if not self.is_allowed_user(repo_name, user):
                    ignored_users += 1
                    continue
                self.process_user(labels, repo_path, user, user_commits, user_stats)
            if ignored_users:
                print(f"Ignored {ignored_users} users for {repo_name}", flush=True)
        else:
            print(f"Not enough contribution for {usernames} in {repo_name} ({min_months} months)", flush=True)

    def process_user(self, labels, repo_path, user, user_commits, user_stats):
        commits = user_commits[user]
        if user not in user_stats:
            user_stats[user] = {}
        user_commit_stats = user_stats[user]
        user_commit_stats[LANGS] = {}
        # iterate through each commit from oldest to newest
        sorted_commits = sorted(commits[COMMITS], key=lambda x: x[1])
        for commit in sorted_commits:
            self.process_commit(commit, user_commit_stats, labels, repo_path, user)

    @staticmethod
    def aggregate_library_helper(import_type, commits, file_extension, libraries, yyyy_mm):
        # TODO change this to bucketize the libs
        if file_extension not in commits[LANGS]:
            commits[LANGS][file_extension] = {}
        if LIBS not in commits[LANGS][file_extension]:
            commits[LANGS][file_extension][LIBS] = {}
        if import_type not in commits[LANGS][file_extension][LIBS]:
            commits[LANGS][file_extension][LIBS][import_type] = {}
        if yyyy_mm not in commits[LANGS][file_extension][LIBS][import_type]:
            commits[LANGS][file_extension][LIBS][import_type][yyyy_mm] = []
        commits[LANGS][file_extension][LIBS][import_type][yyyy_mm].append(libraries)

    @staticmethod
    def get_newly_added_snippets(git_diff):
        """
        Given a git diff, return the newly added snippets. These snippets should be continuous chunks of code that got added
        It can be a new function. It should be a minimum of 10 lines of code
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
                if len(snippet) >= 10:  # minimum lines of code
                    snippets.append('\n'.join(snippet))
                snippet = []  # reset snippet
        # check for the last snippet
        if len(snippet) >= 10:
            snippets.append('\n'.join(snippet))
        return snippets

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
                # Any single file diff with more than 10000 chars changed is too big to analyze
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
            self.process_sig_contrib(commit_hash, curr_user, file_diff_content, file_extension, file_name, labels,
                                     repo_path, user_commit_stats, yyyy_mm)

    def process_sig_contrib(self, commit_hash, curr_user, file_diff_content, file_extension, file_name, labels,
                            repo_path, commits, yyyy_mm):
        snippets = self.get_newly_added_snippets(file_diff_content)
        if snippets:
            self.add_to_time_series_stats(commits, file_extension, yyyy_mm, SIGNIFICANT_CONTRIBUTION, len(snippets))
            if file_extension not in commits[LANGS]:
                commits[LANGS][file_extension] = {}
            if SIG_CODE_SNIPPETS not in commits[LANGS][file_extension]:
                commits[LANGS][file_extension][SIG_CODE_SNIPPETS] = {}
            if yyyy_mm not in commits[LANGS][file_extension][SIG_CODE_SNIPPETS]:
                commits[LANGS][file_extension][SIG_CODE_SNIPPETS][yyyy_mm] = []
            commits[LANGS][file_extension][SIG_CODE_SNIPPETS][yyyy_mm].append((file_name, snippets))

    def deep_analysis_of_a_commit(self, repo_path, commit_hash, file_line_stats, user_commit_stats, labels, yyyy_mm,
                                  curr_user):
        src_prefix = random.randint(0, 1000)
        dest_prefix = random.randint(0, 1000)
        # Analyze the actual code changes in the given commit
        file_list = ""
        for file in file_line_stats.keys():
            file = file.replace(repo_path + "/", "")
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

    def save_libraries(self, repo_level_data, libraries_file_name, repo_name, repo_path):
        with open(libraries_file_name, "w") as f:
            for file_name in repo_level_data[LIBS].keys():
                f.write("{")
                f.write(f"\"{REPO_PATH}\": ")
                f.write(f"{json.dumps(repo_path)}, ")
                f.write(f"\"{REPO}\": ")
                f.write(f"{json.dumps(repo_name)}, ")
                f.write(f"\"{FILE}\": ")
                f.write(
                    f"{json.dumps(file_name)}, \"{IMPORTS}\": {json.dumps(repo_level_data[LIBS][file_name])}")
                f.write("}\n")

    def load_library_data(self, libraries_file_name, repo_level_data):
        if os.path.exists(libraries_file_name):
            with open(libraries_file_name, "r") as f:
                for line in f:
                    lib_data = json.loads(line)
                    file_name = lib_data[FILE]
                    repo_level_data[LIBS][file_name] = lib_data[IMPORTS]

    def process_single_repo(self, repo_path, user_stats_output_file_name, repo_lib_output_file_name,
                            final_output, min_months, usernames, num_months):
        skill_min_score = float(self.config['modelteam.ai']['skill_min_score'])
        lop_min_score = float(self.config['modelteam.ai']['lop_min_score'])
        min_scores = {C2S: skill_min_score, LIFE_OF_PY: lop_min_score, I2S: skill_min_score}
        user_profiles = {}
        repo_level_data = {LIBS: {}, SKILLS: {}}
        if not os.path.exists(user_stats_output_file_name):
            repo_name = repo_path.split("/")[-1]
            self.generate_user_profiles(repo_path, user_profiles, repo_level_data, usernames, repo_name, min_months,
                                        num_months)
            if repo_level_data[LIBS]:
                self.save_libraries(repo_level_data, repo_lib_output_file_name, repo_name, repo_path)
            # TODO: Email validation, A/B profiles
            if user_profiles:
                # Store hash to file
                with open(user_stats_output_file_name, "w") as f:
                    for user in user_profiles:
                        self.write_user_profile_to_file(f, repo_name, repo_path, user, user_profiles[user])
        if not args.skip_model_eval and os.path.exists(user_stats_output_file_name):
            if not os.path.exists(final_output):
                if not repo_level_data[LIBS]:
                    self.load_library_data(repo_lib_output_file_name, repo_level_data)
                for file in repo_level_data[LIBS].keys():
                    file_extension = get_file_extension(file)
                    parser = get_language_parser(file_extension, "", file, self.keep_only_public_libraries)
                    if not parser:
                        repo_level_data[LIBS][file] = ""
                        continue
                    lib_list = repo_level_data[LIBS][file]
                    libs_in_file = ""
                    for imp in lib_list:
                        imp = imp.strip()
                        libs_in_file += parser.get_import_prefix() + imp + "\n"
                    repo_level_data[LIBS][file] = libs_in_file
                # when starting from tmp, we need to get repo details from the jsonl file
                if not user_profiles:
                    with open(user_stats_output_file_name, "r") as f:
                        for line in f:
                            user_stats = json.loads(line)
                            # Same repo for all users
                            repo_name = user_stats[REPO]
                            repo_path = user_stats[REPO_PATH]
                            if USER in user_stats and self.is_allowed_user(repo_name, user_stats[USER]):
                                user_profiles[user_stats[USER]] = user_stats[STATS]
                has_new_data = 0
                for model_type in MODEL_TYPES:
                    models = get_model_list(self.config, model_type)
                    for model_path in models:
                        # Evaluate 1 model at a time to avoid memory issues
                        model_data = init_model(model_path, model_type, self.config, device)
                        if model_type == C2S or model_type == LIFE_OF_PY or model_type == I2S:
                            for user in user_profiles:
                                user_profile = user_profiles[user]
                                if SKILLS not in user_profile:
                                    user_profile[SKILLS] = {}
                                if TMP_MAX_YYYY_MM in user_profile and user_profile[TMP_MAX_YYYY_MM] < min_months:
                                    continue
                                has_new_data += self.extract_skills(user_profile, repo_level_data, min_months,
                                                                    model_data, repo_name)
                if has_new_data == 0:
                    print(f"No users with extracted skills found for {repo_path}", flush=True)
                    return
                if not user_profiles:
                    print(f"No user profiles found for {repo_path}", flush=True)
                    return
                if not args.keep_repo_name:
                    repo_path = sha256_hash(repo_name)
                    repo_name = anonymize(repo_name)
                with open(final_output, "w") as fo:
                    for user in user_profiles:
                        user_profile = user_profiles[user]
                        if TMP_MAX_YYYY_MM in user_profile and user_profile[TMP_MAX_YYYY_MM] >= min_months:
                            self.filter_non_public_data(user_profile)
                            filter_skills(user_profile, min_scores)
                            self.write_user_profile_to_file(fo, repo_name, repo_path, user, user_profile)

    def write_user_profile_to_file(self, f, repo_name, repo_path, user, user_profile):
        f.write("{")
        f.write(f"\"{VERSION}\": {json.dumps(self.config['modelteam.ai']['version'])}, ")
        f.write(f"\"{TIMESTAMP}\": {utc_now}, ")
        f.write(f"\"{REPO_PATH}\": {json.dumps(repo_path)}, ")
        f.write(f"\"{REPO}\": {json.dumps(repo_name)}, ")
        f.write(f"\"{USER}\": {json.dumps(user)}, ")
        f.write(f"\"{STATS}\": {json.dumps(user_profile)}")
        f.write("}\n")

    def extract_skills(self, user_profile, repo_level_data, min_months, model_data, repo_name):
        global label_file_list
        features = []
        if LANGS not in user_profile:
            return 0
        lang_stats = user_profile[LANGS]
        # lang, file_name, yyyy_mm, snippet, libs_added, line_count, doc_string_line_count
        for lang in lang_stats:
            if SIG_CODE_SNIPPETS not in lang_stats[lang]:
                continue
            num_months = len(lang_stats[lang][TIME_SERIES])
            if TMP_MAX_YYYY_MM not in user_profile:
                user_profile[TMP_MAX_YYYY_MM] = num_months
            else:
                user_profile[TMP_MAX_YYYY_MM] = max(user_profile[TMP_MAX_YYYY_MM], num_months)
            if TIME_SERIES not in lang_stats[lang] or num_months < min_months:
                continue
            sig_code_snippets = lang_stats[lang][SIG_CODE_SNIPPETS]
            for yyyy_mm in sig_code_snippets.keys():
                monthly_snippets = sig_code_snippets[yyyy_mm]
                for i in range(len(monthly_snippets)):
                    snippets = monthly_snippets[i]
                    file_name = snippets[0]
                    key = get_repo_user_key(repo_name, file_name)
                    is_labeled_file = 0
                    if key in label_file_list:
                        is_labeled_file = 1
                    snippet_list = snippets[1]
                    for snippet in snippet_list:
                        file_extension = get_file_extension(file_name)
                        parser = get_language_parser(file_extension, snippet, file_name,
                                                     self.keep_only_public_libraries)
                        if not parser:
                            continue
                        chunks = break_code_snippets_to_chunks(file_name, snippet, T5_CHUNK_CHAR_LIMIT)
                        for chunk in chunks:
                            lines = chunk.split("\n")
                            line_count = len(lines)
                            doc_string_line_count = self.get_docstring_line_count(lines, parser)
                            libs_in_file = ""
                            if file_name in repo_level_data[LIBS]:
                                libs_in_file = repo_level_data[LIBS][file_name]
                            features.append({"lang": lang, "file_name": file_name, "yyyy_mm": yyyy_mm, "snippet": chunk,
                                             "libs": libs_in_file, "line_count": line_count,
                                             "is_labeled_file": is_labeled_file,
                                             "doc_string_line_count": doc_string_line_count})
        if features:
            self.eval_llm_model(model_data, features, user_profile)
            return len(features)
        return 0

    @staticmethod
    def get_docstring_line_count(lines, parser):
        docstrings = parser.extract_documentation(lines)
        docstring_line_count = 0
        if docstrings:
            for docstring in docstrings:
                norm_docstrings = normalize_docstring(docstring)
                if norm_docstrings:
                    docstring_line_count += len(norm_docstrings)
        return docstring_line_count

    def eval_llm_model(self, model_data, features, user_profile):
        print(f"Evaluating {len(features)} snippets for {model_data['model_tag']}",
              flush=True)
        snippet_key = "snippet"
        if model_data['model_type'] == I2S:
            snippet_key = "libs"
        snippets = [feature[snippet_key] for feature in features]
        if model_data['model_type'] == LIFE_OF_PY:
            limit = LIFE_OF_PY_PREDICTION_LIMIT
        else:
            limit = SKILL_PREDICTION_LIMIT
        # TODO: Add support for batch processing
        skill_list, score_list, sm_score_list = eval_llm_batch_with_scores(model_data['tokenizer'], device,
                                                                           model_data['model'], snippets,
                                                                           model_data['new_tokens'], limit)
        for i in range(len(features)):
            lang = features[i]["lang"]
            yyyy_mm = features[i]["yyyy_mm"]
            line_count = features[i]["line_count"]
            doc_string_line_count = features[i]["doc_string_line_count"]
            is_labeled_file = features[i]["is_labeled_file"]
            ModelTeamGitParser.accumulate_score(user_profile, lang, yyyy_mm, score_list[i], sm_score_list[i],
                                                skill_list[i], line_count, doc_string_line_count,
                                                model_data['model_tag'], model_data['model_type'] == C2S,
                                                is_labeled_file)

    @staticmethod
    def filter_non_public_data(user_profile):
        if TMP_MAX_YYYY_MM in user_profile:
            del user_profile[TMP_MAX_YYYY_MM]
        if LANGS not in user_profile:
            return
        lang_stats = user_profile[LANGS]
        for lang in lang_stats:
            if SIG_CODE_SNIPPETS in lang_stats[lang]:
                del lang_stats[lang][SIG_CODE_SNIPPETS]
            if LIBS in lang_stats[lang]:
                del lang_stats[lang][LIBS]

    @staticmethod
    def accumulate_score(user_profile, lang, yyyy_mm, scores, sm_scores, skills, code_len, doc_string_len, tag, is_c2s,
                         is_labeled_file):
        for i in range(len(skills)):
            s = skills[i]
            score = scores[i]
            sm_score = sm_scores[i]
            if is_c2s:
                if s not in user_profile[SKILLS]:
                    user_profile[SKILLS][s] = 0
                user_profile[SKILLS][s] += sm_score * code_len
            if tag not in user_profile[LANGS][lang][TIME_SERIES][yyyy_mm]:
                user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag] = {}
            if s not in user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag]:
                # min, max, sum, count, code_line_count, doc_string_line_count, is_labeled_file
                user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag][s] = [score, score, 0, sm_score, sm_score, 0, 0, 0,
                                                                           0, 0]
            skill_map = user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag][s]
            skill_map[0] = max(skill_map[0], score)
            skill_map[1] = min(skill_map[1], score)
            skill_map[2] += score
            skill_map[3] = max(skill_map[3], sm_score)
            skill_map[4] = min(skill_map[4], sm_score)
            skill_map[5] += sm_score
            skill_map[6] += 1
            skill_map[7] += code_len
            skill_map[8] += doc_string_len
            skill_map[9] = max(skill_map[9], is_labeled_file)

    @staticmethod
    def add_to_skills(skill_stats, monthly_skills_and_scores, model_path, score_type):
        model_name = f"{model_path}::{score_type}"
        for month in monthly_skills_and_scores:
            skills = monthly_skills_and_scores[month].keys()
            for skill in skills:
                if model_name not in skill_stats:
                    skill_stats[model_name] = {}
                if skill not in skill_stats[model_name]:
                    skill_stats[model_name][skill] = {}
                    skill_stats[model_name][skill][TIME_SERIES] = []
                    skill_stats[model_name][skill][SCORES] = []
                skill_stats[model_name][skill][TIME_SERIES].append(month)
                skill_stats[model_name][skill][SCORES].append(monthly_skills_and_scores[month][skill])


def load_label_files(lf_name):
    label_files = set()
    if lf_name:
        print(f"Loading label files from {lf_name}", flush=True)
        with open(lf_name, "r") as f:
            for line in f:
                labels = json.loads(line)
                if REPO not in labels or FILE not in labels:
                    continue
                repo = labels[REPO]
                file = labels[FILE]
                label_files.add(get_repo_user_key(repo, file))
        print(f"Loaded {len(label_files)} label files", flush=True)
    return label_files


def gen_user_name(users, max_len=255):
    if len(users) == 1:
        return users[0]
    domain_users = {}
    for user in users:
        domain = user.split("@")[1]
        if domain not in domain_users:
            domain_users[domain] = []
        domain_users[domain].append(user)
    user = ""
    for domain in domain_users:
        users += "(" + ",".join(domain_users[domain]) + ")@" + domain + ","
    user = user[:-1]
    if len(user) > max_len:
        user = user[:max_len-3] + "..."
    return user


def merge_json(users, output_file_list, merged_json):
    user = gen_user_name(users)
    phc = generate_hc(os.path.abspath(sys.argv[0]))
    merged_profile = {USER: user, TIMESTAMP: utc_now, PROFILES: [], PHC: phc}
    lines_added = 0
    months = set()
    languages = set()
    skills = set()

    with open(merged_json, "w") as merged_json_writer:
        for profile_json in output_file_list:
            with open(profile_json, "r") as f:
                for line in f:
                    profile = json.loads(line)
                    if LANGS in profile[STATS]:
                        for lang in profile[STATS][LANGS]:
                            if TIME_SERIES in profile[STATS][LANGS][lang]:
                                for month in profile[STATS][LANGS][lang][TIME_SERIES]:
                                    if month not in months:
                                        months.add(month)
                                    if lang not in languages:
                                        languages.add(lang)
                                    lines_added += profile[STATS][LANGS][lang][TIME_SERIES][month][ADDED]
                    if SKILLS in profile[STATS]:
                        for skill in profile[STATS][SKILLS]:
                            if skill not in skills:
                                skills.add(skill)
                    merged_profile[PROFILES].append(profile)
        print("Stats for", user)
        print("Number of repositories analyzed:", len(output_file_list))
        print("Number of months analyzed:", len(months))
        print("Kinds of file analyzed:", ", ".join(languages))
        print("Number of lines analyzed:", lines_added)
        print("Number of skills extracted:", len(skills))
        end_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        time_taken_in_minutes = round((end_ts - utc_now) / 60)
        print("Time taken: ", time_taken_in_minutes, "minutes")
        json.dump(merged_profile, merged_json_writer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse Git Repositories')
    parser.add_argument('--input_path', type=str, help='Path to the input folder containing git repos')
    parser.add_argument('--output_path', type=str, help='Path to the output folder')
    parser.add_argument('--config', type=str, help='Config.ini path')
    parser.add_argument('--user_emails', type=str,
                        help='User emails as CSV, if present will generate stats only for that user')
    # These are advanced options that's usually used for internal use
    parser.add_argument('--skip_model_eval', default=False, help='Skip model evaluation', action='store_true')
    parser.add_argument('--keep_repo_name', default=False, help='Retain Full Repo Name', action='store_true')
    parser.add_argument('--parallel_mode', default=False, help='Multiple Runs may run, check for touch files',
                        action='store_true')
    parser.add_argument('--allow_list', type=str, help='List of repos,users to be allowed', default=None)
    parser.add_argument('--start_from_tmp', default=False, help='Start from tmp', action='store_true')
    parser.add_argument('--label_file_list', type=str, help='Path to the Repo Topics JSONL', default=None)
    parser.add_argument('--num_years', type=int, help='Number of years to consider', default=5)

    args = parser.parse_args()
    input_path = args.input_path
    output_path = args.output_path
    usernames = args.user_emails
    config_file = args.config
    config = configparser.ConfigParser()
    config.read(config_file)
    min_months = int(config['modelteam.ai']['min_months'])
    num_months = args.num_years * 12
    utc_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    allowed_users = load_repo_user_list(args.allow_list)
    label_file_list = load_label_files(args.label_file_list)
    if not input_path or not output_path:
        print("Invalid arguments")
        exit(1)
    if not usernames:
        print("Warning: No user email provided. Will generate stats for all users\nThis will take a very long time",
              flush=True)
    else:
        # split, trim and convert to set
        usernames = set([x.strip() for x in usernames.split(",")])
    cnt = 0
    # iterate through all the folders in base_path and use it as repo_path
    if args.start_from_tmp:
        folder_list = os.listdir(f"{output_path}/tmp-stats")
    else:
        folder_list = os.listdir(input_path)
    randomized_folder_list = random.sample(folder_list, len(folder_list))
    git_parser = ModelTeamGitParser(config)
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(f"{output_path}/tmp-stats", exist_ok=True)
    os.makedirs(f"{output_path}/touch-files", exist_ok=True)
    os.makedirs(f"{output_path}/final-stats", exist_ok=True)
    merged_json = f"{output_path}/mt_profile.json"
    final_outputs = []
    # TODO: Aggregate stats from all repos for a user
    for folder in randomized_folder_list:
        if folder.endswith("_libs.jsonl"):
            continue
        if (os.path.isdir(f"{input_path}/{folder}") and os.path.isdir(
                f"{input_path}/{folder}/.git")) or args.start_from_tmp:
            if args.parallel_mode:
                touch_file = f"{output_path}/touch-files/{folder}"
                if os.path.exists(touch_file):
                    print(f"Skipping {folder} as it is already processed")
                    continue
                else:
                    # There is a very tiny chance that another process might create the file
                    # Randomized file list should have taken care of this
                    try:
                        with open(touch_file, "x") as f:
                            f.write("1")
                    except FileExistsError:
                        print(f"Rare Exception: Skipping {folder} as it is already processed")
                        continue
            cnt += 1
            print(f"Processing {folder}", flush=True)
            if args.start_from_tmp:
                # Repo path won't be real as it reads from tmp-stats
                repo_path = f"{output_path}/tmp-stats/{folder}"
                file_prefix = folder.replace(".jsonl", "")
            else:
                repo_path = f"{input_path}/{folder}"
                file_prefix = f"""{repo_path.replace("/", "_")}"""
            # check if the repo is no longer open. Ignore if it asks for password
            # result = run_commandline_command(f"git -C {repo_path} pull --rebase")
            # if not result:
            #     print(f"Skipping {folder} as it is no longer open")
            #     continue
            user_stats_output_file_name = f"""{output_path}/tmp-stats/{file_prefix}.jsonl"""
            repo_lib_output_file_name = f"""{output_path}/tmp-stats/{file_prefix}_libs.jsonl"""
            final_output = f"""{output_path}/final-stats/{file_prefix}_user_profile.jsonl"""
            if os.path.exists(final_output):
                print(f"Skipping {final_output} as it is already processed")
            else:
                git_parser.process_single_repo(repo_path, user_stats_output_file_name, repo_lib_output_file_name,
                                               final_output, min_months, usernames, num_months)
            if os.path.exists(final_output):
                final_outputs.append(final_output)
        else:
            print(f"Skipping {folder}")
        if final_outputs and args.user_emails:
            merge_json(args.user_emails, final_outputs, merged_json)
    print(f"Processed {cnt} out of {len(folder_list)}")
