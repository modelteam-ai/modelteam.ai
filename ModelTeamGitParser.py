import argparse
import configparser
import json
import os
import random
import re

import matplotlib.pyplot as plt
import torch
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from wordcloud import WordCloud

from modelteam_utils.constants import (ADDED, DELETED, TIME_SERIES, LANGS, LIBS, COMMITS, START_TIME,
                                       END_TIME, MIN_LINES_ADDED, SIGNIFICANT_CONTRIBUTION, REFORMAT_CHAR_LIMIT,
                                       TOO_BIG_TO_ANALYZE_LIMIT, TOO_BIG_TO_ANALYZE,
                                       SIGNIFICANT_CONTRIBUTION_LINE_LIMIT, MAX_DIFF_SIZE, STATS, USER, REPO, REPO_PATH,
                                       SCORES, SIG_CODE_SNIPPETS,
                                       SKILLS, FILE, IMPORTS)
from modelteam_utils.constants import SKILL_PREDICTION_LIMIT, LIFE_OF_PY_PREDICTION_LIMIT, C2S, LIFE_OF_PY, \
    MODEL_TYPES
from modelteam_utils.utils import eval_llm_batch_with_scores, init_model, get_model_list
from modelteam_utils.utils import get_file_extension, run_commandline_command, timestamp_to_yyyy_mm, \
    get_num_chars_changed, get_language_parser, get_extension_to_language_map, normalize_docstring

TRAIN_FLAG = False
ONE_MONTH = 30 * 24 * 60 * 60
ONE_WEEK = 7 * 24 * 60 * 60
THREE_MONTH = 3 * 30 * 24 * 60 * 60

debug = False
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def generate_tag_cloud(skill_map, file_name):
    if len(skill_map) > 20:
        skill_map = dict(sorted(skill_map.items(), key=lambda item: item[1], reverse=True)[:20])
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(skill_map)
    # Display the generated word cloud
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("Top Skills", fontsize=24)
    plt.savefig(file_name)


def to_short_date(yyyymm):
    mon_str = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month = int(yyyymm[4:6])
    return f"{mon_str[month - 1]}\n{yyyymm[:4]}"


def generate_ts_plot(ts_stats, file_name):
    years_months = sorted(ts_stats.keys())
    readable_dates = []
    for yyyymm in years_months:
        readable_dates.append(to_short_date(yyyymm))

    # Extract added and deleted values
    added = [ts_stats[key][0] for key in years_months]
    deleted = [ts_stats[key][1] for key in years_months]

    # Plotting
    plt.figure(figsize=(10, 5))
    plt.plot(readable_dates, added, label='Lines Added')
    plt.plot(readable_dates, deleted, label='Lines Deleted')

    plt.xlabel('Time', fontsize=15)
    plt.ylabel('Count', fontsize=15)
    plt.title('Code Contribution Over Time', fontsize=24)
    plt.tick_params(axis='both', which='major', labelsize=12)
    plt.legend(fontsize=15)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(file_name)


