# main.py
import time
import logging
from config_loader import ConfigLoader
from google_auth import GoogleAuth
from google_sheets_client import GoogleSheetsClient
from notion_client_wrapper import NotionClientWrapper
from data_syncer import DataSyncer

logging.basicConfig(
    filename='sync_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """
    Main function to run the synchronization script.
    """
    config_loader = ConfigLoader()
    config = config_loader.load_config()
    if not config:
        return

    google_auth = GoogleAuth(scopes=['https://www.googleapis.com/auth/spreadsheets'])
    google_creds = google_auth.get_credentials()
    
    google_sheets_client = GoogleSheetsClient(credentials=google_creds)
    notion_client_wrapper = NotionClientWrapper(auth_token=config['NOTION_INTEGRATION_TOKEN'])

    syncer = DataSyncer(config, google_sheets_client, notion_client_wrapper)

    run_repeatedly = config.get('RUN_REPEATEDLY', False)
    interval_minutes = config.get('REPEAT_INTERVAL_MINUTES', 30)

    if not run_repeatedly:
        print("Running sync once.")
        syncer.run_sync_cycle()
        print("Sync complete.")
    else:
        print(f"Starting repeated sync. Interval: {interval_minutes} minutes.")
        try:
            while True:
                syncer.run_sync_cycle()
                print(f"Sync cycle complete. Waiting for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\nScript stopped by user. Exiting.")

if __name__ == '__main__':
    main()
