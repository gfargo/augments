from setuptools import setup, find_packages

setup(
    name="augments",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-dotenv~=0.21.0",
        "openai>=1.0.0",
        "yt-dlp>=2023.10.13",
        "pyperclip>=1.8.2",
        "pytest>=7.4.0",
        "gTTS>=2.3.2",
    ],
)