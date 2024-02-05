import argparse
from configparser import ConfigParser

import torch
from peft import PeftConfig, PeftModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


def init_model(peft_model_id):
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    config = PeftConfig.from_pretrained(peft_model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(config.base_model_name_or_path)
    model = PeftModel.from_pretrained(model, peft_model_id)
    with torch.no_grad():
        inputs = tokenizer(code, return_tensors="pt", padding=True, truncation=True, max_length=400).to(device)
        model.generation_config.length_penalty = 0.0
        outputs = model.generate(**inputs)
        results = [tokenizer.decode(output, skip_special_tokens=True) for output in outputs['sequences']]
        for res in results:
            print(res)


arg_parser = argparse.ArgumentParser(description="Download models")
arg_parser.add_argument("--config", type=str, help="config file")
args = arg_parser.parse_args()
model_team_config = ConfigParser()
model_team_config.read(args.config)
base_model = model_team_config.get("base_model", "name")
c2s_model = model_team_config.get("c2s", "name")
device = "cpu"  # for GPU usage or "cpu" for CPU usage

code = """
def hello():
    print("Hello! Welcome to Model Team!, We appreciate your contribution to your team!")
    return 0
"""
init_model(c2s_model)
