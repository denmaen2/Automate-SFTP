def generate_time_series(servers_data):
    """
    Generate time series data for visualization
    
    Args:
        servers_data: Dictionary of server data
        
    Returns:
        dict: Time series data for sent and received files
    """
    time_series = {
        "sent": {},
        "received": {}
    }
    
    # Process sent files time series
    for server, data in servers_data.items():
        sent_by_day = defaultdict(int)
        
        for file in data["sent_files"]:
            try:
                # Parse the timestamp (format: %Y-%m-%d %H:%M:%S)
                dt = datetime.strptime(file["timestamp"], "%Y-%m-%d %H:%M:%S")
                day = dt.strftime("%Y-%m-%d")
                sent_by_day[day] += 1
            except (ValueError, KeyError):
                continue
        
        time_series["sent"][server] = dict(sent_by_day)
    
    # Process received files time series (estimated from received_files)
    for server, data in servers_data.items():
        received_by_day = defaultdict(int)
        
        for file in data["received_files"]:
            try:
                # Try to parse the date from the file info
                # This is less precise than sent data but gives an approximation
                if "date" in file:
                    # Try to parse the date (varies by format)
                    try:
                        dt = datetime.strptime(file["date"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # Try alternative format
                        dt = datetime.strptime(file["date"], "%Y-%m-%d")
                    
                    day = dt.strftime("%Y-%m-%d")
                    received_by_day[day] += 1
            except (ValueError, KeyError):
                continue
        
        time_series["received"][server] = dict(received_by_day)
    
    return time_seriesimport os
import csv
import json
import pandas as pd
from datetime import datetime
from collections import defaultdict

def parse_exchange_data(base_dir):
    """
    Parse the exchange data from each server's logs
    
    Args:
        base_dir: Base directory containing exchange_results
        
    Returns:
        dict: Structured data with all server information
    """
    result = {
        "servers": {},
        "summary": {
            "total_files_sent": 0,
            "total_files_received": 0,
            "server_ips": {}
        }
    }
    
    # Server IPs mapping from the original script
    server_ips = {
        "ubuntu-server-1": "192.168.56.101",
        "ubuntu-server-2": "192.168.56.102", 
        "ubuntu-server-3": "192.168.56.103"
    }
    
    result["summary"]["server_ips"] = server_ips
    
    # Get all server directories
    try:
        server_dirs = [d for d in os.listdir(base_dir) 
                     if os.path.isdir(os.path.join(base_dir, d)) and d.startswith('ubuntu-server')]
    except FileNotFoundError:
        # If directory doesn't exist, return empty result
        return result
    
    for server in server_dirs:
        server_data = {
            "ip": server_ips.get(server, "Unknown"),
            "sent_files": [],
            "received_files": [],
            "history": [],
            "summary": {
                "total_sent": 0,
                "total_received": 0,
                "last_exchange": None
            }
        }
        
        server_dir = os.path.join(base_dir, server)
        
        # Parse history.csv if it exists
        history_file = os.path.join(server_dir, "history.csv")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        server_data["history"].append(row)
                        
                        # Update summary based on history
                        if row["action"] == "sent":
                            server_data["sent_files"].append({
                                "timestamp": row["timestamp"],
                                "target": row["target_servers"],
                                "filename": row["file"],
                                "status": row["status"]
                            })
                            server_data["summary"]["total_sent"] += 1
                        
                        # Track the latest exchange
                        if (not server_data["summary"]["last_exchange"] or 
                            row["timestamp"] > server_data["summary"]["last_exchange"]):
                            server_data["summary"]["last_exchange"] = row["timestamp"]
            except Exception as e:
                print(f"Error parsing history for {server}: {str(e)}")
        
        # Parse received_summary.txt if it exists
        summary_file = os.path.join(server_dir, "received_summary.txt")
        if os.path.exists(summary_file):
            try:
                with open(summary_file, 'r') as f:
                    lines = f.readlines()
                    
                    # Extract received files info
                    in_files_section = False
                    for line in lines:
                        line = line.strip()
                        
                        if line.startswith("Files Received:"):
                            in_files_section = True
                            continue
                            
                        if in_files_section and line.startswith("- "):
                            # Parse the file info line
                            # Format: "- filename (Size: X bytes, Date: Y)"
                            parts = line[2:].split('(')
                            filename = parts[0].strip()
                            
                            # Extract source server from filename
                            source_server = "unknown"
                            if filename.startswith("from_") and "_" in filename:
                                source_server = filename.split("_")[1]
                            
                            file_info = {
                                "filename": filename,
                                "source": source_server,
                                "date": parts[1].split("Date:")[1].strip().rstrip(")")
                            }
                            
                            server_data["received_files"].append(file_info)
                            server_data["summary"]["total_received"] += 1
                        
                        if in_files_section and line.startswith("Total Files:"):
                            in_files_section = False
            except Exception as e:
                print(f"Error parsing received summary for {server}: {str(e)}")
        
        # Add to the result
        result["servers"][server] = server_data
        
        # Update global summary
        result["summary"]["total_files_sent"] += server_data["summary"]["total_sent"]
        result["summary"]["total_files_received"] += server_data["summary"]["total_received"]
    
    # Add calculated fields
    result["summary"]["total_exchanges"] = len(server_dirs)
    result["summary"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate time series data for visualization
    result["time_series"] = generate_time_series(result["servers"])
    
    # Generate connection matrix for visualization
    result["connection_matrix"] = generate_connection_matrix(result["servers"])
    
    return result

def generate_connection_matrix(servers_data):
    """
    Generate a connection matrix showing the file exchanges between servers
    
    Args:
        servers_data: Dictionary of server data
        
    Returns:
        dict: Connection matrix data
    """
    # Get all server names
    server_names = list(servers_data.keys())
    
    # Initialize matrix with zeros
    matrix = {}
    for source in server_names:
        matrix[source] = {}
        for target in server_names:
            matrix[source][target] = 0
    
    # Fill in the matrix based on sent files
    for source, data in servers_data.items():
        for file in data.get("sent_files", []):
            target = file.get("target")
            if target in server_names:
                matrix[source][target] += 1
    
    return {
        "servers": server_names,
        "matrix": matrix
    }
