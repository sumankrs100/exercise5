#!/usr/bin/env python3
"""
Simple Python module to schedule a daily "Hello World" task at 4:00 AM using python-crontab
"""

from crontab import CronTab
from datetime import datetime
import os
import sys

def hello_world():
    """Function that prints Hello World with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Hello World! - {timestamp}")

def setup_cron_job():
    """Set up the cron job to run hello_world daily at 4:00 AM"""
    # Create a new crontab for the current user
    cron = CronTab(user=True)
    
    # Get the path to this script
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    
    # Create the command to run
    command = f'{python_path} {script_path} --run'
    
    # Check if job already exists
    existing_jobs = list(cron.find_command(command))
    if existing_jobs:
        print("Cron job already exists!")
        return
    
    # Create new cron job
    job = cron.new(command=command)
    job.setall('0 4 * * *')  # Run at 4:00 AM daily
    job.set_comment('Daily Hello World Task')
    
    # Write the crontab
    cron.write()
    print("Cron job created successfully! Will run daily at 4:00 AM")

def remove_cron_job():
    """Remove the cron job"""
    cron = CronTab(user=True)
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    command = f'{python_path} {script_path} --run'
    
    # Find and remove the job
    jobs_removed = cron.remove_all(command=command)
    if jobs_removed:
        cron.write()
        print(f"Removed {jobs_removed} cron job(s)")
    else:
        print("No matching cron jobs found")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == '--run':
            # This is called by cron to run the actual function
            hello_world()
        elif sys.argv[1] == '--setup':
            # Set up the cron job
            setup_cron_job()
        elif sys.argv[1] == '--remove':
            # Remove the cron job
            remove_cron_job()
        elif sys.argv[1] == '--test':
            # Test the function
            print("Testing hello_world function:")
            hello_world()
        else:
            print("Usage:")
            print("  python hello_scheduler.py --setup   # Set up the cron job")
            print("  python hello_scheduler.py --remove  # Remove the cron job")
            print("  python hello_scheduler.py --test    # Test the function")
            print("  python hello_scheduler.py --run     # Run the function (used by cron)")
    else:
        print("Usage:")
        print("  python hello_scheduler.py --setup   # Set up the cron job")
        print("  python hello_scheduler.py --remove  # Remove the cron job")
        print("  python hello_scheduler.py --test    # Test the function")
        print("  python hello_scheduler.py --run     # Run the function (used by cron)")
