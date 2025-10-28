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
        handling various property types, including formulas, rollups, and relations.
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
                if prop_name == 'ID':
                    row.append(page['id'])
                    continue

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
                    elif prop_type == 'formula':
                        formula_result = prop_data.get('formula')
                        if formula_result:
                            result_type = formula_result.get('type')
                            if result_type == 'number':
                                content = formula_result.get('number') if formula_result.get('number') is not None else '[Null Number]'
                            elif result_type == 'string' and formula_result.get('string') is not None:
                                content = formula_result['string']
                            elif result_type == 'boolean' and formula_result.get('boolean') is not None:
                                content = formula_result['boolean']
                            elif result_type == 'date' and formula_result.get('date'):
                                content = formula_result['date']['start']
                            elif result_type == 'error':
                                content = f"[Formula Error: {formula_result.get('error')}]"
                            else:
                                content = "[Unsupported Formula Result]"
                    elif prop_type == 'rollup':
                        rollup_obj = prop_data.get('rollup')
                        if rollup_obj:
                            result_type = rollup_obj.get('type')
                            if result_type == 'number':
                                content = rollup_obj.get('number') if rollup_obj.get('number') is not None else '[Null Number]'
                            elif result_type == 'string' and rollup_obj.get('string') is not None:
                                content = rollup_obj['string']
                            elif result_type == 'date' and rollup_obj.get('date'):
                                content = rollup_obj['date']['start']
                            elif result_type == 'array':
                                content = "[Rollup Array]"
                            else:
                                content = "[Unsupported Rollup Result]"
                    elif prop_type == 'relation' and prop_value:
                        related_page_titles = []
                        for item in prop_value:
                            try:
                                related_page_id = item['id']
                                related_page = self.client.pages.retrieve(page_id=related_page_id)
                                for prop in related_page['properties'].values():
                                    if prop['type'] == 'title' and prop['title']:
                                        related_page_titles.append(prop['title'][0]['text']['content'])
                                        break
                            except Exception as e:
                                logging.warning(f"Could not retrieve title for related page {item.get('id')}: {e}")
                                related_page_titles.append(item.get('id', ''))
                        content = ', '.join(related_page_titles)

                row.append(content)
            data_grid.append(row)
        return data_grid

    def _are_properties_different(self, new_props, existing_props, schema):
        """Compares new and existing properties to see if an update is needed."""
        for prop_name, new_value_obj in new_props.items():
            prop_type = schema[prop_name]['type']
            existing_value_obj = existing_props.get(prop_name)

            if not existing_value_obj:
                return True # Property didn't exist before

            if prop_type == 'rich_text' or prop_type == 'title':
                new_text = new_value_obj[prop_type][0]['text']['content']
                old_text = existing_value_obj[prop_type][0]['text']['content'] if existing_value_obj[prop_type] else ""
                if new_text != old_text:
                    return True
            elif prop_type == 'number':
                new_num = new_value_obj['number']
                old_num = existing_value_obj['number']
                if new_num != old_num:
                    return True
            elif prop_type == 'checkbox':
                new_bool = new_value_obj['checkbox']
                old_bool = existing_value_obj['checkbox']
                if new_bool != old_bool:
                    return True
            elif prop_type == 'select':
                new_option_name = new_value_obj['select']['name']
                old_option = existing_value_obj['select']
                old_option_name = old_option['name'] if old_option else None
                if new_option_name != old_option_name:
                    return True
            elif prop_type == 'multi_select':
                new_options = {opt['name'] for opt in new_value_obj['multi_select']}
                old_options = {opt['name'] for opt in existing_value_obj['multi_select']}
                if new_options != old_options:
                    return True
        return False

    def notion_upsert(self, data, database_id, notion_properties):
        """
        Performs an intelligent "upsert" in Notion. If an 'ID' column is present,
        it will use the page ID to update existing pages. Otherwise, it falls back
        to matching by title to update or create pages.
        """
        if not data or len(data) < 2: return

        headers, data_rows = data[0], data[1:]
        
        all_existing_pages = self.client.databases.query(database_id=database_id)['results']

        # Decide which mapping to use: ID-based or Title-based
        try:
            id_column_index = headers.index('ID')
            id_to_page = {p['id']: p for p in all_existing_pages}
            print("Using 'ID' column for updates.")
        except ValueError:
            id_column_index = -1
            title_property_name = headers[0]
            title_to_page = {
                p['properties'][title_property_name]['title'][0]['text']['content']: p
                for p in all_existing_pages if p['properties'].get(title_property_name, {}).get('title')
            }
            print("No 'ID' column found. Using title for upserts.")

        for row_data in reversed(data_rows):
            if not row_data or not row_data[0]: continue

            new_properties = {}
            page_id_to_update = None

            # Build the properties object from the sheet data
            for i, header in enumerate(headers):
                target_header = header.removesuffix(" [replace]") if header.endswith(" [replace]") else header

                if target_header not in notion_properties or target_header == 'ID': continue
                
                value = row_data[i] if i < len(row_data) else ""
                prop_type = notion_properties[target_header]['type']
                prop_value = None

                if prop_type == 'title':
                    prop_value = {'title': [{'text': {'content': str(value)}}]}
                elif prop_type == 'number':
                    try:
                        num_format = notion_properties[target_header]['number']['format']
                        cleaned_value = str(value).strip()
                        
                        if num_format in ['dollar', 'euro']:
                            cleaned_value = cleaned_value.replace('$', '').replace('€', '').replace(',', '')
                        elif num_format == 'percent':
                            cleaned_value = cleaned_value.replace('%', '')
                        else: # number, number_with_commas
                            cleaned_value = cleaned_value.replace(',', '')

                        num = float(cleaned_value)

                        if num_format == 'percent':
                            num /= 100.0

                        prop_value = {'number': num}
                    except (ValueError, TypeError, KeyError):
                        pass
                elif prop_type == 'rich_text':
                    prop_value = {'rich_text': [{'text': {'content': str(value)}}]}
                elif prop_type == 'select':
                    if value in [opt['name'] for opt in notion_properties[target_header]['select']['options']]:
                        prop_value = {'select': {'name': str(value)}}
                elif prop_type == 'multi_select':
                    values = [v.strip() for v in str(value).split(',') if v.strip()]
                    prop_value = {'multi_select': [{'name': v} for v in values]} if values else {'multi_select': []}
                elif prop_type == 'checkbox':
                    if str(value).upper() == 'TRUE': prop_value = {'checkbox': True}
                    elif str(value).upper() == 'FALSE': prop_value = {'checkbox': False}

                if prop_value is not None:
                    new_properties[target_header] = prop_value

            # Decide whether to update or create
            existing_page = None
            if id_column_index != -1:
                page_id = row_data[id_column_index] if id_column_index < len(row_data) else None
                if page_id and page_id in id_to_page:
                    existing_page = id_to_page[page_id]
            else:
                title_value = row_data[0]
                if title_value in title_to_page:
                    existing_page = title_to_page[title_value]

            if existing_page:
                if self._are_properties_different(new_properties, existing_page['properties'], notion_properties):
                    print(f"Updating page: {existing_page['id']}")
                    self.client.pages.update(page_id=existing_page['id'], properties=new_properties)
                else:
                    print(f"Skipping unchanged page: {existing_page['id']}")
            else:
                # Only create if we are in title-matching mode and the title is not empty
                if id_column_index == -1 and row_data[0]:
                    print(f"Creating new page: {row_data[0]}")
                    self.client.pages.create(parent={'database_id': database_id}, properties=new_properties)
