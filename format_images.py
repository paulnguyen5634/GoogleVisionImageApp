import fitz
import cv2
from datetime import datetime
import os
from functions import createFolder, folderfiles, percentage_calculator, start_timer, end_timer, progress_percentage
from tqdm import tqdm

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

            if dim.width < 2880:
                zoom = 1600 / (dim.width)
                # zoom = 4    # zoom factor
                mat = fitz.Matrix(zoom, zoom)
                # pix = page.getPixmap(matrix = mat, <...>)
                pix = page.get_pixmap(matrix=mat)

                pix.save(f"{save_folder_path}\%i.png" % page.number)

                #pix.save(f"{filename}\%i.png" % page.number)
            elif dim.width > 2880:
                zoom = 1600 / (dim.width)  
                # zoom = 4    # zoom factor
                mat = fitz.Matrix(zoom, zoom)
                # pix = page.getPixmap(matrix = mat, <...>)
                pix = page.get_pixmap(matrix=mat)

                pix.save(f"{save_folder_path}\%i.png" % page.number)
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
