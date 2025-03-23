# ManhwaOCR
an app that lets you MTL your manhwa with ease. designed with simplicity at its core .

## Table of Contents
- [Woekflow](#workflow)
  - [Create Project](#create-project)
  - [Start OCR](#start-the-ocr)
  - [Translation](#configure-and-translate-with-gemini-api-free)
- [Installation](#installation-guide)
  - [Prerequisites](#prerequisites)
  - [Step-by-Step Guide](#step-by-step-guide)
- [Troubleshooting](#troubleshooting)

---

# Workflow

## Create Project

https://github.com/user-attachments/assets/29a9de14-5e11-4292-8943-4ad793abb5d3

## Start the OCR

https://github.com/user-attachments/assets/432fa7f7-9172-43b7-97c7-28e8d66b6758

## Configure and Translate with Gemini API (Free!)

yes, gemini api is free. if you still haven't made one, what are you waiting for!?!

https://github.com/user-attachments/assets/2b255b1e-a036-4b98-b22c-5d72854a65c3



---

# Installation Guide

This guide will help you set up and run the Manhwa OCR Tool on your system. Follow the steps below to install all necessary dependencies and execute the application.

## Prerequisites

Before proceeding, ensure that you have the following installed on your system:

- **Python 3.9 or higher**: You can download it from [python.org](https://www.python.org/downloads/).
- **pip**: Python's package installer (usually included with Python).

Verify your Python and pip installations by running the following commands in your terminal:

```bash
python --version
pip --version
```

If these commands return version numbers, you're good to proceed.

---

## Step 1: Clone the Repository

Clone this repository to your local machine using the following command:

```bash
git clone https://github.com/Liiesl/ManhwaOCR.git
cd ManhwaOCR
```

## Step 2: Install Required Dependencies

Install core dependencies with a single command:
```bash
pip install PyQt5 qtawesome easyocr numpy Pillow google-generativeai
```

**For EasyOCR** (requires system dependencies):
```bash
pip install easyocr
```
⚠️ **IMPORTANT**: Follow [EasyOCR's GitHub instructions](https://github.com/JaidedAI/EasyOCR#installation) closely (especially windows user, please read their note).

---

Verify Installation
Run this command to check all core dependencies:

```bash
python -c "import PyQt5, Pillow, easyocr, numpy, qtawesome, google-generativeai; print('All dependencies installed successfully!')"
```
If no errors appear, you're ready to proceed.
(Note: EasyOCR requires additional system dependencies - verify its functionality by processing an image)

---

## Step 3: Run the Application

Once all dependencies are installed, you can run the application using the following command:

```bash
python main.py
```

This will launch the Manhwa OCR Tool GUI. From here, you can open a folder containing images, process OCR, and apply translations as described in the tool's documentation.

---

## Troubleshooting

### 1. EasyOCR Installation Issues

If you encounter issues installing EasyOCR, ensure that you have the latest version of `pip` and `setuptools`:

```bash
pip install --upgrade pip setuptools
```

Then retry installing EasyOCR:

```bash
pip install easyocr
```

### 2. PyQt5 Installation Issues

If PyQt5 installation fails, try installing it with the following command:

```bash
pip install PyQt5==5.15.9
```

This specifies a stable version of PyQt5.

### 3. Missing Dependencies

If you encounter any "ModuleNotFoundError" during runtime, it means a required library is missing. Use the error message to identify the missing module and install it using `pip`.

---

## Notes

- Ensure that all images in the selected folder are in supported formats (e.g., PNG, JPG, JPEG).
- The tool groups and merges text regions that are close to each other to improve readability.
- OCR processing may take some time depending on the number of images and their sizes.

---

## Contributing

Feel free to contribute to this project by submitting pull requests or opening issues in the repository.

---

That's it! You should now have a fully functional Manhwa OCR Tool installed on your system. Happy translating!
