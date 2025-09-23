# data_syncer.py
import time
import logging

class DataSyncer:
    """
    Orchestrates the synchronization between Notion and Google Sheets.
    """
    def __init__(self, config, google_sheets_client, notion_client_wrapper):
        self.config = config
        self.google_sheets_client = google_sheets_client
        self.notion_client_wrapper = notion_client_wrapper

    def _sync_notion_to_sheet(self, spreadsheet_id, sheet_range, db_id):
        print("Syncing from Notion to Google Sheet...")
        notion_properties = self.notion_client_wrapper.get_database_properties(db_id)
        headers = list(notion_properties.keys())
        headers.reverse()
        notion_data = self.notion_client_wrapper.get_notion_data(db_id, headers, notion_properties)
        
        if notion_data:
            # Get existing formulas to preserve them
            formula_data = self.google_sheets_client.get_sheet_data(spreadsheet_id, sheet_range, render_option='FORMULA')
            self.google_sheets_client.update_sheet_with_formatting(spreadsheet_id, sheet_range, notion_data, notion_properties, formula_data)

    def _detect_and_update_notion_schema(self, db_id, sheet_grid_data):
        # This is a complex operation, for now we will just log what we would do
        logging.info("Schema detection and update from sheet to Notion is not yet implemented.")

    def _process_sheet_data_for_notion(self, sheet_grid_data, notion_properties):
        if not sheet_grid_data or 'sheets' not in sheet_grid_data or not sheet_grid_data['sheets']:
            return []
        
        rowData = sheet_grid_data['sheets'][0]['data'][0].get('rowData', [])
        processed_data = []

        for row in rowData:
            processed_row = []
            if 'values' in row:
                for cell in row['values']:
                    if 'effectiveValue' in cell:
                        if 'numberValue' in cell['effectiveValue']:
                            processed_row.append(cell['effectiveValue']['numberValue'])
                        elif 'stringValue' in cell['effectiveValue']:
                            processed_row.append(cell['effectiveValue']['stringValue'])
                        elif 'boolValue' in cell['effectiveValue']:
                            processed_row.append(cell['effectiveValue']['boolValue'])
                        else:
                            processed_row.append(cell.get('formattedValue', ''))
                    else:
                        processed_row.append(cell.get('formattedValue', ''))
            processed_data.append(processed_row)
        
        return processed_data

    def _sync_sheet_to_notion(self, spreadsheet_id, sheet_range, db_id):
        print("Syncing from Google Sheet to Notion...")
        sheet_grid_data = self.google_sheets_client.get_sheet_grid_data(spreadsheet_id, sheet_range)
        
        self._detect_and_update_notion_schema(db_id, sheet_grid_data)
        
        notion_properties = self.notion_client_wrapper.get_database_properties(db_id)
        processed_data = self._process_sheet_data_for_notion(sheet_grid_data, notion_properties)

        if processed_data:
            self.notion_client_wrapper.notion_upsert(processed_data, db_id, notion_properties)

    def run_sync_cycle(self):
        """
        Runs one full sync cycle for all pairs defined in the config file.
        """
        spreadsheet_id = self.config['SAMPLE_SPREADSHEET_ID']
        for pair in self.config['SYNC_PAIRS']:
            sheet_range, db_id, priority = pair['RANGE'], pair['DATABASE_ID'], pair['PRIORITY']
            print(f"Starting Sync | Range: {sheet_range} | DB: {db_id} | Priority: {priority}")

            try:
                if priority == 'notion':
                    self._sync_notion_to_sheet(spreadsheet_id, sheet_range, db_id)
                    print("Waiting 1 second for calculations...")
                    time.sleep(1)
                    self._sync_sheet_to_notion(spreadsheet_id, sheet_range, db_id)

                elif priority == 'sheet':
                    self._sync_sheet_to_notion(spreadsheet_id, sheet_range, db_id)
                else:
                    print(f"Unknown priority '{priority}'. Skipping.")
            
            except Exception as e:
                print(f"An error occurred with sync pair (Range: {sheet_range}, DB: {db_id}). See sync_errors.log for details.")
                logging.exception(f"Failed to sync pair (Range: {sheet_range}, DB: {db_id})")

            print("Sync finished for this pair. \n")