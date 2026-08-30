import subprocess

def build_executable():

    subprocess.run([
        "pyinstaller",
        "--name=VoiceTrans",
        "--windowed",
        "--icon=assets/VoiceTrans.ico",
        "--add-data", "utils/config.ini:.",
        "--add-data", "data/replacements.txt:.",
        "--add-data", "data/technical_terms.txt:.",
        "main.py"
    ])

    print(f"Executable built successfully.")

if __name__ == "__main__":
    build_executable()
