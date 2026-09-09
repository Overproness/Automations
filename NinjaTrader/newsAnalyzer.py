import requests
import json
from datetime import datetime
import pytz
import time

def get_forex_factory_calendar():
    url = "https://www.jblanked.com/news/api/forex-factory/calendar/today/"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Api-Key "
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the JSON response
        data = response.json()
        return data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def convert_time_to_local(utc_time_str):
    # Parse the UTC time string
    utc_time = datetime.strptime(utc_time_str, "%Y.%m.%d %H:%M:%S")
    
    # Set the timezone to UTC
    utc_time = pytz.utc.localize(utc_time)
    
    # Convert to local timezone
    local_timezone = datetime.now().astimezone().tzinfo
    local_time = utc_time.astimezone(local_timezone)
    
    return local_time

def is_upcoming_event(event_time):
    now = datetime.now(pytz.utc)
    return event_time > now

def main():
    # Fetch calendar data
    data = get_forex_factory_calendar()
    
    if not data:
        print("No data received or error occurred.")
        return
    
    print("Upcoming Strong Economic Events (Local Time):")
    print("-" * 80)
    print(f"{'Event Name':<40} {'Currency':<10} {'Local Time':<25} {'Forecast':<10}")
    print("-" * 80)
    
    # Current time for filtering upcoming events
    now = datetime.now(pytz.utc)
    
    # Track if we found any upcoming strong events
    found_events = False
    
    for event in data:
        # Check if the event has strong data
        if event.get("Strength") == "Strong Data":
            # Parse the event time
            event_time_str = event.get("Date")
            event_time = datetime.strptime(event_time_str, "%Y.%m.%d %H:%M:%S")
            event_time = pytz.utc.localize(event_time)
            
            # Check if the event is upcoming
            if is_upcoming_event(event_time):
                found_events = True
                
                # Convert to local time
                local_time = convert_time_to_local(event_time_str)
                
                # Format and print the event details
                name = event.get("Name", "N/A")
                currency = event.get("Currency", "N/A")
                forecast = event.get("Forecast", "N/A")
                
                print(f"{name[:38]:<40} {currency:<10} {local_time.strftime('%Y-%m-%d %H:%M:%S %Z'):<25} {forecast:<10}")
    
    if not found_events:
        print("No upcoming strong economic events for today.")

if __name__ == "__main__":
    main()