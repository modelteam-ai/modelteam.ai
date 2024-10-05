import datetime
import gzip
import hashlib
import os
import pickle
import random
import re
import subprocess
from calendar import monthrange
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import try_to_load_from_cache
from peft import PeftConfig, PeftModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from .constants import UNKOWN, MIN_CHUNK_CHAR_LIMIT, SKILL_PREDICTION_LIMIT, LIFE_OF_PY_BUCKETS, C2S, LIFE_OF_PY, MLC, \
    I2S, LANGS, TIME_SERIES, SKILLS
from .languages.CSharpPL import CSharpPL
from .languages.CppPL import CppPL
from .languages.GoPL import GoPL
from .languages.JavaPL import JavaPL
from .languages.JavaScriptPL import JavaScriptPL
from .languages.PhpPL import PhpPL
from .languages.PythonPL import PythonPL
from .languages.RubyPL import RubyPL


def get_edit_distance(s1, s2):
    m, n = len(s1), len(s2)

    # Create a table to store the edit distances
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize the table
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    # Fill in the table using dynamic programming
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1

    return dp[m][n]


def get_file_extension(file_path):
    base_name, ext = os.path.splitext(file_path)
    # remove all non alphanumeric characters
    ext = re.sub('[^0-9a-zA-Z]+', '', ext)
    if not ext:
        ext = UNKOWN
    return ext


def check_for_unsafe_command(command):
    cmd_parts = command.split(";")
    cmd_parts.extend(command.split("&&"))
    cmd_parts.extend(command.split("||"))
    cmd_parts.extend(command.split("|"))
    cmd_parts.extend(command.split("&"))
    for cmd in cmd_parts:
        cmd = cmd.strip()
        if not cmd.startswith("git "):
            raise Exception(f"Unsafe command {command} found")


def run_commandline_command(command):
    try:
        check_for_unsafe_command(command)
        result = subprocess.check_output(command, shell=True, universal_newlines=True)
        # TODO: Handle empty results
        return result
    except Exception as e:
        print(f"Error running command: {command} with error {e}", flush=True)
        return None


def timestamp_to_yyyy_mm(ts):
    date_object = datetime.datetime.fromtimestamp(ts)
    yyyy_mm = date_object.year * 100 + date_object.month
    return yyyy_mm


def get_num_days_in_month(yyyy_mm):
    year, month = yyyy_mm.split("-")
    return monthrange(int(year), int(month))[1]


def get_num_chars_changed(git_diff):
    # Check if the change is just a reformat
    lines = git_diff.strip().split('\n')
    added = []
    deleted = []
    for line in lines:
        if line.startswith('+'):
            added.append(line[1:])
        if line.startswith('-'):
            deleted.append(line[1:])
    added_clean = "".join(added).replace("\n", "").replace("\t", "").replace(" ", "")
    deleted_clean = "".join(deleted).replace("\n", "").replace("\t", "").replace(" ", "")
    return get_edit_distance(added_clean, deleted_clean)


def get_supported_extensions():
    return ["py", "js", "ts", "jsx", "tsx", "java", "cs", "go", "cpp", "c", "h", "php", "rb"]


def get_extension_to_language_map():
    return {
        "py": "Python",
        "js": "Javascript",
        "ts": "Typescript",
        "jsx": "Javascript",
        "tsx": "Typescript",
        "java": "Java",
        "cs": "C#",
        "go": "go",
        "cpp": "C++",
        "c": "C",
        "h": "C/C++",
        "php": "PHP",
        "rb": "Ruby"
    }


def get_supported_languages():
    return ["python", "javascript", "typescript", "java", "csharp", "go", "golang", "c", "c++", "c/c++", "php", "ruby",
            "c#"]


