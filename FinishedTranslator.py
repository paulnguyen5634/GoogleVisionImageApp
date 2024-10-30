
import os
from google.cloud import vision
import textwrap
from PIL import Image, ImageDraw, ImageFont
import math
from deep_translator import GoogleTranslator, single_detection
import time
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

'''def add_text_in_box(image, text, box_coords, font_path, max_font_size=200):
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = box_coords
    box_width = max(right - left, 1)  # Ensure width is at least 1
    box_height = bottom - top

    # Start with the maximum font size and adjust downwards to fit within the box
    font_size = max_font_size
    while font_size > 10:  # Minimal font size for legibility
        font = ImageFont.truetype(font_path, font_size)
        
        # Estimate max characters per line based on current font size and box width
        max_chars_per_line = max(1, int(box_width / font.getlength(' ')))  
        wrapped_text = textwrap.fill(text, width=max_chars_per_line)

        # Calculate the width and height of the entire wrapped text
        lines = wrapped_text.splitlines()
        line_height = font.getbbox('A')[3] - font.getbbox('A')[1]  # Height of one line
        total_text_height = line_height * len(lines)
        
        # Check if the text fits within both width and height constraints
        if total_text_height <= box_height and all(font.getlength(line) <= box_width for line in lines):
            break  # Font size fits within both dimensions, stop reducing
        font_size -= 1  # Reduce font size and try again

    # Re-check the font size to avoid unreadable text
    if font_size < 10:
        font_size = 10  # Set a minimum font size if the box is too small

    # Final drawing with adjusted font size and wrapping
    font = ImageFont.truetype(font_path, font_size)
    wrapped_text = textwrap.fill(text, width=max(1, int(box_width / font.getlength(' '))))

    # Draw the text, centered in the box
    y = top + (box_height - total_text_height) // 2  # Vertically center the text
    for line in wrapped_text.splitlines():
        line_width = font.getlength(line)
        x = left + (box_width - line_width) // 2  # Horizontally center each line
        draw.text((x, y), line, font=font, fill="black")
        y += line_height  # Move y-coordinate for the next line'''






imagefldr = 'images'
# folder of individual png's
fldrOfImages = 'Combined'

image_path = os.path.join(imagefldr, fldrOfImages)

# Create the directory
# Define the folder path you want to create
folder_path = f'{image_path}/translated'
os.makedirs(folder_path, exist_ok=True)

list_of_imgs = os.listdir(image_path)

print("\nTranslating images...\n")
for i in range(0,len(list_of_imgs)):
#for i in range(0,10):
    try:
        '''if i == 0 or i == 1 or i == 2 or i == 3 or i == 4:
            pathToImg = os.path.join(image_path, list_of_imgs[i])
            img = Image.open(pathToImg)

            output_path = os.path.join(folder_path,list_of_imgs[i])
            img.save(output_path)
            continue'''
        print(list_of_imgs[i])
        pathToImg = os.path.join(image_path, list_of_imgs[i])

        # Do transformation on image
        # Iterate over each box and draw the text inside
        img = Image.open(pathToImg)

        # Detect text
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

        # Draw combined boxes
        draw = ImageDraw.Draw(img)
        for box in combined_boxes:
            # Draw the final rectangles on the image
            draw.rectangle(box, outline='white', fill = 'white', width=2)
        # Save the image with combined boxes

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

        percentageChange = 0.30
        for box in dict_from_lists:
            # Calculate width and height based on box coordinates
            left, top, right, bottom = box
            width = right - left
            height = bottom - top

            # Calculate how much to change the left and right sides (5% increase on each side)
            change = int(.25 * width)
            
            # Adjust left and right coordinates to expand the box
            new_left = left - change
            new_right = right + change

            # Draw rectangle with adjusted width
            #draw.rectangle([new_left, top, new_right, bottom], fill='white', outline='black')

        for box, text_list in dict_from_lists.items():
            # Update the box coordinates to use the new width
            left, top, right, bottom = box
            width = right - left
            change = int(percentageChange * width)
            
            # Adjust left and right to expand the box equally on both sides
            new_left = left - change
            new_right = right + change
            adjusted_box = (new_left, top, new_right, bottom)
            
            # Join the text list into a single string
            text = ' '.join(text_list)
            translated = GoogleTranslator(source='chinese (simplified)', target='english').translate(text)

            print(translated)

            if translated is None:
                continue
            elif len(translated) == 1:
                continue

            # Call the add_text_in_box function to draw the text in the expanded box
            add_text_in_box(img, translated, adjusted_box, font_path)

        output_path = os.path.join(folder_path,list_of_imgs[i])
        img.save(output_path)
    except:
        time.sleep(5)
        '''if i == 0:
            pathToImg = os.path.join(image_path, list_of_imgs[i])
            img = Image.open(pathToImg)

            output_path = os.path.join(folder_path,list_of_imgs[i])
            img.save(output_path)'''
        print(list_of_imgs[i])
        pathToImg = os.path.join(image_path, list_of_imgs[i])

        # Do transformation on image
        # Iterate over each box and draw the text inside
        img = Image.open(pathToImg)

        # Detect text
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

        # Draw combined boxes
        draw = ImageDraw.Draw(img)
        for box in combined_boxes:
            # Draw the final rectangles on the image
            draw.rectangle(box, outline='white', fill = 'white', width=2)
        # Save the image with combined boxes

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

        percentageChange = 0.30
        for box in dict_from_lists:
            # Calculate width and height based on box coordinates
            left, top, right, bottom = box
            width = right - left
            height = bottom - top

            # Calculate how much to change the left and right sides (5% increase on each side)
            change = int(.25 * width)
            
            # Adjust left and right coordinates to expand the box
            new_left = left - change
            new_right = right + change

            # Draw rectangle with adjusted width
            #draw.rectangle([new_left, top, new_right, bottom], fill='white', outline='black')

        for box, text_list in dict_from_lists.items():
            # Update the box coordinates to use the new width
            left, top, right, bottom = box
            width = right - left
            change = int(percentageChange * width)
            
            # Adjust left and right to expand the box equally on both sides
            new_left = left - change
            new_right = right + change
            adjusted_box = (new_left, top, new_right, bottom)
            
            # Join the text list into a single string
            text = ' '.join(text_list)
            translated = GoogleTranslator(source='chinese (simplified)', target='english').translate(text)

            print(translated)

            if translated is None:
                continue
            elif len(translated) == 1:
                continue

            # Call the add_text_in_box function to draw the text in the expanded box
            add_text_in_box(img, translated, adjusted_box, font_path)

        output_path = os.path.join(folder_path,list_of_imgs[i])
        img.save(output_path)

print('Finished')