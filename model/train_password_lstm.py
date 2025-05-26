#!/usr/bin/env python
# train_password_lstm.py
# ================================================================
# Пример запуска:
# python train_password_lstm.py --data merei1.csv --col -1 --epochs 20 --save_ckpt personal.pth --export_onnx personal_lstm.onnx --patterns patterns.json
# ================================================================

import argparse, os, json, random, re, pathlib, sys, subprocess 
from collections import Counter

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# ───────────────── reproducibility ───────────────────────────────
SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False
def seed_worker(wid): rng = SEED + wid; random.seed(rng); np.random.seed(rng)
g = torch.Generator(); g.manual_seed(SEED)

# ───────────────── hyper-params ──────────────────────────────────
MAX_SEQ = 50; EMB_DIM = 64; HID_DIM = 128; BATCH = 64

# ───────────────── char vocab ────────────────────────────────────
BASE_CHARS = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "!@#$%^&*()-_=+[]{}|;:,.<>?/\\"
)
char_to_idx = {c: i + 1 for i, c in enumerate(BASE_CHARS)}
char_to_idx["<PAD>"] = 0
char_to_idx["<UNK>"] = len(char_to_idx)
idx_to_char = {i: c for c, i in char_to_idx.items()}

# ───────────────── model ─────────────────────────────────────────
class PasswordLSTM(nn.Module):
    def __init__(self, vocab):
        super().__init__()
        self.embedding = nn.Embedding(vocab, EMB_DIM)
        self.lstm      = nn.LSTM(EMB_DIM, HID_DIM, num_layers=2, batch_first=True)
        self.fc        = nn.Linear(HID_DIM, vocab)

    def forward(self, x):                       # x: [B,L]
        emb, _ = self.lstm(self.embedding(x))   # [B,L,H]
        return self.fc(emb)                     # [B,L,V]

# ───────────────── helpers ───────────────────────────────────────
def count_passwords(pwds): return dict(Counter(pwds))

def to_tensor(passwords):
    X, Y, M = [], [], []
    for p in passwords:
        seq = [char_to_idx.get(c, char_to_idx['<UNK>']) for c in p][:MAX_SEQ]
        ln  = len(seq)
        pad = [0]*(MAX_SEQ-ln)
        X.append(seq + pad)
        # цель — тот же сдвиг + PAD
        Y.append(seq[1:] + [char_to_idx['<PAD>']] + pad) if ln < MAX_SEQ \
            else Y.append(seq[1:] + [char_to_idx['<PAD>']])
        M.append([1]*ln + pad)                  # mask
    return (torch.tensor(X), torch.tensor(Y), torch.tensor(M))

def load_passwords(path: pathlib.Path, col: int):
    if path.suffix == '.txt':
        pw = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        return pw, count_passwords(pw)
    if path.suffix == '.csv':
        df = pd.read_csv(path, header=0)
        pw = df.iloc[:, col].astype(str).tolist()
        return pw, count_passwords(pw)
    if path.suffix == '.json':
        js = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(js, list):
            pw = [row.get('password', '') for row in js]
            return pw, count_passwords(pw)
    raise ValueError('Неизвестный формат файла паролей')

def train(model, data, epochs):
    X, Y, M = data
    loader  = DataLoader(TensorDataset(X, Y, M), batch_size=BATCH,
                         shuffle=True, worker_init_fn=seed_worker, generator=g)
    opt = optim.AdamW(model.parameters(), lr=3e-4)
    ce  = nn.CrossEntropyLoss(reduction='none')

    for ep in range(epochs):
        tot, tok = 0.0, 0
        for xb, yb, mb in loader:
            opt.zero_grad(set_to_none=True)
            out  = model(xb)                    # [B,L,V]
            loss = ce(out.permute(0,2,1), yb)   # [B,L]
            loss = (loss*mb).sum() / mb.sum()   # ignore PAD tokens
            loss.backward(); opt.step()
            tot += loss.item()*mb.sum().item(); tok += mb.sum().item()
        print(f'Epoch {ep+1}: ppl={np.exp(tot/tok):.2f}')

def analyze(pws):
    masks,numbers,words,mut,zigzag = {},{},{},{},0
    m_map = {"0":"o","1":"i","@":"a","$":"s","3":"e","5":"s","7":"t"}
    def mask(p): return ''.join(
        'X' if c.isalpha() else 'D' if c.isdigit() else
        'S' if re.match(r'[!@#$%^&*()\-_=+]', c) else '_' for c in p)

    for p in pws:
        masks[mask(p)] = masks.get(mask(p),0)+1
        for d in set(filter(str.isdigit,p)):
            numbers[d] = numbers.get(d,0)+1
        for L in range(3,8):
            for i in range(len(p)-L+1):
                words[p[i:i+L]] = words.get(p[i:i+L],0)+1
        if ''.join(m_map.get(c,c) for c in p) != p:
            mut[p] = mut.get(p,0)+1
        if any(c.isupper() for c in p) and any(c.islower() for c in p):
            zigzag += 1
    return dict(masks=masks,numbers=numbers,words=words,zigzag=zigzag)


# ───────────────── CLI ───────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data")          # путь к csv/txt/json
    ap.add_argument("--col", type=int, default=-1)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--load_ckpt")
    ap.add_argument("--save_ckpt")
    ap.add_argument("--export_onnx")
    ap.add_argument("--patterns")
    args = ap.parse_args()

    model = PasswordLSTM(len(char_to_idx))

    # Загрузка чекпоинта (если есть)
    if args.load_ckpt and os.path.exists(args.load_ckpt):
        ckpt = torch.load(args.load_ckpt, map_location='cpu')
        model.load_state_dict(ckpt["model_state_dict"])
        print(f'✔ loaded checkpoint {args.load_ckpt}')

    # ─── Обучение и генерация паттернов ───
    if args.data:
        passwords, pw_count = load_passwords(pathlib.Path(args.data), args.col)
        train(model, to_tensor(passwords), args.epochs)

        if args.patterns:
            pat = analyze(passwords)
            pat['password_counts'] = pw_count

            # Записываем patterns.json в UTF-8
            with open(args.patterns, 'w', encoding='utf-8') as f:
                json.dump(pat, f, indent=2, ensure_ascii=False)
            print(f'✔ patterns + counts → {args.patterns}')

    # ─── Сохранение чекпоинта ───
    if args.save_ckpt:
        torch.save({'model_state_dict': model.state_dict()}, args.save_ckpt)
        print(f'✔ checkpoint → {args.save_ckpt}')

    # ─── Экспорт в ONNX и char-map ───
    if args.export_onnx:
        # Убедимся, что onnx установлен (опционально)
        try:
            import onnx  # noqa: F401
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "onnx"])
            print("✅ onnx установлен")

        dummy = torch.randint(1, len(char_to_idx), (1, MAX_SEQ))
        torch.onnx.export(
            model, dummy, args.export_onnx,
            input_names=['input'], output_names=['output'],
            dynamic_axes={'input': {1: 'seq'}, 'output': {1: 'seq'}},
            opset_version=17
        )

        # Записываем char_to_idx.json в UTF-8
        json_path = pathlib.Path(args.export_onnx).with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(char_to_idx, f, indent=2, ensure_ascii=False)
        print(f'✔ ONNX  → {args.export_onnx}')
        print(f'✔ char-map → {json_path}')

if __name__ == "__main__":
    if len(sys.argv)==1: print("Запусти с --help, чтобы увидеть опции.")
    else: main()
