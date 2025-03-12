import argparse
import gc
from configparser import ConfigParser

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from modelteam_utils.constants import MODEL_TYPES, C2S, LIFE_OF_PY, I2S
from modelteam_utils.ai_utils import eval_llm_batch_with_scores, get_model_list, init_model

arg_parser = argparse.ArgumentParser(description="Download models")
arg_parser.add_argument("--config", type=str, help="config file")
args = arg_parser.parse_args()
model_team_config = ConfigParser()
model_team_config.read(args.config)
device = "cpu"  # for GPU usage or "cpu" for CPU usage
code = """
def hello_world():
    print("Hello World! Thanks for using modelteam!")
"""
print("Downloading Base Model https://huggingface.co/Salesforce/codet5p-770m", flush=True)
checkpoint = "Salesforce/codet5p-770m"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint).to(device)

inputs = tokenizer.encode(code, return_tensors="pt").to(device)
outputs = model.generate(inputs, max_length=10)

for model_type in MODEL_TYPES:
    models = get_model_list(model_team_config, model_type)
    for model_path in models:
        print(f"Downloading https://huggingface.co/{model_path}", flush=True)
        model_data = init_model(model_path, model_type, model_team_config, device)
        if model_type == C2S or model_type == LIFE_OF_PY or model_type == I2S:
            skill_list, score_list, sm_score_list = eval_llm_batch_with_scores(model_data['tokenizer'], device,
                                                                               model_data['model'], [code],
                                                                               model_data['new_tokens'], 3)
        del model_data
        gc.collect()
