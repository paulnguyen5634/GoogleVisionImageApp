#from FinishedTranslator import translate_pdf
#from split_PDF import split_pdf
from merge_images import mergeIMGS
from functions import createFolder, folderfiles, move_to_processedArchive
from format_images import convert_pdf_to_image
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
    print("2. Format PDF Images")
    print("3. Translate Images")
    print("4. Split PDF")

    user_action = input("Choose an action: ")

    if user_action == '1':
        # Path to item to be transformed
        user_requested_path, filename = folderfiles(queueFldr)
        print("Merging Images...")
        mergeIMGS(user_requested_path, filename)
        move_to_processedArchive(user_requested_path)
    elif user_action == '2':
        user_requested_path, filename = folderfiles(queueFldr)
        print("Formatting Images...")

        folder_path = f'transformed/Formatted/{filename}_formatted'
        os.makedirs(folder_path, exist_ok=True)
        convert_pdf_to_image(user_requested_path, folder_path)
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()