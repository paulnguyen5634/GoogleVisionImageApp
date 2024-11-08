import os
import shutil
import sys
import json
from datetime import datetime
import re


def folderfiles(folder_name):
    '''
    Looks into the path of the named folder and outputs a list of files/folder in the directory. Function
    then asks the user which file/folder is desired and return the path to that particular item.

    Return: The path to the desired file/folder
    '''

    # Goes into the directory of current python file
    cwd = os.getcwd()
    if os.path.isdir(cwd):
        ToDO_path = os.path.join(cwd, folder_name)

    folder = os.listdir(ToDO_path)

    # returns exception when folder is empty
    if len(folder) == 0:
        raise Exception('There are no files in the ToDo directory')

    folder_dict = {}
    for i in range(0, len(folder)):
        '''if folder[i][-4:] != '.pdf':
            continue'''
        folder_dict[i] = folder[i]

    # prints the dictionary in a visually appealing manner
    print(json.dumps(folder_dict, indent=4, sort_keys=True))

    # Different error handling responses for incorrect user inputs
    while True:
        try:

            user_input = int(input('Please enter number corresponding to desired folder: '))
            filename = folder_dict[user_input]
            # temp_name = str(file)

            folder_path = os.path.join(ToDO_path, filename)
            print(folder_path)
            break

        # user inputs number not on list
        except KeyError:
            print('\n')
            print('Input value is not on list, please enter valid number printed on list')
            print('\n')
            print(json.dumps(folder_dict, indent=4, sort_keys=True))
            pass

        # user inputs string
        except ValueError:
            print('\n')
            print('Input value is a string, please pass in what is on printed list!')
            print('\n')
            print(json.dumps(folder_dict, indent=4, sort_keys=True))
            pass

        except KeyboardInterrupt:
            print('Stopping Program')
            sys.exit(0)
            break
    
    return folder_path, filename

def createFolder(img_path):
    '''
    Creates folder when given an example path, doesn't make when same named folder already exists

    :param img_path: string path to desired folder location
    :return:
    '''
    try:
        if not os.path.exists(img_path):
            os.makedirs(img_path)
            print('Folder Created')
    except OSError:
        print('Error: Creating directory')

def percentage_calculator(len_pdf, increment, i):
    '''
    Iteratively prints the percentage of files done

    :param len_pdf:
    :param increment:
    :param i:
    :return:
    '''
    index = increment


    return increment

def progress_percentage(len_pdf, incr, index):
    percentage = (index / len_pdf)
    if incr == 1:
        return 'All Pages Translated'
    if (percentage-incr) > 0:
        print(f'Completed {index} pages out of {len_pdf}')
        temp = round(incr*100)
        print(f'{temp}% Done\n')
        incr += 0.05
    return incr

def tryint(s):
    """
    Return an int if possible, or `s` unchanged.
    """
    try:
        return int(s)
    except ValueError:
        return s

def alphanum_key(s):
    """
    Turn a string into a list of string and number chunks.

    alphanum_key("z23a")
    ["z", 23, "a"]

    """
    return [tryint(c) for c in re.split('([0-9]+)', s)]

def human_sort(l):
    """
    Sort a list in the way that humans expect.
    """
    l.sort(key=alphanum_key)

def start_timer():
    start_time = datetime.now()

def end_timer(start_time):
    end_time = datetime.now()
    fin_time = str(end_time - start_time)
    a = datetime.strptime(fin_time, "%H:%M:%S.%f")
    print(f'It took {a.hour} hrs, {a.minute} mins, {a.second} seconds, {a.microsecond} microseconds to finish')

def move_to_processedArchive(user_requested_path):
    # Move a file
    shutil.move(user_requested_path, 'ProcessedArchive')