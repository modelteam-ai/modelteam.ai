import gzip
import os
import pickle

import numpy as np
import torch
import transformers
from huggingface_hub import try_to_load_from_cache
from peft import PeftConfig, PeftModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM

from .constants import SKILL_PREDICTION_LIMIT, LIFE_OF_PY_BUCKETS, C2S, LIFE_OF_PY, I2S, MLC, MT_START, MT_END
from .utils import load_file_to_list, convert_list_to_index


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


def eval_llm_batch_with_scores(tokenizer, device, model, codes, new_tokens, limit=SKILL_PREDICTION_LIMIT,
                               is_qwen=False):
    if is_qwen:
        new_codes = []
        for prompt in codes:
            messages = [
                {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
                {"role": "user", "content": f"{MT_START}{prompt}{MT_END}"}
            ]
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            new_codes.append(text)
        codes = new_codes
    skill_list = []
    next_best_prob_list = []
    soft_max_list = []
    max_new_tokens = 2
    score_index = 1
    with torch.no_grad():
        if is_qwen:
            input_tokens = tokenizer(codes, return_tensors="pt", padding=True, truncation=True).to(device)
            max_new_tokens = 1
            score_index = 0
        else:
            input_tokens = tokenizer(codes, return_tensors="pt", padding=True, truncation=True, max_length=400).to(
                device)
        output = model.generate(**input_tokens, max_new_tokens=max_new_tokens, return_dict_in_generate=True,
                                output_scores=True, no_repeat_ngram_size=3, do_sample=False, renormalize_logits=True)
    for i in range(len(codes)):
        score_map = {}
        soft_max_map = {}
        new_token_scores = []
        words = []
        for j in new_tokens:
            word = tokenizer.decode(j)
            score_map[word] = output.scores[score_index][i][j].item()
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


def smart_tokenizer_and_embedding_resize(
        new_tokens: [],
        tokenizer: transformers.PreTrainedTokenizer,
        model: transformers.PreTrainedModel,
        modify_embedding: bool = True,
):
    """Resize tokenizer and embedding.

    Note: This is the unoptimized version that may make your embedding size not be divisible by 64.
    """
    num_new_tokens = tokenizer.add_tokens(new_tokens)
    model.resize_token_embeddings(len(tokenizer))
    if num_new_tokens > 0 and modify_embedding:
        input_embeddings = model.get_input_embeddings().weight.data
        output_embeddings = model.get_output_embeddings().weight.data

        input_embeddings_avg = input_embeddings[:-num_new_tokens].mean(dim=0, keepdim=True)
        output_embeddings_avg = output_embeddings[:-num_new_tokens].mean(dim=0, keepdim=True)

        input_embeddings[-num_new_tokens:] = input_embeddings_avg
        output_embeddings[-num_new_tokens:] = output_embeddings_avg
    vocabulary = tokenizer.get_vocab()
    new_token_ids = set()
    for word in new_tokens:
        if word in vocabulary:
            new_token_ids.add(vocabulary.get(word))
    return tokenizer, new_token_ids


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
    is_qwen = "qwen" in checkpoint.lower()
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    new_words = load_file_to_list(skills_file)
    if is_qwen:
        new_words.append(MT_START)
        new_words.append(MT_END)
        tokenizer.padding_side = 'left'
        tokenizer.pad_token_id = tokenizer.eos_token_id
    # modify embedding only for Qwen models
    tokenizer, new_token_ids = smart_tokenizer_and_embedding_resize(new_words, tokenizer, model,
                                                                    modify_embedding=is_qwen)
    return tokenizer, new_token_ids


def get_life_of_py_tokenizer_with_new_tokens_and_update_model(checkpoint, model):
    is_qwen = "qwen" in checkpoint.lower()
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    if is_qwen:
        new_tokens = LIFE_OF_PY_BUCKETS.copy()
        new_tokens.append(MT_START)
        new_tokens.append(MT_END)
        tokenizer.padding_side = 'left'
        tokenizer.pad_token_id = tokenizer.eos_token_id
    else:
        new_tokens = LIFE_OF_PY_BUCKETS
    tokenizer, new_token_ids = smart_tokenizer_and_embedding_resize(new_tokens, tokenizer, model,
                                                                    modify_embedding=is_qwen)
    return tokenizer, new_token_ids


def get_life_of_py_bucket(change):
    if change < 30:
        return LIFE_OF_PY_BUCKETS[0]
    else:
        return LIFE_OF_PY_BUCKETS[1]
    # bucket = LIFE_OF_PY_BUCKETS[change // 20]
    # return bucket


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
    file_list = ['adapter_model.safetensors', 'pytorch_model.bin', 'model.safetensors']
    for file in file_list:
        filepath = try_to_load_from_cache(model_name, file)
        if isinstance(filepath, str):
            return filepath.replace(file, '')
    return model_name


def init_model(model_path, model_type, config, device):
    model_data = {"model_type": model_type, "model_tag": f"{model_type}::{model_path}"}
    if model_type == C2S or model_type == LIFE_OF_PY or model_type == I2S:
        model_path = get_hf_cache_path_if_present(model_path)
        skill_list = config["modelteam.ai"]["skill_list"]
        peft_config = PeftConfig.from_pretrained(model_path)
        base_model_path = get_hf_cache_path_if_present(peft_config.base_model_name_or_path)
        base_llm = get_hf_cache_path_if_present(base_model_path)
        is_qwen = 'qwen' in model_path.lower() or 'qwen' in base_model_path.lower()
        if is_qwen:
            model = AutoModelForCausalLM.from_pretrained(base_model_path, torch_dtype=torch.bfloat16).to(device)
        else:
            model = AutoModelForSeq2SeqLM.from_pretrained(base_model_path).to(device)
        if model_type == LIFE_OF_PY:
            tokenizer, new_tokens = get_life_of_py_tokenizer_with_new_tokens_and_update_model(base_llm, model)
        else:
            tokenizer, new_tokens = get_tokenizer_with_new_tokens_and_update_model(base_llm, skill_list, model)
        model = PeftModel.from_pretrained(model, model_path).to(device)
        if is_qwen:
            model.generation_config.pad_token_id = tokenizer.pad_token_id
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
