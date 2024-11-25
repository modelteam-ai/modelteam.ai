import datetime
import gzip
import hashlib
import math
import os
import random
import re
import subprocess
from calendar import monthrange

from .constants import UNKOWN, MIN_CHUNK_CHAR_LIMIT, C2S, LIFE_OF_PY, I2S, LANGS, TIME_SERIES, SKILLS
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


def anonymize(input_string, max_show_percent=0.5):
    if not input_string:
        return input_string
    num_chars = len(input_string)

    if num_chars <= 2:
        return input_string[0] + "*"
    if num_chars <= 6:
        return input_string[:2] + "*" * (num_chars - 2)

    first_chars = input_string[:2]
    last_chars = input_string[-2:]
    num_chars_to_show = max(0, math.ceil(num_chars * max_show_percent) - 4)
    chance = num_chars_to_show / (num_chars - 4) if num_chars > 4 else 0

    output = first_chars
    for i in range(2, num_chars - 2):
        if random.random() < chance and num_chars_to_show > 0:
            output += input_string[i]
            num_chars_to_show -= 1
        else:
            output += "*"
    output += last_chars
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
                    elif model_type != LIFE_OF_PY and (skill not in user_profile[SKILLS]
                                                       or skill in manual_edits):
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


def yyyy_mm_to_quarter(yyyymm):
    yyyy = yyyymm // 100
    mm = yyyymm % 100
    return str(yyyy) + "Q" + str((mm - 1) // 3 + 1)


def yyyy_mm_to_half(yyyymm):
    yyyy = yyyymm // 100
    mm = yyyymm % 100
    return str(yyyy) + "H" + str((mm - 1) // 6 + 1)
