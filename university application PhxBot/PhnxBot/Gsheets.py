import gspread
from oauth2client.service_account import ServiceAccountCredentials

class GoogleSheetHandler:
    def __init__(self, credentials_file, sheet_key, status_column="STATUS"):
        """
        credentials_file: Path to the service account JSON key file.
        sheet_key: The spreadsheet ID from the URL.
        status_column: The name of the column to check/update.
        """
        self.credentials_file = credentials_file
        self.sheet_key = sheet_key
        self.status_column = status_column
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.client = self._authorize()
        self.sheet = self.client.open_by_key(self.sheet_key).sheet1

    def _authorize(self):
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, self.scope)
        return gspread.authorize(creds)

    def get_all_records(self):
        """Return all records as a list of dictionaries."""
        return self.sheet.get_all_records()

    def get_next_n_unprocessed(self, n):
        """
        Return the first n rows with empty STATUS.
        Returns: list of (row_index, row_dict), where row_index is 0-based (excluding header).
        """
        data = self.get_all_records()
        return [
            (i, row) for i, row in enumerate(data)
            if not row.get(self.status_column)
        ][:n]

    def update_status(self, row_index, new_status):
        """
        Update the STATUS column for the given row index (0-based, excluding header).
        """
        header = self.sheet.row_values(1)
        if self.status_column not in header:
            raise ValueError(f"Column '{self.status_column}' not found in sheet.")
        col_index = header.index(self.status_column) + 1  # gspread is 1-based
        self.sheet.update_cell(row_index + 2, col_index, new_status)  # +2 = 1 (header) + 1 (0-based row)

if __name__ == "__main__":
    # Use the correct spreadsheet key from the URL
    # URL: https://docs.google.com/spreadsheets/d/
    sheet_key = ""

    handler = GoogleSheetHandler("phoenix-462906-c4271d0cdf4b.json", sheet_key)

    # Get first 5 unprocessed rows
    unprocessed = handler.get_next_n_unprocessed(1)
    for index, row in unprocessed:
        print(f"Row {index}: {row}")

    # Update status for the first unprocessed row
    if unprocessed:
        handler.update_status(unprocessed[0][0], "IN_PROGRESS")
