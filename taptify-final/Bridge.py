import pandas as pd
import os
import sys
import re

def clean_bad_resolution_column(df):
    """
    Cleans the 'Bad Resolution' column by stripping spaces, converting to strings, and removing non-visible characters.
    """
    # Convert all entries to strings (in case there are numeric or mixed data)
    df['Bad Resolution'] = df['Bad Resolution'].astype(str)
    
    # Remove non-visible and non-printable characters using a regex
    df['Bad Resolution'] = df['Bad Resolution'].apply(lambda x: re.sub(r'[^\x00-\x7F]+', '', x))
    
    # Strip leading/trailing whitespace
    df['Bad Resolution'] = df['Bad Resolution'].str.strip()
    
    # Log the values that are empty after cleaning
    empty_entries = df[df['Bad Resolution'] == '']
    if not empty_entries.empty:
        print(f"Found {len(empty_entries)} rows with empty 'Bad Resolution' after cleaning.")
    
    # Return dataframe with non-empty rows
    return df[df['Bad Resolution'] != '']  # Only keep rows where 'Bad Resolution' is non-empty

def merge_excel_files(file1_path, file2_path):
    # Read the first Excel file to get the column names
    df1_all = pd.read_excel(file1_path)

    # List of columns to include (default)
    columns_to_use = ['Name', 'Address', 'Website', 'Phone']

    # Check if 'Email' column is present, and add it if available
    if 'Email' in df1_all.columns:
        columns_to_use.append('Email')

    # Read only the relevant columns from the first Excel file
    df1 = df1_all[columns_to_use]

    # Read the second Excel file (Bad Resolution)
    df2 = pd.read_excel(file2_path, usecols=['Bad Resolution'])

    # Clean and filter 'Bad Resolution' column
    df2_clean = clean_bad_resolution_column(df2)

    # Check if there are duplicate columns in df1 and df2 and handle them
    for column in df1.columns:
        if column in df2_clean.columns:
            print(f"Warning: Duplicate column found: {column}")
            # To avoid duplication, rename df2 column if needed (or remove it if not needed)
            df2_clean = df2_clean.rename(columns={column: f"{column}_from_df2"})

    # Merge both dataframes
    merged_df = pd.concat([df1, df2_clean], axis=1)

    # Add two empty columns: Good Resolution and QR Codes
    merged_df['Good Resolution'] = ''
    merged_df['QR Codes'] = ''

    # Define the output file path (same folder as input files)
    output_file_path = os.path.join(os.path.dirname(file1_path), 'clients.xlsx')

    # Save the merged data to a new Excel file
    merged_df.to_excel(output_file_path, index=False)
    print(f'Clients file created: {output_file_path}')


if __name__ == "__main__":
    # Ensure that the script receives exactly one argument
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <path_to_excel_file>")
        sys.exit(1)  # Exit if the argument count is wrong

    # Take the file path from command-line arguments
    file1_path = sys.argv[1]

    # Extract the base name (without extension) and extension of file1_path
    base_name, extension = os.path.splitext(file1_path)

    # Concatenate _updated to the base name and append the original extension
    file2_path = f"{base_name}_updated{extension}"

    # Now file2_path will be something like 'clients_updated.xlsx'
    merge_excel_files(file1_path, file2_path)
