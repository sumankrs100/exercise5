import os
import schedule
import time
from datetime import datetime

def hello_world():
    """Function to print hello world with timestamp"""
    print(f"Hello World! - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def parse_time_format(time_str):
    """Parse time string and convert to 24-hour format"""
    try:
        # Handle different formats like "7:00 AM", "9:00 PM", "07:00", etc.
        time_str = time_str.strip().upper()
        
        if 'AM' in time_str or 'PM' in time_str:
            # Parse 12-hour format
            time_obj = datetime.strptime(time_str, '%I:%M %p').time()
            return time_obj.strftime('%H:%M')
        else:
            # Assume 24-hour format
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            return time_obj.strftime('%H:%M')
    except ValueError as e:
        print(f"Error parsing time format: {e}")
        return None

def get_scheduled_time():
    """Get the scheduled time from environment variable"""
    return os.getenv('SCHEDULED_TIME', '7:00 AM')

def setup_schedule():
    """Setup the schedule based on environment variable"""
    # Clear any existing schedules
    schedule.clear()
    
    # Get time from environment variable
    env_time = get_scheduled_time()
    parsed_time = parse_time_format(env_time)
    
    if parsed_time:
        # Schedule the job
        schedule.every().day.at(parsed_time).do(hello_world)
        print(f"Scheduled daily execution at {parsed_time} (from env: {env_time})")
        return True
    else:
        print(f"Invalid time format in environment variable: {env_time}")
        return False

def check_for_time_change():
    """Check if the environment variable has changed"""
    current_jobs = schedule.jobs
    if not current_jobs:
        return True  # No jobs scheduled, need to set up
    
    # Get current scheduled time from the job
    current_scheduled_time = str(current_jobs[0].at_time)
    
    # Get time from environment variable
    env_time = get_scheduled_time()
    parsed_time = parse_time_format(env_time)
    
    if parsed_time and parsed_time != current_scheduled_time:
        print(f"Time changed from {current_scheduled_time} to {parsed_time}")
        return True
    
    return False

def main():
    """Main function to run the scheduler"""
    print("Starting dynamic scheduler...")
    print(f"Current environment time: {get_scheduled_time()}")
    
    # Initial setup
    if not setup_schedule():
        return
    
    print("Scheduler is running. Press Ctrl+C to stop.")
    print("Change the SCHEDULED_TIME environment variable to update the schedule.")
    
    try:
        while True:
            # Check if environment variable changed every minute
            if check_for_time_change():
                setup_schedule()
            
            # Run pending scheduled jobs
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\nScheduler stopped.")

if __name__ == "__main__":
    main()
