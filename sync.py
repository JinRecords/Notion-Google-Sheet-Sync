# sync.py

# --- Standard Library Imports ---
import pickle
import os.path
import time
import json
import logging

# --- Third-Party Library Imports ---
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from notion_client import Client


logging.basicConfig(
    filename='sync_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Core Functions ---

def load_config():
    """
    Loads and validates the configuration from the config.json file.
    
    Returns:
        dict: A dictionary containing the configuration settings.
        None: If the file is not found, invalid, or missing required keys.
    """
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Please create it.")
        return None
    except json.JSONDecodeError:
        print("Error: config.json is not a valid JSON file.")
        return None

# Defines the permissions the script will request from the user's Google account.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_creds():
    """
    Manages Google API authentication. It will either load saved credentials,
    refresh expired ones, or prompt the user to log in for the first time.
    
    Returns:
        google.oauth2.credentials.Credentials: Valid credentials for the Google API.
    """
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def get_sheet_data(service, spreadsheet_id, range_name, render_option='FORMATTED_VALUE'):
    """
    Fetches data from a specified range in a Google Sheet.
    
    Args:
        service: The authenticated Google Sheets API service object.
        spreadsheet_id (str): The ID of the Google Sheet.
        range_name (str): The A1 notation of the range to retrieve (e.g., 'Sheet1!A:E').
        render_option (str): How values should be represented. 'FORMULA' is used to detect formulas.
    
    Returns:
        list: A list of lists representing the rows and columns of data.
    """
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=spreadsheet_id, 
        range=range_name, 
        valueRenderOption=render_option
    ).execute()
    return result.get('values', [])

def get_notion_data(notion_client, database_id, expected_headers):
    """
    Retrieves all pages from a Notion database and formats them into a grid,
    ensuring the column order matches the provided 'expected_headers'.
    
    Args:
        notion_client: The authenticated Notion client object.
        database_id (str): The ID of the Notion database.
        expected_headers (list): A list of strings representing the desired column order.
    
    Returns:
        list: A list of lists, with the first list being the headers.
    """
    results = []
    has_more = True
    next_cursor = None
    
    while has_more:
        response = notion_client.databases.query(database_id=database_id, start_cursor=next_cursor)
        results.extend(response['results'])
        has_more = response['has_more']
        next_cursor = response['next_cursor']

    data_grid = [expected_headers]
    for page in results:
        row = []
        for prop_name in expected_headers:
            prop = page['properties'].get(prop_name, {})
            prop_type = prop.get('type')
            content = ""
            if prop_type and prop.get(prop_type):
                if prop_type == 'title' and prop['title']: content = prop['title'][0]['text']['content']
                elif prop_type == 'rich_text' and prop['rich_text']: content = prop['rich_text'][0]['text']['content']
            row.append(content)
        data_grid.append(row)
    return data_grid

def update_sheet(service, spreadsheet_id, range_name, notion_data):
    """
    Updates a Google Sheet with data from Notion, preserving any formulas in the sheet.
    
    Args:
        service: The authenticated Google Sheets API service object.
        spreadsheet_id (str): The ID of the Google Sheet to update.
        range_name (str): The range to update.
        notion_data (list): The data from Notion to write to the sheet.
    """
    sheet_formulas = get_sheet_data(service, spreadsheet_id, range_name, render_option='FORMULA')
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
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueInputOption='USER_ENTERED', body=update_body
    ).execute()

