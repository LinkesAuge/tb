from setuptools import setup, find_packages

setup(
    name="scout",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "opencv-python",
        "numpy",
        "mss",
        "pywin32",
        "pyautogui",
        "pygame",
        "pytesseract"
    ]
) 