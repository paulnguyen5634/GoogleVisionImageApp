import fitz
import cv2
from datetime import datetime
import os
from functions import createFolder, folderfiles, percentage_calculator, start_timer, end_timer, progress_percentage
from tqdm import tqdm
import fitz  # PyMuPDF
from PIL import Image
from tqdm import tqdm
from datetime import datetime
import io

def convert_pdf_to_image(fic, save_folder_path):
    '''
    Splits a pdf into individual images and formats those images to smaller dimensions

    :param fic: string path to the pdf to be split
    :param folder_name: name of folder in which images will be saved
    :return:
    '''
    print("\nSplitting PDF...\n")
    start_time = datetime.now()
    if fic.endswith('pdf'):
        # open your file
        doc = fitz.open(fic)
        # iterate through the pages of the document and create a RGB image of the page
        for page in tqdm(doc):
            dim = page.get_pixmap()

            if dim.width >= 2200:
                zoom = 1800 / (dim.width)
                # zoom = 4    # zoom factor
                mat = fitz.Matrix(zoom, zoom)
                # pix = page.getPixmap(matrix = mat, <...>)
                pix = page.get_pixmap(matrix=mat)

                pix.save(f"{save_folder_path}\%i.png" % page.number)

                #pix.save(f"{filename}\%i.png" % page.number)
            else:
                pix = page.get_pixmap()
                # Save individual images to folder of same name as pdf name
                pix.save(f"{save_folder_path}\%i.png" % page.number)
                #pix.save(f"{filename}\%i.png" % page.number)

        print('PDF has been converted')

    end_time = datetime.now()
    fin_time = str(end_time - start_time)
    a = datetime.strptime(fin_time, "%H:%M:%S.%f")
    print(f'It took {a.hour} hrs, {a.minute} mins, {a.second} seconds, {a.microsecond} microseconds to finish')

def convert_pdf_to_image_and_back(fic, output_pdf_path):
    '''
    Splits a PDF into individual images, formats those images, and converts them back into a single PDF.

    :param fic: string path to the PDF to be split
    :param output_pdf_path: string path to save the final merged PDF
    :return:
    '''
    print("\nSplitting PDF and formatting images...\n")
    start_time = datetime.now()

    images = []

    if fic.endswith('pdf'):
        # Open the PDF file
        doc = fitz.open(fic)

        # Iterate through each page of the document
        for page in tqdm(doc):
            dim = page.get_pixmap()

            # Resize the image if it's too large
            if dim.width >= 2200:
                zoom = 1600 / dim.width
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
            else:
                pix = page.get_pixmap()

            # Convert pixmap to a PIL Image
            img_data = pix.tobytes(output="png")
            img = Image.open(io.BytesIO(img_data))

            # Format the image (e.g., resize, convert to RGB)
            img = img.convert("RGB")

            # Append the image to the list for PDF conversion
            images.append(img)

        # Save the images as a single PDF
        if images:
            print("\nSaving formatted images back to PDF...\n")
            images[0].save(output_pdf_path, save_all=True, append_images=images[1:])

        print("PDF has been successfully converted back to a single PDF.")

    end_time = datetime.now()
    fin_time = str(end_time - start_time)
    a = datetime.strptime(fin_time, "%H:%M:%S.%f")
    print(f'It took {a.hour} hrs, {a.minute} mins, {a.second} seconds, {a.microsecond} microseconds to finish')

def format_images_and_merge_to_pdf(image_folder_path, output_pdf_path):
    '''
    Formats all images in a folder and merges them into a single PDF.

    :param image_folder_path: string path to the folder containing images
    :param output_pdf_path: string path to save the final merged PDF
    :return:
    '''
    print("\nFormatting images and merging into a single PDF...\n")
    start_time = datetime.now()

    images = []
    valid_extensions = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')

    # List all image files in the folder
    image_files = sorted([f for f in os.listdir(image_folder_path) if f.lower().endswith(valid_extensions)])

    if not image_files:
        print("No valid image files found in the folder.")
        return

    # Iterate through each image file
    for image_file in tqdm(image_files):
        image_path = os.path.join(image_folder_path, image_file)

        try:
            # Open the image file
            img = Image.open(image_path)

            # Convert to RGB and resize the image
            img = img.convert("RGB")

            # Append the formatted image to the list
            images.append(img)

        except Exception as e:
            print(f"Error processing image {image_file}: {e}")

    # Save the images as a single PDF
    if images:
        print("\nSaving formatted images back to PDF...\n")
        images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
        print("Images have been successfully merged into a single PDF.")

    end_time = datetime.now()
    fin_time = str(end_time - start_time)
    a = datetime.strptime(fin_time, "%H:%M:%S.%f")
    print(f'It took {a.hour} hrs, {a.minute} mins, {a.second} seconds, {a.microsecond} microseconds to finish')