import os
import csv
import json
import pandas as pd
from datetime import datetime
from flask import send_file, Response

class DataExporter:
    """
    Utility class for exporting exchange data to various formats
    """
    
    @staticmethod
    def export_csv(data, filename=None):
        """
        Export exchange data to CSV format
        
        Args:
            data: Dictionary of exchange data
            filename: Optional filename to save to
            
        Returns:
            File path if saved, or Response object if sent directly
        """
        # Create a pandas DataFrame for server summary
        server_data = []
        for server_name, server_info in data['servers'].items():
            server_data.append({
                'hostname': server_name,
                'ip_address': server_info['ip'],
                'files_sent': server_info['summary']['total_sent'],
                'files_received': server_info['summary']['total_received'],
                'last_exchange': server_info['summary']['last_exchange']
            })
        
        df = pd.DataFrame(server_data)
        
        if filename:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_csv(filename, index=False)
            return filename
        else:
            # Return CSV as string
            return df.to_csv(index=False)
    
    @staticmethod
    def export_json(data, filename=None):
        """
        Export exchange data to JSON format
        
        Args:
            data: Dictionary of exchange data
            filename: Optional filename to save to
            
        Returns:
            File path if saved, or JSON string if no filename
        """
        if filename:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            return filename
        else:
            return json.dumps(data, indent=2)
    
    @staticmethod
    def export_excel(data, filename=None):
        """
        Export exchange data to Excel format
        
        Args:
            data: Dictionary of exchange data
            filename: Filename to save to (required for Excel)
            
        Returns:
            File path of saved Excel file
        """
        if not filename:
            filename = f"exchange_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Create Excel writer
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        
        # Create a DataFrame for server summary
        server_data = []
        for server_name, server_info in data['servers'].items():
            server_data.append({
                'hostname': server_name,
                'ip_address': server_info['ip'],
                'files_sent': server_info['summary']['total_sent'],
                'files_received': server_info['summary']['total_received'],
                'last_exchange': server_info['summary']['last_exchange']
            })
        
        server_df = pd.DataFrame(server_data)
        server_df.to_excel(writer, sheet_name='Server Summary', index=False)
        
        # Create sheets for each server's sent and received files
        for server_name, server_info in data['servers'].items():
            # Sent files
            sent_data = pd.DataFrame(server_info['sent_files'])
            if not sent_data.empty:
                sent_data.to_excel(writer, sheet_name=f'{server_name}_sent', index=False)
            
            # Received files
            received_data = pd.DataFrame(server_info['received_files'])
            if not received_data.empty:
                received_data.to_excel(writer, sheet_name=f'{server_name}_received', index=False)
        
        # Create a history sheet with all exchanges
        all_history = []
        for server_name, server_info in data['servers'].items():
            for entry in server_info.get('history', []):
                all_history.append({
                    'server': server_name,
                    **entry
                })
        
        history_df = pd.DataFrame(all_history)
        if not history_df.empty:
            history_df.to_excel(writer, sheet_name='Exchange History', index=False)
        
        # Save the Excel file
        writer.save()
        
        return filename
    
    @staticmethod
    def export_html_report(data, filename=None):
        """
        Export exchange data to a standalone HTML report
        
        Args:
            data: Dictionary of exchange data
            filename: Optional filename to save to
            
        Returns:
            File path if saved, or HTML string if no filename
        """
        # Create HTML table for server summary
        server_table = '<table border="1" class="dataframe">\n'
        server_table += '<thead><tr><th>Hostname</th><th>IP Address</th><th>Files Sent</th><th>Files Received</th><th>Last Exchange</th></tr></thead>\n'
        server_table += '<tbody>\n'
        
        for server_name, server_info in data['servers'].items():
            server_table += f'<tr><td>{server_name}</td><td>{server_info["ip"]}</td><td>{server_info["summary"]["total_sent"]}</td><td>{server_info["summary"]["total_received"]}</td><td>{server_info["summary"]["last_exchange"] or "N/A"}</td></tr>\n'
        
        server_table += '</tbody></table>\n'
        
        # Create HTML table for recent exchanges
        all_history = []
        for server_name, server_info in data['servers'].items():
            for entry in server_info.get('history', []):
                all_history.append({
                    'server': server_name,
                    **entry
                })
        
        # Sort by timestamp, most recent first
        all_history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        history_table = '<table border="1" class="dataframe">\n'
        history_table += '<thead><tr><th>Timestamp</th><th>Source</th><th>Action</th><th>Target</th><th>File</th><th>Status</th></tr></thead>\n'
        history_table += '<tbody>\n'
        
        for entry in all_history[:20]:  # Show only the 20 most recent
            history_table += f'<tr><td>{entry.get("timestamp", "")}</td><td>{entry.get("server", "")}</td><td>{entry.get("action", "")}</td><td>{entry.get("target_servers", "")}</td><td>{entry.get("file", "")}</td><td>{entry.get("status", "")}</td></tr>\n'
        
        history_table += '</tbody></table>\n'
        
        # Build the complete HTML report
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>VM File Exchange Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c5282; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th {{ background-color: #edf2f7; padding: 8px; text-align: left; }}
                td {{ padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f7fafc; }}
                .summary {{ display: flex; margin-bottom: 20px; }}
                .summary-card {{ background-color: #f7fafc; border-radius: 5px; padding: 15px; margin-right: 15px; width: 200px; }}
                .summary-card h3 {{ margin-top: 0; color: #4a5568; }}
                .summary-card p {{ font-size: 24px; font-weight: bold; color: #2b6cb0; }}
                .timestamp {{ color: #718096; font-style: italic; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>VM File Exchange Report</h1>
            <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <div class="summary-card">
                    <h3>Total Files Sent</h3>
                    <p>{data['summary']['total_files_sent']}</p>
                </div>
                <div class="summary-card">
                    <h3>Total Files Received</h3>
                    <p>{data['summary']['total_files_received']}</p>
                </div>
                <div class="summary-card">
                    <h3>Server Count</h3>
                    <p>{len(data['servers'])}</p>
                </div>
            </div>
            
            <h2>Server Summary</h2>
            {server_table}
            
            <h2>Recent Exchanges</h2>
            {history_table}
            
            <h2>About This Report</h2>
            <p>This report was generated by the VM File Exchange Monitor.</p>
        </body>
        </html>
        '''
        
        if filename:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                f.write(html)
            return filename
        else:
            return html
