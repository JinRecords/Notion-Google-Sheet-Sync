import os
import glob
import shutil
from PIL import Image
from bs4 import BeautifulSoup
import pdfkit
import pathlib
from urllib.parse import unquote

# Explicitly register pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass # pillow_heif not found

def is_image_file(file_path):
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.heic']
    return any(file_path.lower().endswith(ext) for ext in image_extensions)

def process_images(source_directory, output_directory, max_size_kb=300):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    image_map = {}
    notion_face_paths = []
    image_counter = 1
    
    for file_path in glob.glob(os.path.join(source_directory, '**', '*'), recursive=True):
        if os.path.isfile(file_path) and is_image_file(file_path):
            try:
                relative_path = os.path.relpath(file_path, source_directory)

                with Image.open(file_path) as img:
                    img.thumbnail((1280, 720))
                    new_filename = f'image_{image_counter}.jpg'
                    new_filepath = os.path.join(output_directory, new_filename)
                    
                    while os.path.exists(new_filepath):
                        image_counter += 1
                        new_filename = f'image_{image_counter}.jpg'
                        new_filepath = os.path.join(output_directory, new_filename)

                    img = img.convert('RGB')
                    quality = 85
                    img.save(new_filepath, 'JPEG', quality=quality)
                    
                    while os.path.getsize(new_filepath) > max_size_kb * 1024 and quality > 10:
                        quality -= 5
                        img.save(new_filepath, 'JPEG', quality=quality)

                    relative_new_path = os.path.join(os.path.basename(output_directory), new_filename)
                    image_map[relative_path] = relative_new_path
                    image_counter += 1

                    if 'my-notion-face' in os.path.basename(file_path):
                        notion_face_paths.append(relative_new_path)

            except Exception as e:
                print(f"Could not process file {file_path}: {e}")

    return image_map, notion_face_paths

def update_html_and_create_gallery(html_path, image_map, notion_face_paths):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    figure_counter = 1

    for img_tag in soup.find_all('img'):
        src = img_tag.get('src', '')
        if not src:
            img_tag.decompose()
            continue
            
        unquoted_src = unquote(src)
        normalized_src = os.path.normpath(unquoted_src)

        if normalized_src in image_map:
            new_src = image_map[normalized_src]
            img_tag['src'] = new_src
            
            if new_src not in notion_face_paths:
                anchor_id = f'figure_{figure_counter}'
                a_tag = soup.new_tag('a', href=f'#{anchor_id}')
                img_tag.wrap(a_tag)
                figure_counter += 1
        else:
            img_tag.decompose()

    gallery_html = '<h1 style="page-break-before: always;">Image Gallery</h1>'
    
    gallery_images = sorted([path for path in image_map.values() if path not in notion_face_paths])
    figure_counter = 1

    for i, image_path in enumerate(gallery_images):
        if i % 9 == 0:
            if i > 0:
                gallery_html += '</table>'
            gallery_html += '<table style="width: 100%; border-collapse: collapse; page-break-after: always;">'

        if i % 3 == 0:
            gallery_html += '<tr>'

        anchor_id = f'figure_{figure_counter}'
        gallery_html += f'<td id="{anchor_id}" style="width: 33.33%; border: 1px solid white; vertical-align: top; text-align: center; padding: 5px;">'
        gallery_html += f'<img src="{image_path}" style="width: 100%; height: auto;"/>'
        gallery_html += f'<p>figure {figure_counter}</p>'
        gallery_html += '</td>'

        if (i + 1) % 3 == 0 or (i + 1) == len(gallery_images):
            gallery_html += '</tr>'

        figure_counter += 1

    if gallery_images:
        gallery_html += '</table>'

    soup.body.append(BeautifulSoup(gallery_html, 'html.parser'))
    
    return str(soup)

def main():
    base_dir = os.getcwd()
    output_pdf = os.path.join(base_dir, 'converted.pdf')
    processed_images_dir = os.path.join(base_dir, 'processed_images')
    temp_html_path = os.path.join(base_dir, 'temp.html')

    # Cleanup
    for path in [output_pdf, processed_images_dir, temp_html_path]:
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except OSError:
            pass

    source_directory = os.path.join(base_dir, 'Private & Shared-1')
    html_files = glob.glob(os.path.join(source_directory, '*.html'))
    if not html_files:
        print("No HTML file found.")
        return
        
    html_file = html_files[0]

    image_map, notion_face_paths = process_images(source_directory, processed_images_dir)
    
    final_html = update_html_and_create_gallery(html_file, image_map, notion_face_paths)

    try:
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(final_html)

        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'enable-internal-links': None,
        }

        print("\n--- Generating PDF from temporary HTML file ---")
        pdfkit.from_file(temp_html_path, output_pdf, options=options)
        print(f"--- Successfully converted to {output_pdf} ---")

    finally:
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)

if __name__ == '__main__':
    main()
