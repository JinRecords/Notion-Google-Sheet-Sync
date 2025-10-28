# google_sheets_client.py
from googleapiclient.discovery import build

def _get_sheet_id(service, spreadsheet_id, sheet_name):
    """Helper function to get the sheetId from a sheet name."""
    sheets_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in sheets_metadata['sheets']:
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None

class GoogleSheetsClient:
    """
    A client for interacting with the Google Sheets API.
    """
    def __init__(self, credentials):
        self.service = build('sheets', 'v4', credentials=credentials)

    def get_sheet_data(self, spreadsheet_id, range_name, render_option='FORMATTED_VALUE'):
        """
        Fetches data from a specified range in a Google Sheet.
        """
        sheet = self.service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id, 
            range=range_name, 
            valueRenderOption=render_option
        ).execute()
        return result.get('values', [])

    def get_sheet_grid_data(self, spreadsheet_id, range_name):
        """
        Fetches detailed grid data from a specified range in a Google Sheet.
        """
        request = self.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[range_name],
            includeGridData=True
        )
        return request.execute()

    def batch_update_sheet(self, spreadsheet_id, requests):
        """
        Performs a batch update on a spreadsheet.
        """
        body = {'requests': requests}
        return self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    def update_sheet_with_formatting(self, spreadsheet_id, range_name, notion_data, notion_properties, formula_data=None, ignore_col_indices=None):
        """
        Updates a Google Sheet with data and formatting from Notion, preserving formulas and ignoring specified columns.
        """
        sheet_name = range_name.split('!')[0]
        sheet_id = _get_sheet_id(self.service, spreadsheet_id, sheet_name)
        if sheet_id is None:
            print(f"Error: Sheet '{sheet_name}' not found.")
            return

        # Step 1: Apply formatting requests (data validation, number formats)
        formatting_requests = []
        headers = notion_data[0]
        if ignore_col_indices is None: ignore_col_indices = []

        for col_index, header in enumerate(headers):
            if header not in notion_properties or col_index in ignore_col_indices: continue

            prop = notion_properties[header]
            prop_type = prop['type']
            
            range_spec = {
                'sheetId': sheet_id,
                'startRowIndex': 1, # Start after header
                'startColumnIndex': col_index,
                'endColumnIndex': col_index + 1
            }

            if prop_type == 'select':
                options = [opt['name'] for opt in prop['select']['options']]
                formatting_requests.append({
                    'setDataValidation': {
                        'range': range_spec,
                        'rule': {
                            'condition': {
                                'type': 'ONE_OF_LIST',
                                'values': [{'userEnteredValue': opt} for opt in options]
                            },
                            'strict': True,
                            'showCustomUi': True
                        }
                    }
                })
            elif prop_type == 'checkbox':
                formatting_requests.append({
                    'setDataValidation': {
                        'range': range_spec,
                        'rule': {
                            'condition': {
                                'type': 'BOOLEAN'
                            },
                            'strict': True
                        }
                    }
                })
            elif prop_type == 'number':
                num_format = prop['number']['format']
                patterns = {
                    'number': '#,##0.0000',
                    'number_with_commas': '#,##0.0000',
                    'percent': '0.0000%',
                    'dollar': '$#,##0.0000',
                    'euro': '€#,##0.0000'
                }
                pattern = patterns.get(num_format, '0.0000')
                formatting_requests.append({
                    'repeatCell': {
                        'range': range_spec,
                        'cell': {
                            'userEnteredFormat': {
                                'numberFormat': {
                                    'type': 'NUMBER',
                                    'pattern': pattern
                                }
                            }
                        },
                        'fields': 'userEnteredFormat.numberFormat'
                    }
                })
        
        if formatting_requests:
            self.batch_update_sheet(spreadsheet_id, formatting_requests)

        # Step 2: Update cell values, preserving formulas and ignoring columns
        formula_cells = set()
        if formula_data:
            for r, row in enumerate(formula_data):
                for c, cell in enumerate(row):
                    if isinstance(cell, str) and cell.startswith('='):
                        formula_cells.add((r, c))

        final_data = []
        for r_idx, row in enumerate(notion_data):
            row_data = []
            for c_idx, cell_value in enumerate(row):
                if (r_idx, c_idx) in formula_cells or c_idx in ignore_col_indices:
                    row_data.append(None) # This tells the values.update API to skip the cell
                else:
                    row_data.append(cell_value)
            final_data.append(row_data)

        update_body = {'values': final_data}
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption='USER_ENTERED', body=update_body
        ).execute()

    def update_sheet(self, spreadsheet_id, range_name, notion_data):
        """
        Original method to update a Google Sheet with data from Notion.
        """
        sheet_formulas = self.get_sheet_data(spreadsheet_id, range_name, render_option='FORMULA')
        formula_cells = set()
        for r, row in enumerate(sheet_formulas):
            for c, cell in enumerate(row):
                if isinstance(cell, str) and cell.startswith('='):
                    formula_cells.add((r, c))

        max_rows = len(notion_data)
        max_cols = len(notion_data[0]) if notion_data else 0
        final_data = []
        for r in range(max_rows):
            row_data = []
            for c in range(max_cols):
                if (r, c) in formula_cells:
                    row_data.append(None)
                else:
                    row_data.append(notion_data[r][c] if c < len(notion_data[r]) else "")
            final_data.append(row_data)

        update_body = {'values': final_data}
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption='USER_ENTERED', body=update_body
        ).execute()