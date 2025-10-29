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

    def _sync_sheet_to_notion(self, spreadsheet_id, sheet_range, db_id):
        print("Syncing from Google Sheet to Notion...")
        sheet_data = self.google_sheets_client.get_sheet_data(
            spreadsheet_id, 
            sheet_range, 
            render_option='FORMATTED_VALUE'
        )
        
        if sheet_data:
            notion_properties = self.notion_client_wrapper.get_database_properties(db_id)
            self.notion_client_wrapper.notion_upsert(sheet_data, db_id, notion_properties)

    def _sync_calculator_mode(self, spreadsheet_id, sheet_range, db_id):
        print("Running in Calculator Mode...")
        # Add a delay to allow Notion to finalize calculations before fetching data.
        print("Waiting 2 seconds for Notion calculations...")
        time.sleep(2)

        sheet_name = sheet_range.split('!')[0]
        header_range = f"{sheet_name}!1:1"
        sheet_headers_data = self.google_sheets_client.get_sheet_data(spreadsheet_id, header_range)
        if not sheet_headers_data:
            print("Could not read headers from the sheet. Skipping calculator mode.")
            return
        sheet_headers = sheet_headers_data[0]

        replace_col_indices = [i for i, h in enumerate(sheet_headers) if h.endswith(" [replace]")]
        notion_target_headers = [h.removesuffix(" [replace]") if h.endswith(" [replace]") else h for h in sheet_headers]

        notion_properties = self.notion_client_wrapper.get_database_properties(db_id)
        notion_data = self.notion_client_wrapper.get_notion_data(db_id, notion_target_headers, notion_properties)

        if notion_data:
            formula_data = self.google_sheets_client.get_sheet_data(spreadsheet_id, sheet_range, render_option='FORMULA')
            self.google_sheets_client.update_sheet_with_formatting(
                spreadsheet_id, sheet_range, notion_data, notion_properties, formula_data,
                ignore_col_indices=replace_col_indices
            )

        print("Waiting 1 second for calculations...")
        time.sleep(1)

        self._sync_sheet_to_notion(spreadsheet_id, sheet_range, db_id)

    def run_sync_for_pair(self, pair):
        """
        Runs a sync for a single pair defined in the config file.
        """
        job_name = pair.get('NAME', pair.get('RANGE'))
        print(f"Starting Sync for '{job_name}'...")
        
        spreadsheet_id = self.config['SAMPLE_SPREADSHEET_ID']
        sheet_range, db_id, priority = pair['RANGE'], pair['DATABASE_ID'], pair['PRIORITY']

        try:
            if priority == 'notion':
                self._sync_notion_to_sheet(spreadsheet_id, sheet_range, db_id)
                print("Waiting 1 second for calculations...")
                time.sleep(1)
                self._sync_sheet_to_notion(spreadsheet_id, sheet_range, db_id)
            elif priority == 'sheet':
                self._sync_sheet_to_notion(spreadsheet_id, sheet_range, db_id)
            elif priority == 'calculator':
                self._sync_calculator_mode(spreadsheet_id, sheet_range, db_id)
            else:
                print(f"Unknown priority '{priority}' for job '{job_name}'. Skipping.")
        
        except Exception as e:
            print(f"An error occurred with job '{job_name}' (Range: {sheet_range}, DB: {db_id}). See sync_errors.log for details.")
            logging.exception(f"Failed to sync job '{job_name}' (Range: {sheet_range}, DB: {db_id})")
            return # Stop further execution for this pair if an error occurs

        print(f"Sync finished for job '{job_name}'. \n")