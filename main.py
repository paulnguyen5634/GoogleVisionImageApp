from merge_images import mergeIMGS
from functions import createFolder, folderfiles, move_to_processedArchive
from format_images import convert_pdf_to_image, convert_pdf_to_image_and_back, format_images_and_merge_to_pdf
import os

def main():
    cwd = os.getcwd()
    queueFldr = 'ProcessingQueue'
    path_to_imagefldr = os.path.join(cwd, queueFldr)

    def merge_images_action():
        user_requested_path, filename = folderfiles(queueFldr)
        print("Merging Images...")
        mergeIMGS(user_requested_path, filename)
        move_to_processedArchive(user_requested_path)

    def format_images_action():
        user_requested_path, filename = folderfiles(queueFldr)
        output_pdf_path = f'transformed/Formatted/{filename}_formatted.pdf'

        # If the file is a pdf, split the pdf -> format -> merge back
        if filename[-4:] == '.pdf':
            filename = filename[:-4]
            print("Formatting Images...")
            convert_pdf_to_image_and_back(user_requested_path, output_pdf_path)
            move_to_processedArchive(user_requested_path)
            return

        print("Formatting Images...")
        format_images_and_merge_to_pdf(user_requested_path, output_pdf_path)
        move_to_processedArchive(user_requested_path)
        return
    
    def exit_action():
        print("Exiting the app. Goodbye!")
        exit()  # Exits the program
    


    actions = {
        '0': exit_action,
        '1': merge_images_action,
        '2': format_images_action,
        # Add additional actions here as needed, such as:
        # '3': translate_images_action,
        # '4': split_pdf_action,
    }

    while True:
        try:
            print("\nPDF Manipulation App")
            print("1. Merge Images")
            print("2. Format PDF Images")
            print("3. Translate Images")
            print("4. Split PDF")
            print("0. Exit")

            user_action = input("Choose an action: ")

            # Execute the chosen action or handle invalid choice
            action = actions.get(user_action)
            if action:
                action()
            else:
                print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\nOperation interrupted. Exiting the app. Goodbye!")
            break

if __name__ == "__main__":
    main()
