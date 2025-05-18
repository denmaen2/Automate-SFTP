#!/bin/bash
# Script to run the VM File Exchange Monitor directly with Python

# Check if virtual environment exists
if [ ! -d "vm_monitor_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv vm_monitor_env
    
    # Activate virtual environment
    source vm_monitor_env/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install flask redis pandas plotly apscheduler flask-cors gunicorn fakeredis
else
    # Activate virtual environment
    source vm_monitor_env/bin/activate
fi

# Make sure sample data exists
if [ ! -d "exchange_results" ] || [ -z "$(ls -A exchange_results 2>/dev/null)" ]; then
    echo "Creating sample data..."
    mkdir -p exchange_results/ubuntu-server-1/logs
    mkdir -p exchange_results/ubuntu-server-2/logs
    mkdir -p exchange_results/ubuntu-server-3/logs
    
    # Create sample files
    for server in ubuntu-server-1 ubuntu-server-2 ubuntu-server-3; do
        echo "timestamp,hostname,action,target_servers,file,status" > exchange_results/$server/logs/history.csv
        echo "2024-05-01 12:30:45,$server,sent,ubuntu-server-2,status_${server}_20240501_123045.txt,success" >> exchange_results/$server/logs/history.csv
        echo "2024-05-01 12:50:10,$server,sent,ubuntu-server-3,status_${server}_20240501_125010.txt,success" >> exchange_results/$server/logs/history.csv
        
        echo "Received Files Summary for $server" > exchange_results/$server/logs/received_summary.txt
        echo "Generated: 2024-05-01 13:00:00" >> exchange_results/$server/logs/received_summary.txt
        echo "=======================================" >> exchange_results/$server/logs/received_summary.txt
        echo "" >> exchange_results/$server/logs/received_summary.txt
        echo "Files Received:" >> exchange_results/$server/logs/received_summary.txt
        echo "- from_ubuntu-server-2_20240501_123045.txt (Size: 1024 bytes, Date: 2024-05-01 12:31:10)" >> exchange_results/$server/logs/received_summary.txt
        echo "- from_ubuntu-server-3_20240501_125112.txt (Size: 1024 bytes, Date: 2024-05-01 12:52:30)" >> exchange_results/$server/logs/received_summary.txt
        echo "" >> exchange_results/$server/logs/received_summary.txt
        echo "Total Files: 2" >> exchange_results/$server/logs/received_summary.txt
    done
fi

# Run the application
echo "Starting VM File Exchange Monitor..."
echo "Access the dashboard at: http://localhost:5000"
echo "Press Ctrl+C to stop the application"
echo ""

python app_simple/app.py