def notion_upsert(notion_client, data, database_id):
    """
    Performs an "upsert" operation in Notion: updates existing pages or inserts new ones.
    It identifies pages based on the value in the first column (the 'Title').
    
    Args:
        notion_client: The authenticated Notion client object.
        data (list): The data from the Google Sheet, including headers.
        database_id (str): The ID of the Notion database to update.
    """
    if not data or len(data) < 2: return
    
    headers, data_rows, title_property_name = data[0], data[1:], data[0][0]
    
    existing_pages = notion_client.databases.query(database_id=database_id)
    title_to_page_id = {
        p['properties'][title_property_name]['title'][0]['text']['content']: p['id']
        for p in existing_pages.get('results', []) if p['properties'][title_property_name]['title']
    }

    for row_data in reversed(data_rows):
        if not row_data: continue
        
        title_value = row_data[0]
        properties = {title_property_name: {'title': [{'text': {'content': str(title_value)}}]}}
        for header, value in zip(headers[1:], row_data[1:]):
            properties[header] = {'rich_text': [{'text': {'content': str(value)}}]}

        if title_value in title_to_page_id:
            notion_client.pages.update(page_id=title_to_page_id[title_value], properties=properties)
        else:
            notion_client.pages.create(parent={'database_id': database_id}, properties=properties)

# --- Main Application Logic ---

def run_sync_cycle(config, google_service, notion_client):
    """
    Runs one full sync cycle for all pairs defined in the config file.
    Includes error handling to prevent the script from crashing.
    
    Args:
        config (dict): The loaded configuration dictionary.
        google_service: The authenticated Google Sheets API service object.
        notion_client: The authenticated Notion client object.
    """
    spreadsheet_id = config['SAMPLE_SPREADSHEET_ID']
    for pair in config['SYNC_PAIRS']:
        sheet_range, db_id, priority = pair['RANGE'], pair['DATABASE_ID'], pair['PRIORITY']
        print(f"--- Starting Sync | Range: {sheet_range} | DB: {db_id} | Priority: {priority} ---")

        # --- MODIFIED: Added a try...except block to catch errors for each sync pair ---
        try:
            if priority == 'notion':
                sheet_headers_data = get_sheet_data(google_service, spreadsheet_id, sheet_range)
                if not sheet_headers_data: continue
                sheet_headers = sheet_headers_data[0]
                
                notion_data = get_notion_data(notion_client, db_id, sheet_headers)
                if notion_data and len(notion_data) > 1:
                    print("Updating Google Sheet from Notion...")
                    update_sheet(google_service, spreadsheet_id, sheet_range, notion_data)
                
                print("Waiting 1 second for calculations...")
                time.sleep(1)
                
                calculated_sheet_data = get_sheet_data(google_service, spreadsheet_id, sheet_range)
                if calculated_sheet_data:
                    print("Updating Notion from Google Sheet...")
                    notion_upsert(notion_client, calculated_sheet_data, db_id)

            elif priority == 'sheet':
                sheet_data = get_sheet_data(google_service, spreadsheet_id, sheet_range)
                if sheet_data:
                    print("Updating Notion from Google Sheet...")
                    notion_upsert(notion_client, sheet_data, db_id)
            else:
                print(f"Unknown priority '{priority}'. Skipping.")
        
        except Exception as e:
            # If any error occurs, log it to the file and print a message to the console.
            print(f"An error occurred with sync pair (Range: {sheet_range}, DB: {db_id}). See sync_errors.log for details.")
            # logging.exception will record the full error traceback in the log file.
            logging.exception(f"Failed to sync pair (Range: {sheet_range}, DB: {db_id})")

        print("--- Sync finished for this pair --- \n")

# This is the main entry point of the script.
if __name__ == '__main__':
    config = load_config()
    if config:
        run_repeatedly = config.get('RUN_REPEATEDLY', False)
        interval_minutes = config.get('REPEAT_INTERVAL_MINUTES', 30)

        google_creds = get_google_creds()
        google_service = build('sheets', 'v4', credentials=google_creds)
        notion = Client(auth=config['NOTION_INTEGRATION_TOKEN'])

        if not run_repeatedly:
            print("Running sync once.")
            run_sync_cycle(config, google_service, notion)
            print("Sync complete.")
        else:
            print(f"Starting repeated sync. Interval: {interval_minutes} minutes.")
            try:
                while True:
                    run_sync_cycle(config, google_service, notion)
                    print(f"Sync cycle complete. Waiting for {interval_minutes} minutes...")
                    time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nScript stopped by user. Exiting.")
