import os
import fitz  # PyMuPDF
from PIL import Image
import io

# --- Configuration ---
# List of PDF files to extract images from
PDF_FILES = [
    "Food Group .pdf",
    "Malaysian food portion size  photo album.pdf"
]
# Directory to save the extracted images
OUTPUT_DIR = os.path.join("data", "images")

def extract_images_from_pdfs():
    """
    Extracts all images from the specified PDF files and saves them
    to the output directory.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")

    for pdf_file in PDF_FILES:
        if not os.path.exists(pdf_file):
            print(f"Warning: PDF file not found at '{pdf_file}'. Skipping.")
            continue

        print(f"--- Processing {pdf_file} ---")
        doc = fitz.open(pdf_file)
        image_count = 0

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Generate a descriptive filename
                filename_prefix = os.path.splitext(os.path.basename(pdf_file))[0].replace(" ", "_")
                image_filename = f"{filename_prefix}_p{page_num + 1}_img{img_index}.png"
                output_path = os.path.join(OUTPUT_DIR, image_filename)

                # Save the image
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    image.save(output_path, "PNG")
                    image_count += 1
                except Exception as e:
                    print(f"Could not save image {img_index} on page {page_num + 1}: {e}")

        print(f"Extracted {image_count} images from {pdf_file}\n")
        doc.close()

if __name__ == "__main__":
    extract_images_from_pdfs()
    print("✅ Image extraction complete.")