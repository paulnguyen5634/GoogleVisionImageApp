'''
Merges a folder of individual pdf's into a singular pdf file

'''

from PyPDF2 import PdfMerger
from PIL import Image
import os
from functions import human_sort

def mergeIMGS(path_fldr, desired_filename):
    '''
    Merges images and PDFs from a folder into a single PDF.

    :param path_fldr: Path to the folder containing images and PDFs
    :param desired_filename: String name of the output PDF
    :return: None
    '''
    # Get current working directory and define output path
    cwd = os.getcwd()
    save_location = os.path.join(cwd, 'Transformed', 'Merged', f'{desired_filename}.pdf')

    # Sort the files naturally
    list_of_files = os.listdir(path_fldr)
    human_sort(list_of_files)

    # Initialize PdfMerger and list to track temp files
    merger = PdfMerger()
    temp_files = []

    try:
        for file in list_of_files:
            file_path = os.path.join(path_fldr, file)
            file_ext = file.lower().split('.')[-1]

            if file_ext in ['jpg', 'jpeg', 'png']:
                # Convert images to PDF format
                temp_pdf = os.path.join(path_fldr, f'{file}.temp.pdf')
                with Image.open(file_path).convert("RGB") as img:
                    img.save(temp_pdf, "PDF")
                merger.append(temp_pdf)
                temp_files.append(temp_pdf)  # Add temp file to list for later removal

            elif file_ext == 'pdf':
                # Append PDF directly
                merger.append(file_path)

        # Write final output
        if merger.pages:
            merger.write(save_location)
            print(f"Files merged successfully into {save_location}")
        else:
            print("No files found to merge.")

    finally:
        # Clean up resources
        merger.close()
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)  # Remove temp files after merger is closed

    print('Files Merged!')
