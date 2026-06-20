import os
import sys
import time
import pandas as pd
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# Base config constants
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
TRAIN_DATA_PATH = "data/training/train.json"
VAL_DATA_PATH = "data/training/val.json"
OUTPUT_DIR = "models/bharatllm"
FINAL_MODEL_DIR = "models/bharatllm-final"
LOG_CSV_PATH = "models/training_log.csv"

def run_preflight_checks():
    print("Running Pre-flight Training Checks...")
    
    # 1. Verify dataset files exist and meet entry limits
    if not os.path.exists(TRAIN_DATA_PATH) or not os.path.exists(VAL_DATA_PATH):
        print(f"CRITICAL ERROR: Training split files missing. Generate datasets first.")
        sys.exit(1)
        
    try:
        import json
        with open(TRAIN_DATA_PATH, "r", encoding="utf-8") as f:
            train_len = len(json.load(f))
        with open(VAL_DATA_PATH, "r", encoding="utf-8") as f:
            val_len = len(json.load(f))
            
        print(f"Dataset Verified. Train samples: {train_len}, Val samples: {val_len}")
        if train_len < 1000 or val_len < 100:
            print("WARNING: Dataset sizes are lower than minimum recommendations (1000 train, 100 val).")
    except Exception as e:
        print(f"CRITICAL ERROR reading dataset files: {e}")
        sys.exit(1)
        
    # 2. Check for HF_TOKEN in environment variable
    if not os.getenv("HF_TOKEN"):
        print("WARNING: HF_TOKEN environment variable not set. LLaMA model downloads may fail.")
        
    # 3. Check for CUDA execution framework
    if not torch.cuda.is_available():
        print("CRITICAL ERROR: CUDA is not available. GPU is required for QLoRA fine-tuning.")
        sys.exit(1)
        
    gpu_name = torch.cuda.get_device_name(0)
    vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    print(f"GPU Found: {gpu_name} ({vram_total:.2f} GB total VRAM)")

def alpaca_prompt_formatter(sample):
    # Formats training dataset sample to Alpaca Prompt format
    instruction = sample.get("instruction", "")
    inp = sample.get("input", "")
    output = sample.get("output", "")
    
    if inp.strip():
        text = (
            "Below is an instruction related to BharatLLM Government documents. "
            "Write a response that appropriately answers the request.\n\n"
            f"### Instruction:\n{instruction}\n\n"
            f"### Input:\n{inp}\n\n"
            f"### Response:\n{output}"
        )
    else:
        text = (
            "Below is an instruction related to BharatLLM Government documents. "
            "Write a response that appropriately answers the request.\n\n"
            f"### Instruction:\n{instruction}\n\n"
            f"### Response:\n{output}"
        )
    return {"text": text}

def main():
    run_preflight_checks()
    
    # 1. MODEL SETUP
    print("Loading Base model and tokenizer...")
    # Quantization configurations
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map={"": 0},
        torch_dtype=torch.bfloat16
    )
    
    # Prepare model for quantized training
    model = prepare_model_for_kbit_training(model)
    
    # 2. LoRA CONFIGURATION
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj", "v_proj", "k_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    print("Model prepared with PEFT adapters targetting QLoRA configurations.")
    model.print_trainable_parameters()
    
    # 3. DATASETS LOADING
    dataset = load_dataset("json", data_files={"train": TRAIN_DATA_PATH, "validation": VAL_DATA_PATH})
    
    # Format templates
    formatted_dataset = dataset.map(alpaca_prompt_formatter, remove_columns=dataset["train"].column_names)
    
    # 4. TRAINING ARGUMENTS
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=50,
        save_steps=200,
        eval_steps=200,
        evaluation_strategy="steps",
        save_strategy="steps",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=3,
        report_to="none"
    )
    
    trainer = SFTTrainer(
        model=model,
        train_dataset=formatted_dataset["train"],
        eval_dataset=formatted_dataset["validation"],
        peft_config=lora_config,
        dataset_text_field="text",
        max_seq_length=2048,
        tokenizer=tokenizer,
        args=training_args
    )
    
    # 5. TRAINING RUN
    print("Starting QLoRA fine-tuning...")
    start_time = time.time()
    train_result = trainer.train()
    total_time = time.time() - start_time
    
    print(f"Training completed in {total_time/3600:.2f} hours.")
    
    # Log results
    log_history = trainer.state.log_history
    steps, train_loss, eval_loss, lrs, epochs = [], [], [], [], []
    for log in log_history:
        if "loss" in log or "eval_loss" in log:
            steps.append(log.get("step", 0))
            train_loss.append(log.get("loss", None))
            eval_loss.append(log.get("eval_loss", None))
            lrs.append(log.get("learning_rate", None))
            epochs.append(log.get("epoch", 0))
            
    df_log = pd.DataFrame({
        "step": steps,
        "train_loss": train_loss,
        "eval_loss": eval_loss,
        "learning_rate": lrs,
        "epoch": epochs
    })
    # Forward fill/backward fill missing matching logs
    df_log = df_log.bfill().ffill()
    os.makedirs(os.path.dirname(LOG_CSV_PATH), exist_ok=True)
    df_log.to_csv(LOG_CSV_PATH, index=False)
    print(f"Training log metrics saved to {LOG_CSV_PATH}")
    
    # 6. POST-TRAINING - Adapter Merging
    print("Loading base model to merge weights (CPU memory constraints may apply)...")
    # Reload model in bfloat16 (without quantization) to merge
    try:
        base_model_reload = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            return_dict=True,
            torch_dtype=torch.bfloat16,
            device_map="cpu"
        )
        
        from peft import PeftModel
        # Load best model adapter
        peft_model = PeftModel.from_pretrained(
            base_model_reload,
            os.path.join(OUTPUT_DIR, "best_checkpoint") if os.path.exists(os.path.join(OUTPUT_DIR, "best_checkpoint")) else OUTPUT_DIR
        )
        
        merged_model = peft_model.merge_and_unload()
        print(f"Merging completed. Saving final model weights to {FINAL_MODEL_DIR}...")
        merged_model.save_pretrained(FINAL_MODEL_DIR)
        tokenizer.save_pretrained(FINAL_MODEL_DIR)
        print("Final model saved successfully ✓")
    except Exception as e:
        print(f"Warning: Merging adapters failed (likely system memory out): {e}")
        print("Ensure PEFT adapters in the models folder are loaded on-the-fly during runtime.")

if __name__ == "__main__":
    main()
