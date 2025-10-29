# scheduler.py
import time
import calendar
from datetime import datetime

class Scheduler:
    """
    Manages scheduling and running of sync jobs based on per-job configurations.
    """
    def __init__(self, syncer):
        self.syncer = syncer
        self.jobs = self.syncer.config.get('SYNC_PAIRS', [])
        # Use a unique identifier for each job for tracking last run times
        self.last_run_times = {f"{job.get('DATABASE_ID')}-{job.get('RANGE')}": None for job in self.jobs}

    def _is_due(self, job, now):
        """
        Checks if a job is due to run based on its schedule.
        """
        # Support both 'REPEAT' and the user's typo 'REAPEAT' for robustness.
        is_repeat = job.get('REPEAT', False) or job.get('REAPEAT', False)
        if not is_repeat:
            return False

        interval = job.get('INTERVAL')
        if not interval:
            return False

        last_run = self.last_run_times[f"{job.get('DATABASE_ID')}-{job.get('RANGE')}"]

        try:
            if interval == 'hour':
                run_minute = int(job['REPEAT_HOUR'])
                if now.minute == run_minute:
                    if last_run is None or (now - last_run).total_seconds() > 60:
                        return True
            
            elif interval == 'day':
                run_time_str = job['REPEAT_DAY'] # "18:01"
                run_hour, run_minute = map(int, run_time_str.split(':'))
                if now.hour == run_hour and now.minute == run_minute:
                    if last_run is None or (now - last_run).days >= 1:
                        return True

            elif interval == 'week':
                run_time_str, run_day_str = job['REPEAT_WEEK'].split('-') # "00:01-Monday"
                run_hour, run_minute = map(int, run_time_str.split(':'))
                # Monday is 0, Sunday is 6
                weekday_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
                run_weekday = weekday_map[run_day_str.lower()]
                if now.weekday() == run_weekday and now.hour == run_hour and now.minute == run_minute:
                    if last_run is None or (now - last_run).days >= 7:
                        return True

            elif interval == 'month':
                run_time_str, run_day_of_month_str = job['REPEAT_MONTH'].split('-') # "11:59-31"
                run_hour, run_minute = map(int, run_time_str.split(':'))
                run_day_of_month = int(run_day_of_month_str)

                # Get the last day of the current month
                _, last_day_of_current_month = calendar.monthrange(now.year, now.month)

                # Determine the target day for this month
                target_run_day = min(run_day_of_month, last_day_of_current_month)

                if now.day == target_run_day and now.hour == run_hour and now.minute == run_minute:
                    if last_run is None or (now.month != last_run.month or now.year != last_run.year):
                        return True

            elif interval == 'year':
                run_time_str, run_day, run_month = job['REPEAT_YEAR'].split('-') # "00:01-31-12"
                run_hour, run_minute = map(int, run_time_str.split(':'))
                if now.month == int(run_month) and now.day == int(run_day) and now.hour == run_hour and now.minute == run_minute:
                    if last_run is None or now.year != last_run.year:
                        return True

        except (ValueError, KeyError) as e:
            print(f"Error parsing schedule for job {job['RANGE']}: {e}")
            return False
            
        return False

    def run(self):
        """
        Starts the main scheduler loop.
        """
        # First, run all jobs once that are not configured to repeat.
        print("Performing initial run for all non-repeating jobs...")
        for job in self.jobs:
            is_repeat = job.get('REPEAT', False) or job.get('REAPEAT', False)
            job_name = job.get('NAME', job.get('RANGE'))
            if not is_repeat:
                try:
                    self.syncer.run_sync_for_pair(job)
                except Exception as e:
                    print(f"Error running initial sync for job '{job_name}': {e}")

        # Check if there are any repeating jobs to schedule
        repeating_jobs = [job for job in self.jobs if job.get('REPEAT', False) or job.get('REAPEAT', False)]
        if not repeating_jobs:
            print("No repeating jobs configured. Exiting.")
            return

        print("Scheduler started. Checking for due jobs...")
        while True:
            now = datetime.now()
            for job in repeating_jobs:
                job_name = job.get('NAME', job.get('RANGE'))
                if self._is_due(job, now):
                    print(f"Scheduled job '{job_name}' is due. Running sync.")
                    try:
                        self.syncer.run_sync_for_pair(job)
                        self.last_run_times[f"{job.get('DATABASE_ID')}-{job.get('RANGE')}"] = now
                    except Exception as e:
                        print(f"Error running scheduled job '{job_name}': {e}")
            
            # Sleep for 60 seconds before checking again
            time.sleep(60)
