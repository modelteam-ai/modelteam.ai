import datetime
import hashlib
import os
import re
import subprocess
from calendar import monthrange

from modelteam.languages.CSharpPL import CSharpPL
from modelteam.languages.CppPL import CppPL
from modelteam.languages.GoPL import GoPL
from modelteam.languages.JavaPL import JavaPL
from modelteam.languages.JavaScriptPL import JavaScriptPL
from modelteam.languages.PhpPL import PhpPL
from modelteam.languages.PythonPL import PythonPL
from modelteam.languages.RubyPL import RubyPL
from modelteam.utils.constants import UNKOWN, MIN_CHUNK_CHAR_LIMIT


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


def get_supported_languages():
    return ["python", "javascript", "typescript", "java", "csharp", "go", "golang", "c", "c++", "c/c++", "php", "ruby"]


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


def load_public_libraries(config_path):
    pub_libs = {}
    file_list = os.listdir(config_path)
    for file in file_list:
        if file.endswith(".txt"):
            with open(os.path.join(config_path, file), "r") as f:
                language = file.replace(".txt", "")
                if language not in pub_libs:
                    pub_libs[language] = set()
                lines = f.readlines()
                for line in lines:
                    pub_libs[language].add(line.split("\t")[0].strip())
    return pub_libs


def load_lib_config(path):
    files = os.listdir(path)
    prev_libs = {}
    for file in files:
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
