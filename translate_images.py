from pypdf import PdfReader, PdfWriter
from io import BytesIO
import fitz  # PyMuPDF
from PIL import Image
import os
import shutil
import re
import requests
from google.cloud import vision
import textwrap
from PIL import Image, ImageDraw, ImageFont
import math
from deep_translator import GoogleTranslator, single_detection
import time
from functions import createFolder, folderfiles
from deep_translator.exceptions import LanguageNotSupportedException
import nltk
# nltk.download('words')
from nltk.corpus import words
nltk_words = set(words.words())
font_path = 'font\\CC Wild Words Roman.ttf'
# Replace with your Google Cloud Vision API credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys\\linear-enigma-328214-c41ea53b04ad.json'

def detect_text(path):
    """Detects text in the given image."""
    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)
    texts = response.text_annotations 

    if texts:
        detected_text = texts[0].description
        detected_language = texts[0].locale

        if detected_language == 'zh':
            print("Detected language: Chinese")
        elif detected_language == 'ja':
            print("Detected language: Japanese")
        else:
            print(f"Detected language: {detected_language}")

    return texts

def new_detect_text(image_bytes):
    """Detects text in the given image bytes."""
    client = vision.ImageAnnotatorClient()

    # Create an Image object using the bytes content
    image = vision.Image(content=image_bytes)

    # Perform text detection
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if response.error.message:
        raise Exception(f"API Error: {response.error.message}")
    
    detected_language = None
    
    if texts:
        detected_text = texts[0].description
        detected_language = texts[0].locale

        if detected_language == 'zh':
            print("Detected language: Chinese")
        elif detected_language == 'ja':
            print("Detected language: Japanese")
        else:
            print(f"Detected language: {detected_language}")

    return texts, detected_language

def is_box_inside(outer_box, inner_box):
    """
    Checks if inner_box is inside outer_box.
    
    Parameters:
    outer_box (list): The coordinates of the outer box [x1, y1, x2, y2].
    inner_box (list): The coordinates of the inner box [x1, y1, x2, y2].

    Returns:
    bool: True if the inner_box is inside the outer_box, False otherwise.
    """
    x1_outer, y1_outer, x2_outer, y2_outer = outer_box
    x1_inner, y1_inner, x2_inner, y2_inner = inner_box

    # Check if both top-left and bottom-right corners of the inner_box are inside the outer_box
    return (x1_outer <= x1_inner <= x2_outer and
            y1_outer <= y1_inner <= y2_outer and
            x1_outer <= x2_inner <= x2_outer and
            y1_outer <= y2_inner <= y2_outer)

def find_enclosing_box(combined_boxes, given_box):
    """
    Finds which box in the list of boxes contains the given_box.

    Parameters:
    combined_boxes (list of lists): A list of bounding boxes, each represented by [x1, y1, x2, y2].
    given_box (list): The coordinates of the box to check [x1, y1, x2, y2].

    Returns:
    list: The bounding box that contains the given_box, or None if no box contains it.
    """
    for box in combined_boxes:
        if is_box_inside(box, given_box):
            return box
    return None

def add_text_in_box(image, text, box_coords, font_path, min_height_ratio=0.7, max_height_ratio=0.9):
    draw = ImageDraw.Draw(image)

    # Box coordinates (left, top, right, bottom)
    left, top, right, bottom = box_coords
    box_width = max(right - left, 1)  # Ensure width is at least 1
    box_height = bottom - top

    # Load the font, start with small size
    font_size = 10  # Starting font size
    font = ImageFont.truetype(font_path, font_size)

    # Dynamically increase font size to occupy at least 70-90% of the box height
    while True:
        # Ensure the box_width is valid before dividing
        if box_width > 0:
            wrapped_text = textwrap.fill(text, width=max(1, int(box_width / font.getlength(' '))))
        else:
            wrapped_text = textwrap.fill(text, width=1)  # Default to width of 1 if invalid

        text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Check if the text height is within the desired range
        if text_height / box_height >= min_height_ratio and text_height / box_height <= max_height_ratio:
            break
        elif text_height / box_height > max_height_ratio or font_size > 200:
            # Stop if the text exceeds max height or the font size becomes too large
            break

        # Increase font size to occupy more space in the box
        font_size += 1
        font = ImageFont.truetype(font_path, font_size)

    # Split the text into multiple lines
    lines = wrapped_text.split('\n')

    # Calculate the total height of all lines
    line_height = text_height / len(lines)
    total_text_height = line_height * len(lines)

    # Vertical centering: adjust starting y-coordinate
    y = top + (box_height - total_text_height) // 2

    # Draw each line of text centered within the box
    for line in lines:
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_width = line_bbox[2] - line_bbox[0]

        # Center each line horizontally
        x = left + (box_width - line_width) // 2
        draw.text((x, y), line, font=font, fill="black")

        # Move to the next line
        y += line_height

