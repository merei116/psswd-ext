from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

APPNAME = "Password Guardian"

# ─── Python зависимости ───
python_reqs = [
    "torch>=2.2.0",
    "pandas>=2.2",
    "numpy>=1.26",
    "rapidfuzz>=3.6",
    # "scikit-learn",
    # "matplotlib",
]

def ensure_python_packages():
    """Ставим недостающие pip-пакеты из python_reqs."""
    missing = []
    for spec in python_reqs:
        mod = spec.split("==")[0].split(">=")[0].split("<=")[0]
        if importlib.util.find_spec(mod) is None:
            missing.append(spec)
    if missing:
        print("⚙️  pip install", " ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("✅ Python-зависимости готовы!\n")


def ensure_npm():
    """Проверяем npm и завершаем, если отсутствует."""
    if shutil.which("npm") is None:
        messagebox.showerror(
            APPNAME,
            "npm не найден. Установите Node.js и повторите."
        )
        sys.exit(1)


def choose_csv() -> Path | None:
    tk.Tk().withdraw()
    path = filedialog.askopenfilename(
        title="Выберите экспорт паролей (CSV или JSON)",
        filetypes=[("CSV/JSON", "*.csv *.json")]
    )
    return Path(path) if path else None


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n> Выполняется: {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=cwd, shell=True)
    if p.returncode:
        print("❌ Ошибка:", cmd)
        messagebox.showerror(APPNAME, f"Команда {' '.join(cmd)} завершилась с ошибкой")
        sys.exit(1)
    print("✅ Успешно")


def main() -> None:
    # 1) Проверяем и ставим зависимости
    ensure_python_packages()
    ensure_npm()

    # 2) Базовая директория
    base_path = (Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS")
                 else Path(__file__).resolve().parent.parent)

    # 3) Предустановка node-зависимостей
    print("🛠  npm install…")
    run(["npm", "install"], cwd=base_path)

    # 4) Выбор CSV-файла
    messagebox.showinfo(APPNAME, "Сейчас выберите файл экспорта своих паролей.")
    csv = choose_csv()
    if not csv:
        sys.exit(0)

    # 5) Обучение модели + генерация паттернов
    model_dir = base_path / "model"
    assets = (base_path / "src" / "assets")

    print("🧠 Обучение модели + генерация паттернов…")
    run([
        "python", "train_password_lstm.py",
        "--data", str(csv),
        "--col", "-2",
        "--epochs", "6",
        "--load_ckpt", "base.pth",
        "--export_onnx", "personal_lstm.onnx",
        "--patterns", "patterns.json"
    ], cwd=model_dir)

    print("📂 Копируем результаты обучения…")
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy(model_dir / "personal_lstm.json", assets / "char_to_idx.json")
    shutil.copy(model_dir / "patterns.json",      assets / "patterns.json")

    # 6) Сборка расширения
    print("🏗  npm run build…")
    run(["npm", "run", "build"], cwd=base_path)

    # 7) Копируем путь ext_dir в буфер обмена
    ext_dir = base_path / "dist"
    path_str = str(ext_dir.resolve())
    root = tk.Tk()
    root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(path_str)
    root.update()  # сохраняем в буфер

    print("\n✅ Расширение собрано!")
    print(f"Папка расширения скопирована в буфер: {path_str}")

    messagebox.showinfo(
        APPNAME,
        f"Модель обучена и расширение собрано!\n\n"
        f"Путь расширения скопирован в буфер обмена:\n{path_str}\n\n"
        "Открыть chrome://extensions вручную для загрузки расширения."
    )

if __name__ == "__main__":
    main()
