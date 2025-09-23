# notion_client_wrapper.py
import logging
from notion_client import Client

class NotionClientWrapper:
    """
    A wrapper for the Notion client to handle data retrieval and updates.
    """
    def __init__(self, auth_token):
        self.client = Client(auth=auth_token)

    def get_database_properties(self, database_id):
        """
        Retrieves the properties (schema) of a Notion database.
        """
        return self.client.databases.retrieve(database_id=database_id)['properties']

    def update_database_properties(self, database_id, properties):
        """
        Updates the properties (schema) of a Notion database.
        """
        self.client.databases.update(database_id=database_id, properties=properties)

    def get_notion_data(self, database_id, expected_headers, notion_properties):
        """
        Retrieves all pages from a Notion database and formats them into a grid,
        handling various property types.
        """
        results = []
        has_more = True
        next_cursor = None
        
        while has_more:
            response = self.client.databases.query(database_id=database_id, start_cursor=next_cursor)
            results.extend(response['results'])
            has_more = response['has_more']
            next_cursor = response['next_cursor']

        results.reverse()

        data_grid = [expected_headers]
        for page in results:
            row = []
            for prop_name in expected_headers:
                prop_data = page['properties'].get(prop_name, {})
                prop_type = prop_data.get('type')
                content = ""

                if prop_type and prop_data.get(prop_type):
                    prop_value = prop_data[prop_type]
                    if prop_type == 'title' and prop_value: content = prop_value[0]['text']['content']
                    elif prop_type == 'rich_text' and prop_value: content = prop_value[0]['text']['content']
                    elif prop_type == 'number': content = prop_value
                    elif prop_type == 'checkbox': content = prop_value
                    elif prop_type == 'select' and prop_value: content = prop_value['name']
                    elif prop_type == 'multi_select': content = ', '.join([opt['name'] for opt in prop_value])
                
                row.append(content)
            data_grid.append(row)
        return data_grid

    def notion_upsert(self, data, database_id, notion_properties):
        """
        Performs an "upsert" operation in Notion, handling various data types.
        """
        if not data or len(data) < 2: return
        
        headers, data_rows, title_property_name = data[0], data[1:], data[0][0]
        
        existing_pages = self.client.databases.query(database_id=database_id)
        title_to_page_id = {
            p['properties'][title_property_name]['title'][0]['text']['content']: p['id']
            for p in existing_pages.get('results', []) if p['properties'].get(title_property_name, {}).get('title')
        }

        for row_data in reversed(data_rows):
            if not row_data: continue
            
            title_value = row_data[0]
            properties = {}

            # Handle Title Property
            properties[title_property_name] = {'title': [{'text': {'content': str(title_value)}}]}

            # Handle Other Properties
            for header, value in zip(headers[1:], row_data[1:]):
                if header not in notion_properties: continue
                
                prop_type = notion_properties[header]['type']
                prop_value = None

                if prop_type == 'number':
                    try:
                        prop_value = {'number': float(value)}
                    except (ValueError, TypeError):
                        logging.warning(f"Could not convert '{value}' to a number for property '{header}'. Skipping.")
                elif prop_type == 'rich_text':
                    prop_value = {'rich_text': [{'text': {'content': str(value)}}]}
                elif prop_type == 'select':
                    options = [opt['name'] for opt in notion_properties[header]['select']['options']]
                    if value in options:
                        prop_value = {'select': {'name': str(value)}}
                    else:
                        logging.warning(f"Value '{value}' not a valid option for select property '{header}'. Skipping.")
                elif prop_type == 'multi_select':
                    if value:
                        values = [v.strip() for v in str(value).split(',') if v.strip()]
                        if values:
                            prop_value = {'multi_select': [{'name': v} for v in values]}
                        else:
                            prop_value = {'multi_select': []}
                    else:
                        prop_value = {'multi_select': []}
                elif prop_type == 'checkbox':
                    if str(value).upper() == 'TRUE':
                        prop_value = {'checkbox': True}
                    elif str(value).upper() == 'FALSE':
                        prop_value = {'checkbox': False}
                    else:
                        logging.warning(f"Value '{value}' not a valid boolean for checkbox property '{header}'. Skipping.")

                if prop_value:
                    properties[header] = prop_value

            if title_value in title_to_page_id:
                self.client.pages.update(page_id=title_to_page_id[title_value], properties=properties)
            else:
                self.client.pages.create(parent={'database_id': database_id}, properties=properties)