def is_sentence_gibberish(sentence):
    common_interjections = {"uh", "huh", "woo", "oh", "ah", '...', 'Hmm'}

    words_in_sentence = sentence.split()
    valid_words_count = sum(
        1 for word in words_in_sentence 
        if word.lower() in nltk_words or word.lower() in common_interjections
    )
    return valid_words_count < len(words_in_sentence) * 0.1  # Adjusted threshold to 50%

def split_pdf_to_png_in_memory(path):

    # Example usage
    with open(path, "rb") as f:
        pdf_bytes = f.read()

    pdf_reader = PdfReader(BytesIO(pdf_bytes))
    images = []

    for page_num in range(len(pdf_reader.pages)):
        # Split the PDF page into an in-memory PDF
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf_reader.pages[page_num])

        page_bytes = BytesIO()
        pdf_writer.write(page_bytes)
        page_bytes.seek(0)

        # Render the page to an image using PyMuPDF
        pdf_document = fitz.open(stream=page_bytes, filetype="pdf")
        page = pdf_document.load_page(0)  # Load the first (and only) page
        pix = page.get_pixmap()

        # Convert to PNG and store in memory
        image_bytes = BytesIO()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image.save(image_bytes, format="PNG")
        image_bytes.seek(0)

        images.append(image_bytes)

    return images

def convert_image_to_bytes(image):
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return image_bytes.getvalue()

def get_png_images_from_folder(folder_path, extensions=("png", "jpg", "jpeg")):
    """Reads images with specified extensions from a folder and returns a list of in-memory images (BytesIO objects)."""
    images = []
    # Check if the folder exists
    if not os.path.exists(folder_path):
        print(f"Folder does not exist: {folder_path}")
        return images
    print(f"Reading files from folder: {folder_path}")
    # Iterate over files in the folder
    for filename in sorted(os.listdir(folder_path)):
        # Check if the file has an acceptable extension
        if any(filename.lower().endswith(ext) for ext in extensions):
            image_path = os.path.join(folder_path, filename)
            # Read the file as bytes and store it in-memory
            with open(image_path, "rb") as img_file:
                img_bytes = BytesIO(img_file.read())
                img_bytes.seek(0)
                images.append(img_bytes)
    return images

def get_png_images_from_folder(folder_path, extensions=("png", "jpg", "jpeg")):
    """Reads images with specified extensions from a folder and returns a list of in-memory images (BytesIO objects)."""
    images = []
    # Check if the folder exists
    if not os.path.exists(folder_path):
        print(f"Folder does not exist: {folder_path}")
        return images
    
    print(f"Reading files from folder: {folder_path}")
    
    # Define a custom sorting key function
    def numerical_sort_key(filename):
        return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', filename)]
    
    # Iterate over files in the folder
    for filename in sorted(os.listdir(folder_path), key=numerical_sort_key):
        # Check if the file has an acceptable extension
        if any(filename.lower().endswith(ext) for ext in extensions):
            image_path = os.path.join(folder_path, filename)
            # Read the file as bytes and store it in-memory
            with open(image_path, "rb") as img_file:
                img_bytes = BytesIO(img_file.read())
                img_bytes.seek(0)
                images.append(img_bytes)
    return images


