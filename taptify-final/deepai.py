import time
import json
import pandas as pd
from pathlib import Path
from urllib.request import urlretrieve
import requests

API_KEY = ""


def process_files(file_path):
    # Load the Excel file into a pandas DataFrame
    df = pd.read_excel(file_path)

    # Check if "Bad Resolution" column exists
    if "Bad Resolution" not in df.columns:
        print("The 'Bad Resolution' column is not present in the Excel file.")
        return

    # Iterate over the "Bad Resolution" column
    for index, row in df.iterrows():
        image_path = row['Bad Resolution']
        if pd.isna(image_path):
            print(f"Skipping row {index}... No path provided.")
            continue

        # Enhance image and get the path of the enhanced image
        enhanced_image_path = upscale_image(image_path, "highres_images")

        if enhanced_image_path:
            df.at[index, 'Good Resolution'] = enhanced_image_path
        else:
            df.at[index, 'Good Resolution'] = 'Error during processing'

    # Save the updated DataFrame back to the Excel file
    df.to_excel(file_path, index=False)
    print("Processing complete. Enhanced image paths saved in 'Good Resolution' column.")


def upscale_image(image_path, dest_folder):
    # Get Image file name : filename.png
    image_filename = Path(image_path).name
    output_folder = Path(dest_folder)

    # Create output folder if not exist
    output_folder.mkdir(exist_ok=True)

    # Generate path for saving output file "highres_images/filename.png"
    output_file = output_folder / image_filename

    p = Path(output_file)
    if p.exists():
        print(f"Skipping... File Already Processed: {image_path}")
        return str(output_file)

    print(f"Processing... {image_path}")

    headers = {
        'x-api-key': API_KEY,
    }

    data = {
        "enhancements": ["denoise", "deblur", "light"],
        "width": 2000
    }

    data_dumped = {"parameters": json.dumps(data)}


    try:
        with open(image_path, 'rb') as f:
            response = requests.post('https://deep-image.ai/rest_api/process_result', headers=headers,
                                     files={'image': f},
                                     data=data_dumped)

            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('status') == 'complete':
                    urlretrieve(response_json['result_url'], output_file)
                    return str(output_file)
                elif response_json['status'] in ['received', 'in_progress']:
                    while response_json['status'] == 'in_progress':
                        response = requests.get(f'https://deep-image.ai/rest_api/result/{response_json["job"]}',
                                                headers=headers)
                        response_json = response.json()
                        time.sleep(1)
                    if response_json['status'] == 'complete':
                        urlretrieve(response_json['result_url'], output_file)
                        return str(output_file)
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None


if __name__ == "__main__":
    process_files('clients.xlsx')
