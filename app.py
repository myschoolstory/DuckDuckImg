import gradio as gr
from duckduckgo_search import DDGS
import os
import zipfile
import shutil
import uuid
import requests

def scrape_and_zip(search_term: str, max_images: int):
    """
    Scrapes images from DuckDuckGo for a given search term,
    zips them, and returns the path to the zip file.

    Args:
        search_term: The term to search for.
        max_images: The maximum number of images to download.

    Returns:
        The path to the generated zip file.
    """
    if not search_term:
        raise gr.Error("Please enter a search term.")

    # Create a unique temporary directory for the images
    temp_dir = f"temp_images_{uuid.uuid4()}"
    os.makedirs(temp_dir, exist_ok=True)

    print(f"Downloading images for '{search_term}' to '{temp_dir}'...")
    try:
        # Use duckduckgo_search to get image URLs
        image_urls = []
        with DDGS() as ddgs:
            results = ddgs.images(
                keywords=search_term,
                region="wt-wt",
                safesearch="off",
                size=None,
                color=None,
                type_image=None,
                layout=None,
                license_image=None,
                max_results=max_images,
            )
            for r in results:
                image_urls.append(r['image'])

        # Download the images from the URLs
        for i, url in enumerate(image_urls):
            try:
                response = requests.get(url, stream=True, timeout=5)
                response.raise_for_status()
                # Get the file extension or default to .jpg
                file_extension = os.path.splitext(url)[1] or '.jpg'
                if '?' in file_extension: # Clean up extensions with query params
                    file_extension = file_extension.split('?')[0]
                
                file_path = os.path.join(temp_dir, f"image_{i}{file_extension}")

                with open(file_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            except Exception as e:
                print(f"Could not download image {url}: {e}")


        # Check if any images were downloaded
        image_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        if not image_files:
            shutil.rmtree(temp_dir)
            raise gr.Error(f"No images found or could be downloaded for '{search_term}'. Please try a different search term.")

        # Create a zip file
        zip_path = f"{search_term.replace(' ', '_')}_images.zip"
        print(f"Creating zip file at '{zip_path}'...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, temp_dir))

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)
        print("Temporary directory cleaned up.")

        return zip_path
    except Exception as e:
        # Clean up the temporary directory in case of an error
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print(f"An error occurred: {e}")
        raise gr.Error(f"An error occurred during the process. Please check the console for details.")


with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # DuckDuckGo Image Scraper & Ziper
        Enter a search term to scrape high-quality images from DuckDuckGo.
        The images will be compiled into a zip folder for you to download. It all takes about 20 seconds.
        """
    )
    with gr.Row():
        with gr.Column(scale=3):
            search_input = gr.Textbox(label="Search Term", placeholder="e.g., 'cute cats'")
        with gr.Column(scale=1):
            num_images_input = gr.Slider(
                minimum=10,
                maximum=200,
                value=50,
                step=10,
                label="Number of Images"
            )
    scrape_button = gr.Button("Scrape and Zip Images", variant="primary")
    with gr.Row():
        output_file = gr.File(label="Download Zipped Images")

    scrape_button.click(
        fn=scrape_and_zip,
        inputs=[search_input, num_images_input],
        outputs=output_file
    )

if __name__ == "__main__":
    demo.launch()