def translate_images(path, filename):
    # If the file is a pdf, split the pdf -> translate each image in memory -> merge back into translated folder
    if filename[-4:] == '.pdf':
        print('Translating PDF')
        filename = filename[:-4]
        # Split PDF and get list of in-memory PNG images
        png_images = split_pdf_to_png_in_memory(path)
    else:
        print('Translating Folder of Images')
        png_images = get_png_images_from_folder(path)

    # Will hold the modified pngs for merging later
    modified_png_lst = []
    print(f"Total PNG images created: {len(png_images)}")
    for page in png_images:

        # Display the first image as a PIL Image (optional)
        img = Image.open(page)
        #img_start.show()  # This will open the image in the default image viewer

        # Convert the image to raw bytes
        img = convert_image_to_bytes(img)

        # Detect text
        try:
            texts, detected_language = new_detect_text(img)
        except:
            print('DNS Error')
            time.sleep(5)
            texts = new_detect_text(img)

        img = Image.open(BytesIO(img))

        # Combine bounding boxes with a threshold 
        merged_boxes = []

        for text in texts:
            if texts.index(text) == 0:
                continue
            vertices = text.bounding_poly.vertices
            x_min, y_min = vertices[0].x, vertices[0].y
            x_max, y_max = vertices[2].x, vertices[2].y

            # Ensure y_min is always the top coordinate
            if y_min > y_max:
                y_min, y_max = y_max, y_min
            if x_min > x_max:
                x_min, x_max = x_max, x_min

            # Check if the box can be merged with an existing merged box
            merged = False
            for mbox in merged_boxes:
                pixLength = 50  # Lower the threshold for closer boxes

                # Merge condition: boxes should either be overlapping or close enough
                if (mbox[0] <= x_max + pixLength and mbox[2] >= x_min - pixLength) and \
                (mbox[1] <= y_max + pixLength and mbox[3] >= y_min - pixLength):
                    # Update the merged box to encompass both areas
                    mbox[0] = min(x_min, mbox[0])
                    mbox[1] = min(y_min, mbox[1])
                    mbox[2] = max(x_max, mbox[2])
                    mbox[3] = max(y_max, mbox[3])
                    merged = True
                    break

            if not merged:
                merged_boxes.append([x_min, y_min, x_max, y_max])

        # Refine the combination to ensure no overlapping or redundant boxes
        combined_boxes = []
        for box in merged_boxes:
            combined = False
            for cbox in combined_boxes:
                if box[0] >= cbox[0] and box[1] >= cbox[1] and \
                box[2] <= cbox[2] and box[3] <= cbox[3]:
                    combined = True
                    break

            if not combined:
                combined_boxes.append(box)

        # Convert list of lists to a dictionary with keys as tuples and values as empty lists
        dict_from_lists = {tuple(lst): [] for lst in combined_boxes}

        for text in texts:
            if texts.index(text) == 0:
                continue

            vertices = text.bounding_poly.vertices
            # Top Left point of BB
            x_min, y_min = vertices[0].x, vertices[0].y
            # Bottom right point of BB
            x_max, y_max = vertices[2].x, vertices[2].y
            # BB of the detexted character
            character = text.description
            characterBB = (x_min, y_min, x_max, y_max)

            enclosing_box = find_enclosing_box(combined_boxes, characterBB)
            enclosing_box = tuple(enclosing_box)

            dict_from_lists[enclosing_box].append(character)

        # Draw combined boxes
        draw = ImageDraw.Draw(img)

        '''for box in combined_boxes:
                    # Draw the final rectangles on the image
                    draw.rectangle(box, outline='white', fill = 'white', width=2)'''
                # Save the image with combined boxes

        for box, text_list in dict_from_lists.items():
            # Calculate width and height based on box coordinates
            left, top, right, bottom = box
            print('\n')
            print(box)
            width = right - left
            height = bottom - top

            '''print('Width')
            print(width)
            print('Height')
            print(height)'''

            # Checking if the box is height biased
            if 10*width < height:
                # Lets do 10% width on each ends for a total of 20% increase in width
                width_increase = width*2
                left -= int((1/2)*width_increase)
                right += int((1/2)*width_increase)
                width = right - left
                height = bottom - top

                box = (left, top, right, bottom)
                '''print('New Box')
                print(box)
                print('New Width')
                print(width)
                print('New Height')
                print(height)'''

            elif width < ((1/2)*height):
                # Lets do 10% width on each ends for a total of 20% increase in width
                width_increase = width*0.25
                left -= int((1/2)*width_increase)
                right += int((1/2)*width_increase)
                width = right - left
                height = bottom - top

                box = (left, top, right, bottom)

            text = ' '.join(text_list)
            translated = None
            while True:
                try:
                    translated = GoogleTranslator(source=detected_language, target='english').translate(text)
                    break
                except requests.exceptions.ConnectionError as e:
                    print("Connection error: Unable to reach Google Translate API")
                    time.sleep(2)
                except LanguageNotSupportedException as e:
                    if detected_language == 'zh':
                        translated = GoogleTranslator(source='chinese (simplified)', target='english').translate(text)
                        break
                    else:
                        print(f"Not Supported Language: {detected_language}")
                        time.sleep(2)
                        break

            
            if translated is None:
                print('Len is None')
                continue
            elif len(translated) < 4:
                print('Smaller than alloited')
                print(translated)
                continue
            elif translated.isdigit():
                print("Returned a Digit")
                print(translated)
                continue
            elif is_sentence_gibberish(translated) == True:
                print('Sentence is gibberish')
                print(translated)
                continue

            # If text is all good, draw box
            draw.rectangle(box, outline='white', fill = 'white', width=2)

            print(translated)
            selected_size = 0
            #font = ImageFont.truetype(font="font\\CC Wild Words Roman.ttf", size=size)

            print('Getting font size')
            for size in range(1, 500):
                # Try except block to find the selected size of the font 
                try:
                    font = ImageFont.truetype(
                        font="font\\CC Wild Words Roman.ttf",
                        size=size)
                    textBox_singlelined = font.getbbox(translated)

                    single_Length = abs(textBox_singlelined[0] - textBox_singlelined[2])
                    avg_char_width_using_getbbox = single_Length / len(translated)

                    max_char_count_Using_getbbox = int((width * .95) / avg_char_width_using_getbbox)

                    
                    text_wrapped = textwrap.fill(text=text, width=max_char_count_Using_getbbox)

                    current_lines = math.ceil(len(text) / max_char_count_Using_getbbox)

                    textBox_multilined = draw.multiline_textbbox(
                        # img testing
                        xy=(img.size[0] / 2, img.size[1] / 2),
                        text=text_wrapped,
                        font=font,
                        anchor='mm',
                        align='center')
                    #print(textBox_multilined)

                    Multi_Length = abs(textBox_multilined[0] - textBox_multilined[2])
                    Multi_Height = abs(textBox_multilined[1] - textBox_multilined[3])

                    height_PerLine = Multi_Height / current_lines

                    if Multi_Length > width * .7 and Multi_Height > height * .9:
                        break

                    selected_size += 1

                except ValueError:
                    print('ValueError: invalid width 0 (must be > 0)')
                    break

            try:
                '''print('selected_size')
                print(selected_size)'''
                font = ImageFont.truetype(
                    font="font\\CC Wild Words Roman.ttf",
                    size=selected_size/1.75)
                textBox_singlelined = font.getbbox(translated)
                single_Length = abs(textBox_singlelined[0] - textBox_singlelined[2])
                avg_char_width_using_getbbox = single_Length / len(translated)
                max_char_count_Using_getbbox = int((width * .95) / avg_char_width_using_getbbox)

                text_wrapped = textwrap.fill(text=translated, width=max_char_count_Using_getbbox)
                draw.text(
                    xy=(((box[0]+box[2])/2),
                        ((box[1]+box[3])/2)),
                    text=text_wrapped,
                    font=font,
                    fill='black',
                    anchor='mm',
                    align='center')
                
            except:
                print('break')
                continue
        
        modified_png_lst.append(img)
        #img.show()

    return modified_png_lst

