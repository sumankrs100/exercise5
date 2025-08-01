#!/usr/bin/env python3
"""
Daily Task Scheduler Module

This module provides functionality to schedule a Python function to run
every day at 4:00 AM using the python-crontab library.
"""

import os
import sys
from crontab import CronTab
from datetime import datetime


class DailyScheduler:
    def __init__(self, user=None):
        """
        Initialize the scheduler with a specific user or current user.
        
        Args:
            user (str, optional): Username for the crontab. If None, uses current user.
        """
        if user:
            self.cron = CronTab(user=user)
        else:
            self.cron = CronTab(user=True)  # Current user's crontab
    
    def my_daily_function(self):
        """
        The function that will be executed daily at 4:00 AM.
        Replace this with your actual task logic.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"Daily task executed at {timestamp}\n"
        
        # Log to a file
        log_file = os.path.expanduser("~/daily_task.log")
        with open(log_file, "a") as f:
            f.write(log_message)
        
        print(f"Daily task completed at {timestamp}")
        
        # Add your actual task logic here
        # For example:
        # - Database maintenance
        # - Send daily reports
        # - Clean temporary files
        # - Backup data
        
    def schedule_daily_task(self, job_comment="Daily Python Task"):
        """
        Schedule the daily function to run at 4:00 AM every day.
        
        Args:
            job_comment (str): Comment to identify the cron job
        
        Returns:
            bool: True if scheduled successfully, False otherwise
        """
        try:
            # Get the path to the current Python interpreter
            python_path = sys.executable
            
            # Get the path to this script
            script_path = os.path.abspath(__file__)
            
            # Create the command to run
            command = f"{python_path} {script_path} --run-task"
            
            # Remove any existing jobs with the same comment
            self.remove_scheduled_task(job_comment)
            
            # Create a new cron job
            job = self.cron.new(command=command, comment=job_comment)
            
            # Set the schedule: minute=0, hour=4, every day
            job.setall("0 4 * * *")
            
            # Validate the job
            if job.is_valid():
                # Write the crontab
                self.cron.write()
                print(f"Successfully scheduled daily task at 4:00 AM")
                print(f"Command: {command}")
                return True
            else:
                print("Invalid cron job created")
                return False
                
        except Exception as e:
            print(f"Error scheduling task: {e}")
            return False
    
    def remove_scheduled_task(self, job_comment="Daily Python Task"):
        """
        Remove the scheduled daily task.
        
        Args:
            job_comment (str): Comment to identify the cron job to remove
        
        Returns:
            bool: True if removed successfully, False otherwise
        """
        try:
            # Find and remove jobs with the specified comment
            jobs_removed = 0
            for job in self.cron:
                if job.comment == job_comment:
                    self.cron.remove(job)
                    jobs_removed += 1
            
            if jobs_removed > 0:
                self.cron.write()
                print(f"Removed {jobs_removed} scheduled task(s)")
                return True
            else:
                print("No matching scheduled tasks found")
                return False
                
        except Exception as e:
            print(f"Error removing scheduled task: {e}")
            return False
    
    def list_scheduled_tasks(self):
        """
        List all scheduled tasks in the crontab.
        """
        print("Current scheduled tasks:")
        for job in self.cron:
            print(f"  Schedule: {job.slices}")
            print(f"  Command: {job.command}")
            print(f"  Comment: {job.comment}")
            print(f"  Enabled: {job.is_enabled()}")
            print("  ---")
    
    def check_task_status(self, job_comment="Daily Python Task"):
        """
        Check if the daily task is currently scheduled.
        
        Args:
            job_comment (str): Comment to identify the cron job
        
        Returns:
            bool: True if task is scheduled, False otherwise
        """
        for job in self.cron:
            if job.comment == job_comment and job.is_enabled():
                return True
        return False


def main():
    """
    Main function to handle command line execution.
    """
    scheduler = DailyScheduler()
    
    # Check if this script is being run by cron
    if len(sys.argv) > 1 and sys.argv[1] == "--run-task":
        # Execute the daily function
        scheduler.my_daily_function()
    else:
        # Interactive mode - schedule the task
        print("Daily Task Scheduler")
        print("===================")
        
        while True:
            print("\nOptions:")
            print("1. Schedule daily task (4:00 AM)")
            print("2. Remove scheduled task")
            print("3. List all scheduled tasks")
            print("4. Check task status")
            print("5. Run task now (test)")
            print("6. Exit")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                if scheduler.schedule_daily_task():
                    print("Task scheduled successfully!")
                else:
                    print("Failed to schedule task.")
            
            elif choice == "2":
                if scheduler.remove_scheduled_task():
                    print("Task removed successfully!")
                else:
                    print("Failed to remove task.")
            
            elif choice == "3":
                scheduler.list_scheduled_tasks()
            
            elif choice == "4":
                if scheduler.check_task_status():
                    print("Daily task is currently scheduled.")
                else:
                    print("Daily task is not scheduled.")
            
            elif choice == "5":
                print("Running task now...")
                scheduler.my_daily_function()
            
            elif choice == "6":
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