# TODO: Supported languages are as follows: c, c++, c-sharp, go, java, javascript, php, python, ruby.
def get_language_parser(file_extension, file_diff_content, filename, keep_only_public_libraries):
    if "go" == file_extension:
        return GoPL(file_extension, file_diff_content, filename, keep_only_public_libraries)
    elif "py" == file_extension:
        return PythonPL("py", file_diff_content, filename, keep_only_public_libraries)
    elif "js" == file_extension or "jsx" == file_extension or "ts" == file_extension or "tsx" == file_extension:
        return JavaScriptPL(file_extension, file_diff_content, filename, keep_only_public_libraries)
    elif "java" == file_extension:
        return JavaPL(file_extension, file_diff_content, filename, keep_only_public_libraries)
    elif "cpp" == file_extension or "c" == file_extension or "h" == file_extension:
        return CppPL(file_extension, file_diff_content, filename, keep_only_public_libraries)
    elif "php" == file_extension:
        return PhpPL(file_extension, file_diff_content, filename, keep_only_public_libraries)
    elif "rb" == file_extension:
        return RubyPL(file_extension, file_diff_content, filename, keep_only_public_libraries)
    elif "cs" == file_extension:
        return CSharpPL(file_extension, file_diff_content, filename, keep_only_public_libraries)
    else:
        return None


# Splitting based on training data. Ideally we can split for each language
def get_expert_from_file_name(file_name):
    extension = get_file_extension(file_name)
    if extension == "py":
        return "python"
    elif extension == "js" or extension == "ts" or extension == "jsx" or extension == "tsx":
        return "javascript"
    elif extension == "java" or extension == "cs":
        return "java_or_csharp"
    elif extension == "go":
        return "go"
    else:
        return "others"


def get_team_mates_key(u1, u2):
    if u1 < u2:
        return f"{u1}:{u2}"
    else:
        return f"{u2}:{u1}"


def anonymize(input_string):
    num_chars = len(input_string)
    max_show_percent = 0.35
    if len(input_string) <= 1:
        return "?"
    if len(input_string) <= 4:
        return input_string[0] + "?" * (len(input_string) - 1)
    first_char = input_string[0]
    last_char = input_string[-1]
    num_chars_to_show = int((num_chars - 2) * max_show_percent)
    output = first_char
    if num_chars_to_show > 0:
        for i in range(1, len(input_string) - 1):
            if random.random() < 0.5 or num_chars_to_show == 0:
                output += "?"
            else:
                output += input_string[i]
                num_chars_to_show -= 1
    output += last_char
    return output


def sha256_hash(input_string):
    sha256_hash = hashlib.sha256(input_string.encode()).hexdigest()
    return sha256_hash


def consistent_hash_code(input_string):
    sha256_hash = hashlib.sha256(input_string.encode()).hexdigest()
    return int(sha256_hash[-15:], 16)


def get_salted_hash(string):
    salt = os.urandom(32)
    return hashlib.sha256(string.encode() + salt).hexdigest()


def is_test(id_str, test_ratio=20):
    """
    Given a id, return True if the id is in the test set using consistent hashing
    :param id_str:
    :param test_ratio:
    :return:
    """
    return consistent_hash_code(id_str) % 100 < test_ratio


# TODO: Try overlapping chunks
def break_code_snippets_to_chunks(file_name, code, chunk_char_limit, sep=None):
    file_ext = get_file_extension(file_name)
    parser = get_language_parser(file_ext, code, file_name, True)
    if not parser:
        print(f"Unknown language {file_ext} for file {file_name}", flush=True)
        return []
    output = []
    if not sep:
        sep = parser.get_snippet_seperator()
    if len(code) > chunk_char_limit:
        snippet_parts = code.split(sep)
        str_so_far = ""
        for s in snippet_parts:
            if len(s) > chunk_char_limit:
                # Break big chunks using new line and just take the first chunk
                if sep != "\n":
                    chunks = break_code_snippets_to_chunks(file_name, s, chunk_char_limit, "\n")
                    if chunks:
                        output.append(chunks[0])
                continue
            elif len(str_so_far) + len(s) > chunk_char_limit:
                if str_so_far:
                    if len(str_so_far) > MIN_CHUNK_CHAR_LIMIT:
                        # ignore very small snippets
                        output.append(str_so_far.strip())
                    str_so_far = ""
            str_so_far += s + sep
        if str_so_far:
            if len(str_so_far) > MIN_CHUNK_CHAR_LIMIT:
                # ignore very small snippets
                output.append(str_so_far.strip())
        return output
    else:
        return [code]


