import os
from google.cloud import vision
import textwrap
from PIL import Image, ImageDraw, ImageFont
import math
from deep_translator import GoogleTranslator, single_detection
import time
from functions import createFolder, folderfiles
import nltk
nltk.download('words')
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

    return texts

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
    words_in_sentence = sentence.split()
    valid_words_count = sum(1 for word in words_in_sentence if word.lower() in nltk_words)
    return valid_words_count < len(words_in_sentence) * 0.5  # Threshold: less than 50% valid words


def main():
    # printing all files in the images folder for user to pick from
    # This is where we will look to find pdf's to translate
    cwd = os.getcwd()
    queueFldr = 'ProcessingQueue'
    path_to_imagefldr = os.path.join(cwd, queueFldr)

    # Path to pdf to be converted
    user_requested_path = folderfiles(queueFldr)


if __name__ == '__main__':
    main()







imagefldr = 'images'
# folder of individual png's
fldrOfImages = 'Test Folder'

fldrOfImages_path = os.path.join(imagefldr, fldrOfImages)

# Create the directory
# Define the folder path you want to create
folder_path = f'{imagefldr}/translated'
os.makedirs(folder_path, exist_ok=True)

list_of_imgs = os.listdir(fldrOfImages_path)

print("\nTranslating images...\n")
for i in list_of_imgs:
    print(i)

    pathToImg = os.path.join(fldrOfImages_path, i)

    # Do transformation on image
    # Iterate over each box and draw the text inside
    img = Image.open(pathToImg)

    # Detect text
    try:
        texts = detect_text(pathToImg)
    except:
        print('DNS Error')
        time.sleep(5)
        texts = detect_text(pathToImg)

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
        translated = GoogleTranslator(source='chinese (simplified)', target='english').translate(text)

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

    #img.show()

    save_path = os.path.join(imagefldr,'translated',i)
    img.save(save_path)



    