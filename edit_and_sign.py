import argparse

from modelteam.modelteam_utils.crypto_utils import encrypt_compress_file


def edit_profile(profile_jsonl, edited_file):
    with open(profile_jsonl, "r") as f:
        with open(edited_file, "w") as f_out:
            for line in f:
                # TODO: Display in the UI and allow the user to remove skills from the profile
                f_out.write(line)
    pass


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--profile_jsonl", type=str, required=True)
    arg_parser.add_argument("--user_key", type=str, required=True)

    args = arg_parser.parse_args()
    file_name_without_extension = args.profile_jsonl.replace(".jsonl", "")
    edited_file = f"{file_name_without_extension}.edited.jsonl"
    encrypted_file = f"{file_name_without_extension}.enc.gz"
    edit_profile(args.profile_jsonl, edited_file)
    encrypt_compress_file(args.profile_jsonl, encrypted_file, args.user_key)
