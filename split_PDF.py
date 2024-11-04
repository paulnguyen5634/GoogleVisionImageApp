from pdf2image import convert_from_path
import os
import shutil
import requests
from google.cloud import vision
import textwrap
from PIL import Image, ImageDraw, ImageFont
import math
from deep_translator import GoogleTranslator, single_detection
import time
from functions import createFolder, folderfiles, human_sort, alphanum_key, tryint
import fitz
import cv2
from datetime import datetime
from tqdm import tqdm
# Paths
font_path = r'font\CC Wild Words Roman.ttf'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'keys\linear-enigma-328214-c41ea53b04ad.json'

def convert_pdf_to_image(fic, filename, folder_name):
    '''
    Splits a pdf into individual images

    :param fic: string path to the pdf to be split
    :param filename: name of file that will be split
    :param folder_name: name of folder in which images will be saved
    :return:
    '''
    print("\nSplitting PDF...")
    start_time = datetime.now()
    if fic.endswith('pdf'):
        doc = fitz.open(fic)
        for page in tqdm(doc):
            pixmap = page.get_pixmap()

            if pixmap.width < 2880:
                zoom = 2880 / pixmap.width
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
            elif pixmap.width > 2880:
                zoom = 2880 / pixmap.width
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
            else:
                pix = page.get_pixmap()

            pix.save(f"{folder_name}/{filename}_{page.number}.png")

        print('PDF has been converted')
    elif fic.endswith('mp4'):
        cam = cv2.VideoCapture(fic)
        currentframe = 0
        os.makedirs(filename, exist_ok=True)

        while True:
            ret, frame = cam.read()
            if ret:
                name = f'./{filename}/{currentframe}.png'
                print('Creating...' + name)
                cv2.imwrite(name, frame)
                currentframe += 1
            else:
                break

        cam.release()
        cv2.destroyAllWindows()

    end_time = datetime.now()
    fin_time = str(end_time - start_time)
    elapsed = datetime.strptime(fin_time, "%H:%M:%S.%f")
    print(f'It took {elapsed.hour} hrs, {elapsed.minute} mins, {elapsed.second} seconds to finish')

cwd = os.getcwd()
queueFldr = 'ProcessingQueue'
path_to_imagefldr = os.path.join(cwd, queueFldr)

# Path to item to be transformed
user_requested_path, filename = folderfiles(queueFldr)

pdf_name = "Ling Xue's Old Friend 1.pdf"
filename_only = filename[:-4]
print(filename)

# Create a folder where the images that are transformed will be saved
folder_path = f'transformed/Split/{filename_only}'

os.makedirs(folder_path, exist_ok=True)

convert_pdf_to_image(f"{path_to_imagefldr}/{filename}", filename_only, folder_path)




