"""Download required NLP models at setup time."""
import subprocess
import sys


def run(cmd: list[str]):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True)
    return result


def main():
    print("=" * 60)
    print("Downloading spaCy English model (en_core_web_sm)...")
    print("=" * 60)
    run([
        sys.executable, "-m", "pip", "install",
        "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
        "-q"
    ])

    print()
    print("=" * 60)
    print("Pre-downloading SentenceTransformer model (all-MiniLM-L6-v2)...")
    print("=" * 60)
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        _ = model.encode(["test"])
        print("SentenceTransformer model ready.")
    except Exception as e:
        print(f"Warning: SentenceTransformer download failed: {e}")
        print("It will be downloaded on first use.")

    print()
    print("NLP setup complete!")


if __name__ == "__main__":
    main()
