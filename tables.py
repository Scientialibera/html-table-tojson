import html2text
import json
from bs4 import BeautifulSoup

class HTMLTableToJsonConverter:
    def __init__(self):
        self.text_maker = html2text.HTML2Text()
        self.text_maker.ignore_links = False
        self.text_maker.ignore_images = True
        self.text_maker.ignore_emphasis = False
        self.text_maker.body_width = 0

    def convert_html_table_to_json(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        for table in tables:
            try:
                if self.is_horizontal(table):
                    json_data = self.convert_row_header_table_to_json(table)
                else:
                    rows = table.find_all('tr')
                    header_rows_count = self.count_header_rows(rows)
                    if self.is_table_complex(rows):
                        normalized_grid = self.normalize_table(rows)
                        json_data = self.convert_normalized_table_to_json(normalized_grid, header_rows_count)
                    else:
                        json_data = self.simple_table_to_json(rows)

                if not self.is_conversion_result_valid(json_data):
                    raise self.TableConversionError("Invalid table data detected.")

                pre_tag = soup.new_tag("pre")
                pre_tag.string = json.dumps(json_data, ensure_ascii=False, indent=4)
                table.replace_with(pre_tag)
            except Exception as e:
                print(f"Failed to process table due to error: {e}")
                continue

        return str(soup)

    def is_conversion_result_valid(self, json_data):
        if isinstance(json_data, list) and any(isinstance(item, dict) and not item for item in json_data):
            return False
        return True

    def normalize_table(self, rows):
        max_cols = 0
        for row in rows:
            col_count = sum(int(cell.get('colspan', 1)) for cell in row.find_all(['td', 'th']))
            max_cols = max(max_cols, col_count)
        grid = [['' for _ in range(max_cols)] for _ in rows]
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            col_index = 0
            for cell in cells:
                # Convert HTML content within the cell to Markdown
                content = self.convert_html_to_markdown(cell.decode_contents())
                colspan = int(cell.get('colspan', 1))
                rowspan = int(cell.get('rowspan', 1))
                while grid[i][col_index] != '':
                    col_index += 1
                for d_row in range(rowspan):
                    for d_col in range(colspan):
                        if i + d_row < len(grid) and col_index + d_col < len(grid[i + d_row]):
                            grid[i + d_row][col_index + d_col] = content
                col_index += colspan
        return grid

    def convert_normalized_table_to_json(self, grid, header_rows_count):
        headers = grid[:header_rows_count]
        data_rows = grid[header_rows_count:]
        json_data = []
        for row_data in data_rows:
            row_dict = {}
            for col_idx, data in enumerate(row_data):
                header_path = [headers[level][col_idx] for level in range(header_rows_count)]
                if len(set(header_path)) == 1:
                    row_dict[header_path[0]] = data
                else:
                    nested_dict = row_dict
                    for header in header_path[:-1]:
                        if header not in nested_dict:
                            nested_dict[header] = {}
                        nested_dict = nested_dict[header]
                    nested_dict[header_path[-1]] = data
            json_data.append(row_dict)
        return json_data

    def is_table_complex(self, rows):
        for row in rows[1:]:
            if any(cell for cell in row.find_all(['td', 'th']) if cell.get('colspan') or cell.get('rowspan')):
                return True
        return False

    def count_header_rows(self, rows):
        """
        Count the number of header rows in the table.
        Now uses `find_header_rows` to accommodate tables with 'table-header' class.
        """
        header_rows = self.find_header_rows(rows)
        return len(header_rows)

    def simple_table_to_json(self, rows):
        """
        Converts a simple table (without colspan or rowspan in data rows) to JSON.
        Updated to support 'table-header' class for headers.
        """
        json_data = []
        header_rows = self.find_header_rows(rows)
        headers = []
        for header_row in header_rows:
            headers.extend([self.convert_html_to_markdown(cell.decode_contents()) for cell in header_row.find_all(['td', 'th'])])
        
        data_rows = rows[len(header_rows):]  # Skip the header rows to get to the data rows
        for row in data_rows:
            cells = row.find_all('td')
            row_dict = {header: self.convert_html_to_markdown(cell.decode_contents()) for header, cell in zip(headers, cells)}
            json_data.append(row_dict)
        
        return json_data
    
    def convert_html_to_markdown(self, html_content):
        return self.text_maker.handle(html_content).strip()
    
    def get_max_columns(self, rows):
        max_cols = 0
        for row in rows:
            col_count = sum(int(cell.get('colspan', 1)) for cell in row.find_all(['td', 'th']))
            max_cols = max(max_cols, col_count)
        return max_cols

    def count_column_headers(self, rows):
        headers_count = 0
        for row in rows:
            if row.find('th'):
                headers_count += 1
            else:
                break
        return headers_count

    def is_horizontal(self, html_content):
        # Parse the HTML content if it's not already a BeautifulSoup object
        if isinstance(html_content, str):
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
        else:
            # Assuming html_content is already a BeautifulSoup 'table' object
            table = html_content
        
        rows = table.find_all('tr')
        total_rows = len(rows)
        max_columns = self.get_max_columns(rows)
        
        first_row_headers = len(rows[0].find_all('th')) if rows else 0
        first_column_headers = sum(1 for row in rows if row.find('th', recursive=False))
        
        is_table_horizontal = first_column_headers == total_rows
        is_table_vertical = first_row_headers == max_columns
        
        return is_table_horizontal

    def convert_row_header_table_to_json(self, table):
        table = table
        rows = table.find_all('tr')

        # Determining the number of columns based on the maximum number of cells in a row
        max_columns = max(len(row.find_all(['th', 'td'])) for row in rows)

        # Initializing a list to hold each column's data as a dictionary
        json_data = []

        # For each column, excluding the first one which contains headers
        for col_idx in range(1, max_columns):
            column_data = {}
            for row in rows:
                cells = row.find_all(['th', 'td'])
                # Making sure there is a header and a cell for the current column
                if len(cells) > col_idx:
                    # Using the header (first cell) as key, and the cell in the current column as value
                    header = cells[0].get_text(strip=True)
                    value = cells[col_idx].get_text(strip=True)
                    column_data[header] = value
            json_data.append(column_data)

        return json_data
    
    def find_header_rows(self, rows):
        """
        Identify header rows either by `th` tags or by `tr` with a `table-header` class.
        """
        header_rows = []
        for row in rows:
            if row.find('th') or 'table-header' in row.get('class', []):
                header_rows.append(row)
            else:
                break  # Assuming headers are always at the top
        return header_rows