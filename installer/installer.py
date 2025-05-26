import os, sys, shutil, subprocess, tempfile, tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

APPNAME = "Password Guardian"

def choose_csv():
    tk.Tk().withdraw()
    path = filedialog.askopenfilename(
        title="Выберите экспорт паролей (CSV или JSON)",
        filetypes=[("CSV/JSON", "*.csv *.json")]
    )
    return Path(path) if path else None

def run(cmd, cwd=None):
    print(f"\n> Выполняется: {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=cwd, shell=True)
    if p.returncode:
        print("❌ Ошибка выполнения:", cmd)
        messagebox.showerror(APPNAME, f"Команда {' '.join(cmd)} завершилась с ошибкой")
        sys.exit(1)
    else:
        print("✅ Успешно")

def main():
    messagebox.showinfo(APPNAME, "Сейчас выберите файл экспорта своих паролей.")
    csv = choose_csv()
    if not csv:
        sys.exit(0)

    print("📁 Создаём временную рабочую папку...")
    work = Path(tempfile.mkdtemp(prefix="pg-"))
    print(f"🗂️  Временная директория: {work}")

    src = Path(sys._MEIPASS) / "extension-src"
    print("📦 Копируем расширение...")
    shutil.copytree(src, work / "ext", dirs_exist_ok=True)

    print("📦 Копируем модель...")
    model_dir = work / "model"
    shutil.copytree(Path(sys._MEIPASS) / "model", model_dir, dirs_exist_ok=True)

    print("🧠 Обучение модели + генерация паттернов...")
    run([
        "python", "train_password_lstm.py",
        "--data", str(csv),
        "--col", "-1",
        "--epochs", "6",
        "--load_ckpt", "base.pth",
        "--export_onnx", "personal_lstm.onnx",
        "--patterns", "patterns.json"
    ], cwd=model_dir)

    print("📂 Копируем результаты обучения...")
    assets = work / "ext" / "src" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy(model_dir / "personal_lstm.json", assets / "char_to_idx.json")
    shutil.copy(model_dir / "patterns.json", assets / "patterns.json")

    print("🛠️ Устанавливаем зависимости...")
    run(["npm", "install"], cwd=work / "ext")

    print("🏗️ Собираем расширение...")
    run(["npm", "run", "build"], cwd=work / "ext")

    dist = work / "ext"
    print("\n✅ Расширение собрано!")
    print(f"📂 Зайди в chrome://extensions и загрузи распакованную папку:\n→ {dist}\n")

    messagebox.showinfo(APPNAME,
        f"Модель обучена!\n\nТеперь зайди в chrome://extensions и загрузи эту папку как расширение:\n\n{dist}\n\n(Нажми «Загрузить распакованное расширение»)")

if __name__ == "__main__":
    main()
