import argparse
import configparser
import gzip
import json
import os
import pickle
import random
import re

import torch
from peft import PeftConfig, PeftModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from utils.constants import ADDED, DELETED, TIME_SERIES, LANGS, LIBS, COMMITS, START_TIME, \
    IMPORTS_ADDED, END_TIME, IMPORTS_IN_FILE, MIN_LINES_ADDED, SIGNIFICANT_CONTRIBUTION, REFORMAT_CHAR_LIMIT, \
    SIGNIFICANT_CONTRIBUTION_CHAR_LIMIT, TOO_BIG_TO_ANALYZE_LIMIT, TOO_BIG_TO_ANALYZE, \
    SIGNIFICANT_CONTRIBUTION_LINE_LIMIT, MAX_DIFF_SIZE, STATS, USER, REPO, REPO_PATH, SCORES, SIG_CODE_SNIPPETS, SKILLS
from utils.utils import get_file_extension, run_commandline_command, timestamp_to_yyyy_mm, \
    get_num_chars_changed, get_language_parser, convert_list_to_index, \
    get_multi_label_classification_scores, eval_llm_batch_with_scores, load_file_to_list, load_file_to_set

TRAIN_FLAG = False
ONE_MONTH = 30 * 24 * 60 * 60
ONE_WEEK = 7 * 24 * 60 * 60
THREE_MONTH = 3 * 30 * 24 * 60 * 60

