# Abstract class for programming languages
import os
from abc import ABC, abstractmethod


class ProgrammingLanguage(ABC):
    public_libraries = None

    @staticmethod
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

    def __init__(self, extension, snippet, file_name, keep_only_public_libraries=True):
        self.extension = extension
        self.snippet = snippet
        self.file_name = file_name
        self.keep_only_public_libraries = keep_only_public_libraries

    @abstractmethod
    def get_import_prefix(self):
        pass

    def get_library_names(self, include_all_libraries=False):
        if include_all_libraries:
            lib_list = self.extract_imports(self.get_code_from_file(self.file_name))
        else:
            lib_list = self.extract_imports(self.snippet)
        if self.keep_only_public_libraries:
            lib_list = self.filter_non_public_libraries(lib_list)
        return lib_list

    def filter_non_public_libraries(self, libraries):
        if not ProgrammingLanguage.public_libraries:
            ProgrammingLanguage.public_libraries = ProgrammingLanguage.load_public_libraries(
                os.path.join("config", "libraries"))
        return [library for library in libraries if library in ProgrammingLanguage.public_libraries[self.extension]]

    def get_name(self):
        return self.extension

    @abstractmethod
    def extract_imports(self, lines):
        pass

    def extract_documentation(self, code_lines):
        comments = []
        inside_comment = False
        current_comment = ""

        for line in code_lines:
            line = line.strip()
            if line.startswith('/**') and line.count('*/') == 0:
                inside_comment = True
                current_comment += line[3:]
            elif line.startswith('/*') and line.count('*/') == 0:
                inside_comment = True
                current_comment += line[2:]
            elif line.startswith('//'):
                current_comment += '\n' + line[2:]
            elif line.startswith('///'):
                current_comment += '\n' + line[3:]
            elif inside_comment:
                if line.count('*/') > 0:
                    current_comment += '\n' + line[:-2]
                    comments.append(current_comment.strip())
                    current_comment = ""
                    inside_comment = False
                else:
                    if line.startswith('*'):
                        line = line[1:]
                    current_comment += '\n' + line
            else:
                if current_comment and len(current_comment) > 300:
                    comments.append(current_comment.strip())
                    current_comment = ""

        if inside_comment and current_comment and len(current_comment) > 300:
            comments.append(current_comment.strip())
        return comments

    @abstractmethod
    def get_snippet_separator(self):
        pass

    @staticmethod
    def get_code_from_file(file_name):
        with open(file_name, "r") as f:
            try:
                lines = f.readlines()
            except UnicodeDecodeError:
                return []
        return lines