def load_lib_config(path):
    files = os.listdir(path)
    prev_libs = {}
    for file in files:
        if not file.endswith(".txt"):
            continue
        with open(os.path.join(path, file), "r") as f:
            lines = f.readlines()
            language = file.split(".")[0]
            for line in lines:
                if not line.strip():
                    continue
                if language not in prev_libs:
                    prev_libs[language] = {}
                    prev_libs[language]["next_id"] = 1
                    prev_libs[language]["libs"] = {}
                parts = line.split("\t")
                id = int(parts[1].strip())
                prev_libs[language]["libs"][parts[0].strip()] = id
                if id >= prev_libs[language]["next_id"]:
                    prev_libs[language]["next_id"] = id + 1
    return prev_libs


def load_file_to_set(file_name):
    """
    Load the file to a set. Can handle both compressed and uncompressed files
    :param file_name:
    :return:
    """
    if file_name.endswith(".gz"):
        with gzip.open(file_name, "rt") as f:
            return set(f.read().splitlines())
    else:
        with open(file_name, "r") as f:
            return set(f.read().splitlines())


def load_file_to_list(file_name):
    """
    Load the file to a list. Can handle both compressed and uncompressed files
    :param file_name:
    :return:
    """
    if file_name.endswith(".gz"):
        with gzip.open(file_name, "rt") as f:
            return f.read().splitlines()
    else:
        with open(file_name, "r") as f:
            return f.read().splitlines()


def convert_list_to_index(lst, do_sort=True):
    """
    Sort a list and return a dictionary with the index of each item
    :param lst:
    :param do_sort: If True, sort the list before creating the index
    :return:
    """
    index = {}
    if do_sort:
        lst = sorted(lst)
    for i, item in enumerate(lst):
        index[item] = i
    return index, lst


def get_only_ones(arr, names):
    """
    Given an array of scores, return only the names with score > 0
    :param arr:
    :param names:
    :return:
    """
    output = []
    for i in range(len(arr)):
        if arr[i] > 0:
            output.append(names[i])
    return ",".join(output)


def get_multi_label_classification_scores(arr, index, names):
    output = []
    scores = []
    score_map = {}
    for i in range(len(arr)):
        if arr[i][index][1] > 0:
            score_map[names[i]] = arr[i][index][1]
    count = 0
    for k in sorted(score_map, key=score_map.get, reverse=True):
        output.append(k)
        scores.append(float(score_map[k]))
        count += 1
        if count == SKILL_PREDICTION_LIMIT:
            break
    return output, scores


def softmax(x):
    exp_x = np.exp(x)
    return exp_x / np.sum(exp_x, axis=0).tolist()


def eval_llm_batch_with_scores_old(tokenizer, device, model, codes, new_tokens, limit=SKILL_PREDICTION_LIMIT):
    skill_list = []
    next_best_prob_list = []
    soft_max_list = []
    for code in codes:
        with torch.no_grad():
            input_tokens = tokenizer(code, return_tensors="pt", padding=True, truncation=True, max_length=400).to(
                device)
            output = model.generate(**input_tokens, max_new_tokens=2, return_dict_in_generate=True, output_scores=True,
                                    no_repeat_ngram_size=3, do_sample=False, renormalize_logits=True)
            score_map = {}
            soft_max_map = {}
            new_token_scores = []
            words = []
            for i in new_tokens:
                word = tokenizer.decode(i)
                score_map[word] = output.scores[1][0][i].item()
                new_token_scores.append(score_map[word])
                words.append(word)
            soft_max_scores = softmax(new_token_scores)
            for w, s in zip(words, soft_max_scores):
                soft_max_map[w] = s
            tmp_results = []
            tmp_scores = []
            tmp_orig_scores = []
            top_n = sorted(score_map, key=score_map.get, reverse=True)[:limit]
            next_best_pr = next_best_prob(soft_max_map, top_n)
            for word in top_n:
                tmp_results.append(word)
                tmp_scores.append(next_best_pr[word])
                tmp_orig_scores.append(soft_max_map[word])
            skill_list.append(tmp_results)
            next_best_prob_list.append(tmp_scores)
            soft_max_list.append(tmp_orig_scores)
    return skill_list, next_best_prob_list, soft_max_list