def generate_pdf(output_path, user, repo, languages, image_files):
    pdf_file = f"{output_path}/{user}.pdf"
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.setFont("Helvetica", 24)
    c.drawString(50, 700, "ModelTeam.AI")
    c.setFont("Helvetica", 12)
    c.drawString(50, 650, f"User: {user}")
    c.drawString(50, 630, f"Repo: {repo}")
    c.drawString(50, 610, f"Languages: {','.join(languages)}")
    top = 400
    for image_file in image_files:
        c.drawImage(image_file, 50, top, width=500, height=200)
        top -= 250
    c.save()


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

    @staticmethod
    def get_commit_log_command(repo_path, username):
        if username:
            return f'git -C {repo_path} log --pretty=format:"%ae%x01%ct%x01%H"  --author="{username}"'
        else:
            return f'git -C {repo_path} log --pretty=format:"%ae%x01%ct%x01%H" --since="36 months ago"'

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

    def process_single_repo(self, repo_path, output_path, username):
        min_months = int(self.config['modelteam.ai']['min_months'])
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(f"{output_path}/tmp-stats", exist_ok=True)
        os.makedirs(f"{output_path}/final-stats", exist_ok=True)
        user_stats_output_file_name = f"""{output_path}/tmp-stats/{repo_path.replace("/", "_")}.jsonl"""
        repo_lib_output_file_name = f"""{output_path}/tmp-stats/{repo_path.replace("/", "_")}_libs.jsonl"""
        final_output = f"""{output_path}/final-stats/{repo_path.replace("/", "_")}_user_profile.jsonl"""
        user_profiles = {}
        repo_level_data = {LIBS: {}, SKILLS: {}}
        repo_name = repo_path.split("/")[-1]
        if not os.path.exists(user_stats_output_file_name):
            self.generate_user_profiles(repo_path, user_profiles, repo_level_data, username)
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
                if not user_profiles:
                    with open(user_stats_output_file_name, "r") as f:
                        for line in f:
                            user_stats = json.loads(line)
                            user_profiles[user_stats[USER]] = user_stats[STATS]
                with open(final_output, "w") as fo:
                    for user in user_profiles:
                        user_profile = user_profiles[user]
                        user_profile[SKILLS] = {}
                        num_skills = self.extract_skills(user_profile, repo_level_data, min_months)
                        if num_skills > 0:
                            self.filter_non_public_data(user_profile)
                            self.write_user_profile_to_file(fo, repo_name, repo_path, user, user_profile)
            if not args.skip_pdf:
                self.generate_pdf_report(final_output)

    def write_user_profile_to_file(self, f, repo_name, repo_path, user, user_profile):
        f.write("{")
        f.write(f"\"version\": {json.dumps(self.config['modelteam.ai']['version'])}, ")
        f.write(f"\"{REPO_PATH}\": {json.dumps(repo_path)}, ")
        f.write(f"\"{REPO}\": {json.dumps(repo_name)}, ")
        f.write(f"\"{USER}\": {json.dumps(user)}, ")
        f.write(f"\"{STATS}\": {json.dumps(user_profile)}")
        f.write("}\n")

    def extract_skills(self, user_profile, repo_level_data, min_months):
        features = []
        if LANGS not in user_profile:
            return 0
        lang_stats = user_profile[LANGS]
        # lang, file_name, yyyy_mm, snippet, libs_added, line_count, doc_string_line_count
        for lang in lang_stats:
            if SIG_CODE_SNIPPETS not in lang_stats[lang]:
                continue
            if TIME_SERIES not in lang_stats[lang] or len(lang_stats[lang][TIME_SERIES]) < min_months:
                continue
            if SKILLS not in lang_stats[lang]:
                lang_stats[lang][SKILLS] = {}
            sig_code_snippets = lang_stats[lang][SIG_CODE_SNIPPETS]
            for yyyy_mm in sig_code_snippets.keys():
                monthly_snippets = sig_code_snippets[yyyy_mm]
                for i in range(len(monthly_snippets)):
                    snippets = monthly_snippets[i]
                    file_name = snippets[0]
                    snippet_list = snippets[1]
                    for snippet in snippet_list:
                        file_extension = get_file_extension(file_name)
                        parser = get_language_parser(file_extension, snippet, file_name,
                                                     self.keep_only_public_libraries)
                        if not parser:
                            continue
                        lines = snippet.split("\n")
                        line_count = len(lines)
                        doc_string_line_count = self.get_docstring_line_count(lines, parser)
                        libs_added = parser.get_library_names(include_all_libraries=False)
                        features.append(
                            [lang, file_name, yyyy_mm, snippet, libs_added, line_count, doc_string_line_count])
        if features:
            self.eval_models_and_update_profile(features, repo_level_data, user_profile)
        return len(features)

    def eval_models_and_update_profile(self, features, repo_level_data, user_profile):
        for model_type in MODEL_TYPES:
            models = get_model_list(self.config, model_type)
            for model_path in models:
                model_data = init_model(model_path, model_type, self.config, device)
                if model_type == C2S or model_type == LIFE_OF_PY:
                    self.eval_llm_model(model_data, features, user_profile)
                # TODO Handle I2S if we are not using I2S as label extension
        pass

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
        snippets = [feature[4] for feature in features]
        if model_data['model_type'] == LIFE_OF_PY:
            limit = LIFE_OF_PY_PREDICTION_LIMIT
        else:
            limit = SKILL_PREDICTION_LIMIT
        skill_list, score_list = eval_llm_batch_with_scores(model_data['tokenizer'], device, model_data['model'],
                                                            snippets, model_data['new_tokens'], limit)
        for i in range(len(features)):
            lang, file_name, yyyy_mm, snippet, libs_added, line_count, doc_string_line_count = features[i]
            ModelTeamGitParser.accumulate_score(user_profile, lang, yyyy_mm, score_list[i], skill_list[i],
                                                line_count, doc_string_line_count, model_data['model_tag'],
                                                model_data['model_type'] == C2S)

    def generate_pdf_report(self, profile_json):
        lang_map = get_extension_to_language_map()
        with open(profile_json, "r") as f:
            for line in f:
                user_stats = json.loads(line)
                user = user_stats[USER]
                repo = user_stats[REPO]
                user_profile = user_stats[STATS]
                if SKILLS in user_profile:
                    skill_list = user_profile[SKILLS]
                    generate_tag_cloud(skill_list, f"{output_path}/{user}_wordcloud.png")
                lang_stats = user_profile[LANGS]
                lang_list = lang_stats.keys()
                lang_names = [lang_map[lang] for lang in lang_list]
                for lang in lang_list:
                    if TIME_SERIES in lang_stats[lang]:
                        time_series = lang_stats[lang][TIME_SERIES]
                        ts_stats = {}
                        for yyyy_mm in time_series:
                            added = time_series[yyyy_mm][ADDED] if ADDED in time_series[yyyy_mm] else 0
                            deleted = time_series[yyyy_mm][DELETED] if DELETED in time_series[yyyy_mm] else 0
                            ts_stats[yyyy_mm] = [added, deleted]
                        if ts_stats:
                            generate_ts_plot(ts_stats, f"{output_path}/{user}_{lang}_ts.png")
                image_files = [f"{output_path}/{user}_wordcloud.png", f"{output_path}/{user}_{lang}_ts.png"]
                generate_pdf(output_path, user, repo, lang_names, image_files)
        pass

    @staticmethod
    def filter_non_public_data(user_profile):
        if REPO_PATH in user_profile:
            del user_profile[REPO_PATH]
        if LANGS not in user_profile:
            return
        lang_stats = user_profile[LANGS]
        for lang in lang_stats:
            if SIG_CODE_SNIPPETS in lang_stats[lang]:
                del lang_stats[lang][SIG_CODE_SNIPPETS]
            if LIBS in lang_stats[lang]:
                del lang_stats[lang][LIBS]

    # TODO: 1. Extract Comments, 2. Change to I2S model, 3. Life of Py Model 4. Store quantity and quality @ skill level
    @staticmethod
    def accumulate_score(user_profile, lang, yyyy_mm, scores, skills, code_len, doc_string_len, tag, is_skill_pred):
        for i in range(len(skills)):
            s = skills[i]
            score = scores[i]
            if is_skill_pred:
                if s not in user_profile[SKILLS]:
                    user_profile[SKILLS][s] = 0
                user_profile[SKILLS][s] += score
            if tag not in user_profile[LANGS][lang][TIME_SERIES][yyyy_mm]:
                user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag] = {}
            if s not in user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag]:
                # min, max, sum, count, code_line_count, doc_string_line_count
                user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag][s] = [score, score, 0, 0, 0, 0]
            skill_map = user_profile[LANGS][lang][TIME_SERIES][yyyy_mm][tag][s]
            skill_map[0] = max(skill_map[0], score)
            skill_map[1] = min(skill_map[1], score)
            skill_map[2] += score
            skill_map[3] += 1
            skill_map[4] += code_len
            skill_map[5] += doc_string_len

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse Git Repositories')
    parser.add_argument('--input_path', type=str, help='Path to the input folder containing git repos')
    parser.add_argument('--output_path', type=str, help='Path to the output folder')
    parser.add_argument('--config', type=str, help='Config.ini path')
    parser.add_argument('--user_email', type=str, help='User email, if present will generate stats only for that user')
    parser.add_argument('--part', type=int, help='Part number to process', default=-1)
    parser.add_argument('--skip_model_eval', default=False, help='Skip model evaluation', action='store_true')
    parser.add_argument('--skip_pdf', default=False, help='Skip PDF Report Generation', action='store_true')

    args = parser.parse_args()
    input_path = args.input_path
    output_path = args.output_path
    username = args.user_email
    config_file = args.config
    config = configparser.ConfigParser()
    config.read(config_file)
    part = args.part

    max_parallelism = 4

    if not input_path or not output_path:
        print("Invalid arguments")
        exit(1)
    if part is not None:
        if part < 0 or part > max_parallelism - 1:
            print("Invalid part")
            exit(1)
        print(f"Running part {part}")
    else:
        part = -1

    if not username:
        print("Warning: No user email provided. Will generate stats for all users\nThis will take a very long time",
              flush=True)
        if part == -1:
            print("Do you want to continue? (y/n)")
            if input().lower() != 'y':
                exit(0)

    cnt = 0
    # iterate through all the folders in base_path and use it as repo_path
    sorted_folders = sorted(os.listdir(input_path))
    git_parser = ModelTeamGitParser(config)
    # TODO: Aggregate stats from all repos for a user
    for folder in sorted_folders:
        if os.path.isdir(f"{input_path}/{folder}") and os.path.isdir(f"{input_path}/{folder}/.git"):
            print(f"Processing {folder}", flush=True)
            cnt += 1
            if part != -1:
                curr_part = int(folder.encode("utf-8").hex(), 16) % max_parallelism
                if curr_part != part:
                    continue
            repo_path = f"{input_path}/{folder}"
            run_commandline_command(f"git -C {repo_path} pull")
            git_parser.process_single_repo(repo_path, output_path, username)
        else:
            print(f"Skipping {folder}")
    print(f"Processed {cnt} out of {len(sorted_folders)}")
