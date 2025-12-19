import argparse
import logging
import os
from datetime import datetime
from models import load_model, generate_response, Args as GenArgs
import json
from prompts import *
import re
from tqdm import tqdm


class ModelWrapper:
    def __init__(self, model, tokenizer, args):
        self.args = args
        self.model_name = self.args.model_name
        self.model, self.tokenizer = load_local_model(self.args)
    
    def generate_response(self, messages):
        gen_args = GenArgs(
            model_name=self.args.model_name,
            model_id=self.args.model_id,
            cache_dir=self.args.cache_dir,
            max_new_tokens=self.args.max_new_tokens,
            do_sample=self.args.do_sample,
            top_p=self.args.top_p,
            top_k=self.args.top_k,
            temperature=self.args.temperature
        )
        return generate_response(self.model, self.tokenizer, messages, gen_args)


class SelectModules:
    def __init__(self, llm, problem, logger, args):
        self.llm = llm
        self.problem = problem
        self.logger = logger
        self.args = args
        self.max_retries = 3

        self.rag_module = f"1. {reasoning_modules[0]}"  # open-ended 처리를 위한 모듈
        self.open_ended = False 
        self.selected_modules = None
        

    def extract_tags(self, response, step='select'):
        pattern = r"<SELECT/>\s*(\[.*?\])\s*</SELECT>"
        step_name = "Step 1. SELECT"

        matches = re.findall(pattern, response, re.S)
        if not matches:
            arr = re.findall(r"\[(?:\s*\d+\s*,?)+\s*\]", response)
            if arr:
                matches = [arr[0]]
        if not matches:
            raise ValueError(f"No valid block found")

        block = matches[0].strip()

        try:
            ids = json.loads(block)
            if not isinstance(ids, list) or not all(isinstance(x, int) for x in ids):
                raise ValueError
            if ids and max(ids) > len(reasoning_modules):
                raise ValueError
            return [f"{i}. " + reasoning_modules[i-1] for i in sorted(set(ids))]
        except Exception:
            raise ValueError(f"{step_name} - Invalid JSON array: {block}")


    def return_response(self, prompt):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                response, _ = self.llm.generate_response(prompt)
                return response
            except Exception:
                retry_count += 1
                print(f"retry {retry_count}")
        raise RuntimeError(f"failed after retries")

    
    def __call__(self):
        prompt = select_prompt.replace("{problem}", self.problem)
        prompt = prompt.replace("{reasoning_modules}", "\n".join([f"{i+1}. {m}" for i, m in enumerate(reasoning_modules)]))
        try:
            response = self.return_response(prompt)
            self.selected_modules = self.extract_tags(response)
        except Exception as e:
            self.selected_modules = response
            print(e)



def setup_logging(log_file, log_level):
    logger = logging.getLogger("__name__")
    logger.setLevel(getattr(logging, log_level))
    handler = logging.FileHandler(log_file)
    handler.setLevel(getattr(logging, log_level))
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


model_version = {
    "gpt-oss-20b": "openai/gpt-oss-20b",
    "qwen3-8b": "Qwen/Qwen3-8B",
    "qwen3-14b": "Qwen/Qwen3-14B",
    "llama-3b": "meta-llama/Llama-3.2-3B-Instruct",
    "llama-8b": "meta-llama/Llama-3.1-8B-Instruct",
    "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3"
}


def main():
    parser = argparse.ArgumentParser(description="Run Self-Discover")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save_interval", type=int, default=1)
    parser.add_argument("--model_name", type=str, default="gpt-oss-20b")
    parser.add_argument("--dataset_name", type=str, default="HotpotQA", help="T4D, MATH500, StrategyQA")
    parser.add_argument("--do_sample", type=bool, default=False)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top_p", type=float, default=0.95)
    parser.add_argument("--top_k", type=int, default=50)
    parser.add_argument("--max_new_tokens", type=int, default=1024)
    parser.add_argument("--log_dir", type=str, default="logs")
    parser.add_argument("--log_level", type=str, default="INFO")
    parser.add_argument("--output_dir", type=str, default="output")
    parser.add_argument("--cache_dir", type=str, default="cache")
    parser.add_argument("--data_dir", type=str, default="data")
    parser.add_argument("--force_eager_attn", action="store_true")
    parser.add_argument("--disable_sdp_flash", action="store_true")


    args = parser.parse_args()
    
    log_dir = os.path.join(args.log_dir, args.dataset_name)
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{args.model_name}_{timestamp}.log")

    logger = setup_logging(log_file, args.log_level)
    logger = logging.getLogger(__name__)
    logger.info(f"Selecting Open/Closed-ended prompt modules using {args.model_name} for {args.dataset_name}")
    for arg, value in vars(args).items():
        logger.info(f"{arg}: {value}")
    logger.info(f"Logs saved to {os.path.abspath(log_file)}")


    output_dir = os.path.join(args.output_dir, args.dataset_name)
    output_path = os.path.join(output_dir, f"{args.model_name}.json")
    os.makedirs(output_dir, exist_ok=True)

    args.model_id = model_version[args.model_name]

    model = ModelWrapper(args)

    data_dir = os.path.join(args.data_dir, args.dataset_name)
    data_path = os.path.join(data_dir, f"{args.dataset_name}.json")
    with open(data_path, 'r') as f:
        dataset = json.load(f)


    res = []
    for data in tqdm(dataset):
        runner = SelectModules(model, data['question'], logger, args)
        runner()
        tmp = {
            "id": data['id'],
            "question": data['question'],
            "answer": data.get('answer'),
            "selected_modules": runner.selected_modules,
            "open_ended": runner.open_ended,
        }
        res.append(tmp)

        with open(output_path, 'w') as f:
            json.dump(res, f, indent=4)
            logger.info(f"Results saved to {os.path.abspath(output_path)}")

    with open(output_path, 'w') as f:
        json.dump(res, f, indent=4)
        logger.info(f"All results saved to {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()


