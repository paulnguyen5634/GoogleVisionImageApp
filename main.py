#from FinishedTranslator import translate_pdf
#from split_PDF import split_pdf
from merge_images import mergeIMGS
from functions import createFolder, folderfiles, move_to_processedArchive
import os

def main():

    cwd = os.getcwd()
    queueFldr = 'ProcessingQueue'
    path_to_imagefldr = os.path.join(cwd, queueFldr)

    actions = {
        '1': mergeIMGS,
    }

    print("PDF Manipulation App")
    print("1. Merge Images")
    print("2. Translate Images")
    print("3. Split PDF")

    user_action = input("Choose an action: ")

    

    if user_action == '1':
        # Path to item to be transformed
        user_requested_path, filename = folderfiles(queueFldr)
        print("Merging Images")
        mergeIMGS(user_requested_path, filename)
        move_to_processedArchive(user_requested_path)
    #elif choice == '2':
        #split_pdf()
    else:
        print("Invalid choice. Please try again.")
    
    

    '''
    
    choice = input("Choose an action (1, 2, or 3): ")

    # Dictionary to map choices to functions
    
    '''

if __name__ == "__main__":
    main()