debug = False
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
os.environ["TOKENIZERS_PARALLELISM"] = "false"


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
            print("WARNING: Getting commits for all users. This will take a long time. For ModelTeam.AI Use.",
                  flush=True)
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
                has_sig_contrib = self.process_sig_contrib(commit_hash, curr_user, file_diff_content, file_extension,
                                                           file_name, labels, repo_path, user_commit_stats, yyyy_mm)
                if has_sig_contrib:
                    if file_name in labels[LIBS]:
                        self.aggregate_library_helper(IMPORTS_IN_FILE, user_commit_stats, file_extension,
                                                      labels[LIBS][file_name], yyyy_mm)
                    library_names = parser.get_library_names(include_all_libraries=False)
                    if library_names:
                        self.aggregate_library_helper(IMPORTS_ADDED, user_commit_stats, file_extension, library_names,
                                                      yyyy_mm)

    def process_sig_contrib(self, commit_hash, curr_user, file_diff_content, file_extension, file_name, labels,
                            repo_path, commits, yyyy_mm):
        snippets = self.get_newly_added_snippets(file_diff_content)
        if snippets:
            if file_extension not in commits[LANGS]:
                commits[LANGS][file_extension] = {}
            if LIBS not in commits[LANGS][file_extension]:
                commits[LANGS][file_extension][SIG_CODE_SNIPPETS] = {}
            if yyyy_mm not in commits[LANGS][file_extension][SIG_CODE_SNIPPETS]:
                commits[LANGS][file_extension][SIG_CODE_SNIPPETS][yyyy_mm] = []
            commits[LANGS][file_extension][SIG_CODE_SNIPPETS][yyyy_mm].extend(snippets)
            return True
        return False

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
        os.makedirs(f"{output_path}/tmp-stats", exist_ok=True)
        os.makedirs(f"{output_path}/final-stats", exist_ok=True)
        user_stats_output_file_name = f"""{output_path}/tmp-stats/{repo_path.replace("/", "_")}.jsonl"""
        filtered_user_stats_output_file_name = f"""{output_path}/final-stats/{repo_path.replace("/", "_")}.jsonl"""
        user_profiles = {}
        repo_level_data = {LIBS: {}}
        repo_name = repo_path.split("/")[-1]
        if not os.path.exists(user_stats_output_file_name):
            self.generate_user_profiles(repo_path, user_profiles, repo_level_data, username)
            # TODO: Email validation, A/B profiles
            if user_profiles and username in user_profiles:
                # Store hash to file
                with open(user_stats_output_file_name, "w") as f:
                    for user in user_profiles:
                        self.write_user_profile_to_file(f, repo_name, repo_path, user, user_profiles[user])
        if not args.skip_model_eval and os.path.exists(user_stats_output_file_name) and not os.path.exists(
                filtered_user_stats_output_file_name):
            with open(user_stats_output_file_name, "r") as f:
                with open(filtered_user_stats_output_file_name, "w") as fo:
                    for line in f:
                        user_stats = json.loads(line)
                        user = user_stats[USER]
                        user_profile = user_stats[STATS]
                        user_profile[SKILLS] = {}
                        self.eval_models(user_profile)
                        self.generate_pdf_report(user_profile)
                        self.filter_non_public_data(user_profile)
                        self.write_user_profile_to_file(fo, repo_name, repo_path, user, user_profile)

    @staticmethod
    def write_user_profile_to_file(f, repo_name, repo_path, user, user_profile):
        f.write("{")
        f.write(f"\"{REPO_PATH}\": {json.dumps(repo_path)}, ")
        f.write(f"\"{REPO}\": {json.dumps(repo_name)}, ")
        f.write(f"\"{USER}\": {json.dumps(user)}, ")
        f.write(f"\"{STATS}\": {json.dumps(user_profile)}")
        f.write("}\n")

    def get_model_list(self, config_key):
        model_list = []
        mc = self.config[config_key]
        model_list.append(mc["path"])
        if "alpha.path" in mc:
            model_list.append(mc["alpha.path"])
        if "beta.path" in mc:
            model_list.append(mc["beta.path"])
        return model_list

    def eval_models(self, user_profile):
        i2s_models = self.get_model_list("i2s")
        for model_path in i2s_models:
            self.eval_i2s_model(model_path, user_profile)
        c2s_models = self.get_model_list("c2s")
        skill_names = load_file_to_set(self.config["c2s"]["skill_list"])
        for model_path in c2s_models:
            self.eval_c2s_model(model_path, user_profile, skill_names)

    def eval_i2s_model(self, model_path, user_profile):
        libs = load_file_to_list(f"{model_path}/lib_list.txt.gz")
        lib_index, lib_names = convert_list_to_index(libs, do_sort=False)
        skills = load_file_to_list(f"{model_path}/skill_list.txt.gz")
        skill_index, skill_names = convert_list_to_index(skills, do_sort=False)
        with gzip.open(f"{model_path}/model.pkl.gz", "rb") as f:
            multi_output_classifier = pickle.load(f)
        if not multi_output_classifier:
            print("Error loading model", flush=True)
            return
        if LANGS not in user_profile:
            return
        lang_stats = user_profile[LANGS]
        for lang in lang_stats:
            if lang not in lib_index or LIBS not in lang_stats[lang]:
                continue
            if SKILLS not in lang_stats[lang]:
                lang_stats[lang][SKILLS] = {}
            imp_added_monthly_features = self.gen_monthly_lib_features(lang_stats[lang], lib_index, IMPORTS_ADDED)
            imp_in_file_monthly_features = self.gen_monthly_lib_features(lang_stats[lang], lib_index, IMPORTS_IN_FILE)
            imp_added_monthly_skills = self.i2s_predict_skills(multi_output_classifier, imp_added_monthly_features,
                                                               skill_names, user_profile)
            self.add_to_skills(lang_stats[lang][SKILLS], imp_added_monthly_skills, model_path, IMPORTS_ADDED)
            imp_in_file_monthly_skills = self.i2s_predict_skills(multi_output_classifier, imp_in_file_monthly_features,
                                                                 skill_names, user_profile)
            self.add_to_skills(lang_stats[lang][SKILLS], imp_in_file_monthly_skills, model_path, IMPORTS_IN_FILE)

    @staticmethod
    def gen_monthly_lib_features(lang_stats, lib_index, import_type):
        monthly_features = {}
        if import_type not in lang_stats[LIBS]:
            return monthly_features
        for month in lang_stats[LIBS][import_type]:
            for lib_list in lang_stats[LIBS][import_type][month]:
                if month not in monthly_features:
                    monthly_features[month] = []
                x = [0] * len(lib_index)
                for lib in lib_list:
                    x[lib_index[lib]] = 1
                monthly_features[month].append(x)
        return monthly_features

    def eval_c2s_model(self, peft_model_id, user_profile, skill_names):
        if LANGS not in user_profile:
            return
        lang_stats = user_profile[LANGS]
        tokenizer = AutoTokenizer.from_pretrained(self.config["base_llm_model"]["path"])
        peft_config = PeftConfig.from_pretrained(peft_model_id)
        model = AutoModelForSeq2SeqLM.from_pretrained(peft_config.base_model_name_or_path).to(device)
        model = PeftModel.from_pretrained(model, peft_model_id).to(device)
        model.eval()

        for lang in lang_stats:
            if SIG_CODE_SNIPPETS not in lang_stats[lang]:
                continue
            if SKILLS not in lang_stats[lang]:
                lang_stats[lang][SKILLS] = {}
            sig_code_snippets = lang_stats[lang][SIG_CODE_SNIPPETS]
            c2s_monthly_skills = self.c2s_predict_skills(tokenizer, model, sig_code_snippets, skill_names, user_profile)
            self.add_to_skills(lang_stats[lang][SKILLS], c2s_monthly_skills, peft_model_id, SIG_CODE_SNIPPETS)

    def generate_pdf_report(self, user_profile):
        pass

    @staticmethod
    def filter_non_public_data(user_profile):
        if LANGS not in user_profile:
            return
        lang_stats = user_profile[LANGS]
        for lang in lang_stats:
            if SIG_CODE_SNIPPETS in lang_stats[lang]:
                del lang_stats[lang][SIG_CODE_SNIPPETS]
            if LIBS in lang_stats[lang]:
                del lang_stats[lang][LIBS]

    @staticmethod
    def i2s_predict_skills(multi_output_classifier, monthly_features, skill_names, user_profile):
        output = {}
        for month in monthly_features:
            features = monthly_features[month]
            predictions = multi_output_classifier.predict_proba(features)
            skill_map = {}
            for i in range(len(features)):
                skills, scores = get_multi_label_classification_scores(predictions, i, skill_names)
                ModelTeamGitParser.accumulate_score(user_profile, scores, skill_map, skills)
            output[month] = skill_map
        return output

    @staticmethod
    def accumulate_score(user_profile, scores, skill_map, skills, code_len=1):
        for i in range(len(skills)):
            s = skills[i]
            score = scores[i]
            if s not in skill_map:
                # max, min, sum, count
                skill_map[s] = [0, 1, 0, 0]
            skill_map[s][0] = max(skill_map[s][0], score)
            skill_map[s][1] = min(skill_map[s][1], score)
            skill_map[s][2] += score
            skill_map[s][3] += code_len
            if s not in user_profile[SKILLS]:
                user_profile[SKILLS][s] = 1
            else:
                user_profile[SKILLS][s] += 1

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

    @staticmethod
    def c2s_predict_skills(tokenizer, model, monthly_features, skill_names, user_profile):
        output = {}
        for month in monthly_features:
            features = monthly_features[month]
            skill_list, score_list = eval_llm_batch_with_scores(tokenizer, device, model, features, skill_names)
            skill_map = {}
            for i in range(len(features)):
                ModelTeamGitParser.accumulate_score(user_profile, score_list[i], skill_map, skill_list[i],
                                                    len(features[i].split("\n")))
            output[month] = skill_map
        return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse Git Repositories')
    parser.add_argument('--input_path', type=str, help='Path to the input folder containing git repos')
    parser.add_argument('--output_path', type=str, help='Path to the output folder')
    parser.add_argument('--config', type=str, help='Config.ini path')
    parser.add_argument('--user_email', type=str, help='User email, if present will generate stats only for that user')
    parser.add_argument('--skip_model_eval', default=False, help='Skip model evaluation', action='store_true')

    args = parser.parse_args()
    input_path = args.input_path
    output_path = args.output_path
    username = args.user_email
    config_file = args.config
    config = configparser.ConfigParser()
    config.read(config_file)

    if not input_path or not output_path or not username:
        print("Invalid arguments")
        exit(1)

    cnt = 0
    # iterate through all the folders in base_path and use it as repo_path
    sorted_folders = sorted(os.listdir(input_path))
    git_parser = ModelTeamGitParser(config)
    for folder in sorted_folders:
        if os.path.isdir(f"{input_path}/{folder}") and os.path.isdir(f"{input_path}/{folder}/.git"):
            print(f"Processing {folder}", flush=True)
            repo_path = f"{input_path}/{folder}"
            run_commandline_command(f"git -C {repo_path} pull")
            git_parser.process_single_repo(repo_path, output_path, username)
        else:
            print(f"Skipping {folder}")
    print(f"Processed {cnt} out of {len(sorted_folders)}")
