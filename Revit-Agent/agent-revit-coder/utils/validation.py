import random, json

IN = "../agent-revit/data/data_GPT_Fine_Tunning/train_data_finetunning_04.jsonl"
OUT_TRAIN = "../agent-revit/data/data_GPT_Fine_Tunning/train_data_finetunning_05.jsonl"
OUT_VALID = "../agent-revit/data/data_GPT_Fine_Tunning/valid_data_02.jsonl"

lines = open(IN, encoding="utf-8").read().splitlines()
random.seed(42)
random.shuffle(lines)

n_val = int(0.1 * len(lines))   # 10% para validación
valid, train = lines[:n_val], lines[n_val:]

with open(OUT_VALID, "w", encoding="utf-8") as f:
    f.write("\n".join(valid))
with open(OUT_TRAIN, "w", encoding="utf-8") as f:
    f.write("\n".join(train))