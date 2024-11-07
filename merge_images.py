'''
Merges a folder of individual pdf's into a singular pdf file

'''

from functions import human_sort, alphanum_key, tryint
import os
from PIL import Image
from PyPDF2 import PdfFileMerger

def mergeIMGS(path_fldr, desired_filename):
    '''
    :param path_fldr: path to the folder of individual pdfs
    :param desired_filename: string name of pdf
    :return:
    '''
    
    # Get the current working directory
    cwd = os.getcwd()
    save_location = os.path.join(cwd, 'Transformed', 'Merged', desired_filename + '.pdf')

    # Sort the list of files
    list_of_files = os.listdir(path_fldr)
    human_sort(list_of_files)

    # Open images using the full path
    images = [Image.open(os.path.join(path_fldr, img_path)).convert("RGB") for img_path in list_of_files]

    # Save all images as a single PDF
    if images:
        images[0].save(save_location, save_all=True, append_images=images[1:])
        #print(f"Images merged successfully into {save_location}")
    else:
        print("No images found to merge.")

    print('Pages Merged!')

