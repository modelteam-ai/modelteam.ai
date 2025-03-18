from setup_utils import get_python_bin, run_command_stream


def main():
    python_bin = get_python_bin(create_venv=False)
    git_helper = [
        python_bin, "-m", "GitHelper",
    ]
    run_command_stream(git_helper)


if __name__ == "__main__":
    main()