def eval_llm_batch_with_scores(tokenizer, device, model, codes, new_tokens, limit=SKILL_PREDICTION_LIMIT):
    skill_list = []
    next_best_prob_list = []
    soft_max_list = []
    with torch.no_grad():
        input_tokens = tokenizer(codes, return_tensors="pt", padding=True, truncation=True, max_length=400).to(
            device)
        output = model.generate(**input_tokens, max_new_tokens=2, return_dict_in_generate=True, output_scores=True,
                                no_repeat_ngram_size=3, do_sample=False, renormalize_logits=True)
    for i in range(len(codes)):
        score_map = {}
        soft_max_map = {}
        new_token_scores = []
        words = []
        for j in new_tokens:
            word = tokenizer.decode(j)
            score_map[word] = output.scores[1][i][j].item()
            new_token_scores.append(score_map[word])
            words.append(word)
        soft_max_scores = softmax(new_token_scores)
        for w, s in zip(words, soft_max_scores):
            soft_max_map[w] = s
        tmp_results = []
        tmp_scores = []
        tmp_orig_scores = []
        top_n = sorted(score_map, key=score_map.get, reverse=True)[:limit]
        next_best_pr = next_best_prob(soft_max_map, top_n)
        for word in top_n:
            tmp_results.append(word)
            tmp_scores.append(next_best_pr[word])
            tmp_orig_scores.append(soft_max_map[word])
        skill_list.append(tmp_results)
        next_best_prob_list.append(tmp_scores)
        soft_max_list.append(tmp_orig_scores)
    return skill_list, next_best_prob_list, soft_max_list


def next_best_prob(word_probabilities, top_words):
    processed_words = set()
    next_best_words_probabilities = {}
    for word in top_words:
        if not next_best_words_probabilities:
            # The first word is the best word
            next_best_words_probabilities[word] = word_probabilities[word]
        else:
            total_prob = sum(word_probabilities[w] for w in word_probabilities.keys() if w not in processed_words)
            next_best_words_probabilities[word] = word_probabilities[word] / total_prob
        processed_words.add(word)
    return next_best_words_probabilities


def get_tokenizer_with_new_tokens_and_update_model(checkpoint, skills_file, model):
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    new_words = load_file_to_list(skills_file)
    print(f"Adding {len(new_words)} new words to tokenizer", flush=True)
    vocabulary = tokenizer.get_vocab().keys()
    for word in new_words:
        if word not in vocabulary:
            tokenizer.add_tokens(word)
    model.resize_token_embeddings(len(tokenizer))
    vocabulary = tokenizer.get_vocab()
    new_token_ids = set()
    for word in new_words:
        if word in vocabulary:
            new_token_ids.add(vocabulary.get(word))
    return tokenizer, new_token_ids


def get_life_of_py_tokenizer_with_new_tokens_and_update_model(checkpoint, model):
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    vocabulary = tokenizer.get_vocab().keys()
    for word in LIFE_OF_PY_BUCKETS:
        if word not in vocabulary:
            tokenizer.add_tokens(word)
    model.resize_token_embeddings(len(tokenizer))
    vocabulary = tokenizer.get_vocab()
    new_token_ids = set()
    for word in LIFE_OF_PY_BUCKETS:
        if word in vocabulary:
            new_token_ids.add(vocabulary.get(word))
    return tokenizer, new_token_ids


def get_life_of_py_bucket(change):
    if change < 30:
        return LIFE_OF_PY_BUCKETS[0]
    else:
        return LIFE_OF_PY_BUCKETS[1]
    # bucket = LIFE_OF_PY_BUCKETS[change // 20]
    # return bucket


def is_documentation(input_string):
    # Count the number of spaces in the input string
    num_spaces = input_string.count(' ')
    num_lines = input_string.count('\n')
    if num_spaces >= num_lines * 5:
        return True
    else:
        return False


def normalize_docstring(comment):
    if 'license' in comment or 'License' in comment or 'LICENSE' in comment:
        return None
    if not is_documentation(comment):
        return None
    comment = comment.replace("\t", " ")
    comment = comment.replace("\r", " ")
    lines = comment.split("\n")
    filtered_lines = []
    keywords_to_skip = ["author ", "param "]
    for line in lines:
        if line.startswith("http") or line.startswith("www"):
            continue
        if any(keyword in line for keyword in keywords_to_skip):
            continue
        filtered_lines.append(line)
    return filtered_lines


