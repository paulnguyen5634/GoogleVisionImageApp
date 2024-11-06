'''
Merges a folder of individual pdf's into a singular pdf file

'''

from functions import human_sort, alphanum_key, tryint
import os

def mergeIMGS(path_fldr, desired_filename):
    '''

    :param path_fldr: path to the folder of individual pdfs
    :param desired_filename: string name of pdf
    :return:
    '''
    from PyPDF2 import PdfFileMerger

    merger = PdfFileMerger()
    list_of_files = os.listdir(path_fldr)
    human_sort(list_of_files)

    i=0
    for file in list_of_files:
        loc = os.path.join(path_fldr, file)
        merger.append(loc)
        i+=1
        '''if i == 5:
            break'''

    cwd = os.getcwd()
    save_location = os.path.join(cwd, 'Finished_pdf', desired_filename+'.pdf')
    merger.write(save_location)
    merger.close()
    print('Pages Merged!')