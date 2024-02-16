import datetime
import gzip
import hashlib
import os
import re
import subprocess
from calendar import monthrange

import numpy as np
import torch
from transformers import AutoTokenizer

from .constants import UNKOWN, MIN_CHUNK_CHAR_LIMIT, SKILL_PREDICTION_LIMIT
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


def run_commandline_command(command):
    try:
        result = subprocess.check_output(command, shell=True, universal_newlines=True)
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


def consistent_hash_code(input_string):
    sha256_hash = hashlib.sha256(input_string.encode()).hexdigest()
    return int(sha256_hash, 16)


def is_test(user, test_ratio=20):
    """
    Given a user, return True if the user is in the test set using consistent hashing
    :param user:
    :param test_ratio:
    :return:
    """
    return consistent_hash_code(user) % 100 < test_ratio


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
                if language not in prev_libs:
                    prev_libs[language] = {}
                    prev_libs[language]["next_id"] = 1
                    prev_libs[language]["libs"] = {}
                parts = line.split("\t")
                id = int(parts[1])
                prev_libs[language]["libs"][parts[0]] = id
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


def eval_llm_batch_with_scores(tokenizer, device, model, codes, new_tokens):
    skill_list = []
    score_list = []
    seq_score_list = []
    for code in codes:
        with torch.no_grad():
            input_tokens = tokenizer(code, return_tensors="pt", padding=True, truncation=True, max_length=400).to(
                device)
            output = model.generate(**input_tokens, max_new_tokens=2, return_dict_in_generate=True, output_scores=True,
                                    no_repeat_ngram_size=3, do_sample=False)
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
            tmp_seq_scores = []
            top_n = sorted(score_map, key=score_map.get, reverse=True)[:SKILL_PREDICTION_LIMIT]
            next_best_pr = next_best_prob(soft_max_map, top_n)
            for word in top_n:
                tmp_results.append(word)
                tmp_scores.append(next_best_pr[word])
                tmp_seq_scores.append(soft_max_map[word])
            skill_list.append(tmp_results)
            score_list.append(tmp_scores)
            seq_score_list.append(tmp_seq_scores)
    return skill_list, score_list, seq_score_list


def next_best_prob(word_probabilities, top_words):
    processed_words = set()
    next_best_words_probabilities = {}
    for word in top_words:
        if not next_best_words_probabilities:
            # The first word is the best word
            next_best_words_probabilities[word] = word_probabilities[word]
        else:
            total_prob = sum(word_probabilities[w] for w in word_probabilities.keys() if w not in processed_words)
            next_best_words_probabilities[word] = word_probabilities[word]/total_prob
        processed_words.add(word)
    return next_best_words_probabilities


def get_tokenizer_with_new_tokens_and_update_model(checkpoint, skills_file, model):
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    new_words = load_file_to_list(skills_file)
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