def get_model_list(config, config_key):
    model_list = []
    if config_key not in config:
        return model_list
    mc = config[config_key]
    model_list.append(mc["path"])
    if "alpha.path" in mc:
        model_list.append(mc["alpha.path"])
    if "beta.path" in mc:
        model_list.append(mc["beta.path"])
    return model_list


def get_hf_cache_path_if_present(model_name):
    if os.path.isdir(model_name):
        return model_name
    file_list = ['config.json', 'adapter_config.json', 'adapter_model.safetensors', 'pytorch_model.bin',
                 'model.safetensors']
    for file in file_list:
        filepath = try_to_load_from_cache(model_name, file)
        if isinstance(filepath, str):
            return Path(filepath.replace(file, ''))
    return model_name


def init_model(model_path, model_type, config, device):
    base_llm = get_hf_cache_path_if_present(config["base_llm_model"]["path"])
    model_data = {"model_type": model_type, "model_tag": f"{model_type}::{model_path}"}
    if model_type == C2S or model_type == LIFE_OF_PY or model_type == I2S:
        model_path = get_hf_cache_path_if_present(model_path)
        print("Loading model", model_path, "of type", model_type, "with base model", base_llm, flush=True)
        skill_list = config["modelteam.ai"]["skill_list"]
        peft_config = PeftConfig.from_pretrained(model_path)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            get_hf_cache_path_if_present(peft_config.base_model_name_or_path)).to(device)
        if model_type == LIFE_OF_PY:
            tokenizer, new_tokens = get_life_of_py_tokenizer_with_new_tokens_and_update_model(base_llm, model)
        else:
            tokenizer, new_tokens = get_tokenizer_with_new_tokens_and_update_model(base_llm, skill_list, model)
        model = PeftModel.from_pretrained(model, model_path).to(device)
        model.eval()
        model_data["model"] = model
        model_data["tokenizer"] = tokenizer
        model_data["new_tokens"] = new_tokens
    elif model_type == MLC:
        with gzip.open(os.path.join(model_path, "model.pkl.gz"), "rb") as f:
            model = pickle.load(f)
            model_data["model"] = model
            model.eval()
        libs = load_file_to_list(os.path.join(model_path, "lib_list.txt.gz"))
        lib_index, lib_names = convert_list_to_index(libs, do_sort=False)
        model_data["lib_index"] = lib_index
        skills = load_file_to_list(os.path.join(model_path, "skill_list.txt.gz"))
        skill_index, skill_names = convert_list_to_index(skills, do_sort=False)
        model_data["skill_names"] = skill_names
    return model_data
    pass


def get_repo_user_key(repo, user):
    return f"{repo}::{user}"


def load_repo_user_list(file_name):
    ignore_users = set()
    if file_name:
        with open(file_name, "r") as f:
            for line in f:
                parts = line.strip().split("\t")
                ignore_users.add(get_repo_user_key(parts[0], parts[1]))
    return ignore_users


def filter_skills(user_profile, min_scores, manual_edits=set()):
    if not user_profile:
        return
    lang_stats = user_profile[LANGS]
    all_skills = set()
    all_good_skills = set()
    for lang in lang_stats.keys():
        monthly_stats = lang_stats[lang][TIME_SERIES]
        for month in monthly_stats.keys():
            for model in monthly_stats[month].keys():
                model_type = model.split("::")[0]
                if model_type not in [C2S, I2S, LIFE_OF_PY]:
                    continue
                min_score_to_filter = min_scores.get(model_type, 0)
                model_stats = monthly_stats[month][model]
                skills = list(model_stats.keys())
                for skill in skills:
                    all_skills.add(skill)
                    # All skills should be in changes, so setting default to TOP_SECRET, so it will be removed
                    max_monthly_score = model_stats[skill][0]
                    if max_monthly_score <= min_score_to_filter:
                        del model_stats[skill]
                    elif model_type != LIFE_OF_PY and (skill not in user_profile[SKILLS] or skill in manual_edits):
                        # Ignore skills that are not present in user profile (No C2S) or top secret skills
                        del model_stats[skill]
                    elif model_type == C2S:
                        # Ignore skills that are not present in C2S model results
                        all_good_skills.add(skill)
    # Remove skills that are not present in any month
    for skill in all_skills:
        if skill in user_profile[SKILLS]:
            if skill in manual_edits or skill not in all_good_skills:
                del user_profile[SKILLS][skill]
