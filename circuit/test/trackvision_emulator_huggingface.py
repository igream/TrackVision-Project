import os


os.environ.setdefault("TRACKVISION_BASE_URL", "https://igream-trackvision-project.hf.space")

from trackvision_emulator import main


if __name__ == "__main__":
    main()
