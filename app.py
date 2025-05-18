import os
import json
import time
import redis
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from data_parser import parse_exchange_data
from data_exporter import DataExporter

app = Flask(__name__)

# Redis configuration
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Update interval (default: 6 hours)
UPDATE_INTERVAL = int(os.environ.get('UPDATE_INTERVAL', 21600))

def update_database():
    """Parse the exchange data and update Redis database"""
    try:
        app.logger.info(f"Starting database update at {datetime.now()}")
        
        # Parse data from exchange_results directory
        exchange_data = parse_exchange_data('/app/exchange_results')
        
        # Update last refresh timestamp
        redis_client.set('last_update', int(time.time()))
        
        # Store parsed data in Redis
        redis_client.set('exchange_data', json.dumps(exchange_data))
        
        # Store individual server data
        for server, data in exchange_data['servers'].items():
            redis_client.set(f'server:{server}', json.dumps(data))
        
        app.logger.info(f"Database update completed at {datetime.now()}")
        return True
    except Exception as e:
        app.logger.error(f"Error updating database: {str(e)}")
        return False

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """Get all exchange data"""
    data = redis_client.get('exchange_data')
    if data:
        return jsonify(json.loads(data))
    else:
        # Initial load if data doesn't exist
        update_database()
        data = redis_client.get('exchange_data')
        return jsonify(json.loads(data) if data else {"error": "No data available"})

@app.route('/api/server/<server_name>')
def get_server_data(server_name):
    """Get data for a specific server"""
    data = redis_client.get(f'server:{server_name}')
    if data:
        return jsonify(json.loads(data))
    else:
        return jsonify({"error": f"No data found for server {server_name}"})

@app.route('/api/update', methods=['POST'])
def trigger_update():
    """Manually trigger a database update"""
    success = update_database()
    return jsonify({"success": success, "timestamp": int(time.time())})

@app.route('/api/status')
def get_status():
    """Get the current status including last update time"""
    last_update = redis_client.get('last_update')
    
    return jsonify({
        "last_update": int(last_update) if last_update else None,
        "last_update_formatted": datetime.fromtimestamp(int(last_update)).strftime('%Y-%m-%d %H:%M:%S') if last_update else "Never"
    })

@app.route('/api/export/<format>')
def export_data(format):
    """Export data in the specified format"""
    # Get the data
    data_json = redis_client.get('exchange_data')
    if not data_json:
        return jsonify({"error": "No data available for export"})
    
    data = json.loads(data_json)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        if format == 'csv':
            # Export as CSV
            output = DataExporter.export_csv(data)
            return output, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=exchange_data_{timestamp}.csv'
            }
        
        elif format == 'json':
            # Export as JSON
            return jsonify(data)
        
        elif format == 'excel':
            # Export as Excel
            export_dir = '/app/exports'
            os.makedirs(export_dir, exist_ok=True)
            filename = f"{export_dir}/exchange_data_{timestamp}.xlsx"
            
            file_path = DataExporter.export_excel(data, filename)
            return send_file(file_path, as_attachment=True)
        
        elif format == 'html':
            # Export as HTML report
            html = DataExporter.export_html_report(data)
            return html, 200, {'Content-Type': 'text/html'}
        
        else:
            return jsonify({"error": f"Unsupported export format: {format}"})
    
    except Exception as e:
        app.logger.error(f"Export error: {str(e)}")
        return jsonify({"error": f"Export failed: {str(e)}"})

if __name__ == '__main__':
    # Initialize scheduler for periodic updates
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_database, 'interval', seconds=UPDATE_INTERVAL)
    scheduler.start()
    
    # Initial data load
    if not redis_client.exists('exchange_data'):
        update_database()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('DEBUG', 'False').lower() == 'true')
