"""Download and validate OCR models once into the shared Docker volume."""

from app.modules.ai.service import reader

if __name__ == "__main__":
    reader()
    print("OCR CPU models ready (en/vi by default)")