def image_to_pdf_in_memory(image):
    # Create a BytesIO object to store the PDF in memory
    pdf_bytes = BytesIO()

    # Save the PIL Image as a PDF into the BytesIO stream
    image.save(pdf_bytes, format="PDF", resolution=100.0)

    # Reset the stream position to the beginning
    pdf_bytes.seek(0)

    return pdf_bytes

def convert_images_to_pdf_and_merge(modified_png_lst, filename, output_directory):

    # Ensure the filename ends with '.pdf'
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    pdf_writer = PdfWriter()

    for image in modified_png_lst:
        # Ensure image is a PIL Image object
        if isinstance(image, Image.Image):
            # Convert the image to a PDF in memory
            pdf_stream = image_to_pdf_in_memory(image)

            # Read the in-memory PDF and add the page to the PdfWriter
            pdf_reader = PdfReader(pdf_stream)
            pdf_writer.add_page(pdf_reader.pages[0])
        else:
            raise TypeError("List contains a non-image object.")

    # Create a BytesIO object to store the merged PDF
    merged_pdf_bytes = BytesIO()
    pdf_writer.write(merged_pdf_bytes)
    merged_pdf_bytes.seek(0)
    
    with open(output_directory, "wb") as output_file:
        output_file.write(merged_pdf_bytes.getvalue())

    return 