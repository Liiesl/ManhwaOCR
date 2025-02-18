# ManhwaOCR
an app that lets you MTL your manhwa with ease. designed with simplicity at its core .

# Installation Guide

This guide will help you set up and run the Manhwa OCR Tool on your system. Follow the steps below to install all necessary dependencies and execute the application.

## Prerequisites

Before proceeding, ensure that you have the following installed on your system:

- **Python 3.8 or higher**: You can download it from [python.org](https://www.python.org/downloads/).
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
cd manhwa-ocr-tool
```

## Step 2: Install Required Dependencies

The Manhwa OCR Tool relies on several Python libraries. Install them one by one using `pip`. Below is the list of required dependencies:

### Core Libraries

1. **PyQt5** - For creating the graphical user interface.
   ```bash
   pip install PyQt5
   ```

2. **Pillow** - For image processing.
   ```bash
   pip install Pillow
   ```

3. **EasyOCR** - For performing OCR tasks.
   please refer to [easyocr's github](https://github.com/JaidedAI/EasyOCR?tab=readme-ov-file#installation) (IMPORTANT!! also check the note especially for windows)

4. **NumPy** - For numerical operations.
   ```bash
   pip install numpy
   ```

5. **qtawesome** - For icons in the GUI.
   ```bash
   pip install qtawesome
   ```

6. **PyYAML** - For configuration file handling (optional, if needed).
   ```bash
   pip install pyyaml
   ```

### Additional Libraries

7. **json** - Standard library, no installation needed.
8. **os**, **sys**, **gc**, **ast** - Standard libraries, no installation needed.

After installing all the above packages, verify their installation by importing them in a Python shell:

```python
import PyQt5
import PIL
import easyocr
import numpy
import qtawesome
```

If no errors occur, the libraries are installed correctly.

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

## Usage Instructions

1. **Open Folder**: Click the "Open Folder" button to select a directory containing images.
2. **Process OCR**: Click the "Process OCR" button to start OCR processing on the selected images.
3. **Import Translation**: Import translations from an MD file using the "Import Translation" button.
4. **Export OCR**: Export OCR results to a Markdown file using the "Export OCR" button.
5. **Apply Translation**: Apply translations to the images using the "Apply Translation" button.

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
