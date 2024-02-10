from .ProgrammingLanguage import ProgrammingLanguage


class GoPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "import "

    def get_snippet_seperator(self):
        return "}\n\n"

    def get_code_quality(self):
        pass

    def get_code_lifetime(self):
        pass

    def extract_imports(self, lines):
        import_lines = []
        in_import_block = False
        import_block = []
        for line in lines:
            if line.startswith("import ") or in_import_block:
                if "(" in line:
                    in_import_block = True
                if not in_import_block:
                    import_lines.append(line)
                if ")" in line:
                    in_import_block = False
                    if import_block:
                        import_lines.append(" ".join(import_block))
                        import_block = []
                else:
                    import_block.append(line)
        imports = []
        for line in import_lines:
            lib_only = line.replace("(", "").replace(")", "").replace('"', "").replace(
                "import", "").replace("\n", "").replace(";", "").replace(
                ",", "").replace("\t", "").split(" ")
            if lib_only:
                for lib in lib_only:
                    if lib:
                        imports.append(lib)
        return imports
