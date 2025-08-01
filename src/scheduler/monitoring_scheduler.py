import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

from src.database.connection import db_session
from src.database.models import Form

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    def __init__(self, config_loader, monitor_function):
        self.config_loader = config_loader
        self.monitor_function = monitor_function # This function will be called by jobs (e.g., monitor_all_forms)
        self.scheduler = BackgroundScheduler()
        self._is_running = False
        logger.info("MonitoringScheduler initialized.")

    def start(self):
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Scheduler started.")
        else:
            logger.info("Scheduler is already running.")

    def stop(self):
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped.")
        else:
            logger.info("Scheduler is not running.")

    def is_running(self):
        return self._is_running and self.scheduler.running

    def add_monitoring_jobs(self):
        """
        Adds monitoring jobs to the scheduler based on configured frequencies for each form.
        Also adds a general fallback job.
        """
        logger.info("Adding monitoring jobs...")
        
        # Clear existing jobs to prevent duplicates on restart
        self.scheduler.remove_all_jobs()

        with db_session() as session:
            forms = session.query(Form).all()
            if not forms:
                logger.warning("No forms found in the database. Cannot add specific monitoring jobs.")
                logger.info("Adding a default daily monitoring job as a fallback.")
                self.scheduler.add_job(
                    self.monitor_function, 
                    'interval', 
                    days=1, 
                    id='default_daily_monitor', 
                    replace_existing=True,
                    next_run_time=datetime.now() + timedelta(seconds=10) # Run shortly after start
                )
                return

            for form in forms:
                job_id = f"form_monitor_{form.id}"
                frequency = form.check_frequency.lower() if form.check_frequency else 'weekly' # Default to weekly if not set

                if frequency == 'daily':
                    trigger = IntervalTrigger(days=1)
                elif frequency == 'weekly':
                    trigger = IntervalTrigger(weeks=1)
                elif frequency == 'monthly':
                    trigger = IntervalTrigger(weeks=4) # Approx monthly
                else:
                    logger.warning(f"Unknown frequency '{frequency}' for form {form.name}. Defaulting to weekly.")
                    trigger = IntervalTrigger(weeks=1)
                
                # Schedule the job to run the monitor_all_forms function
                # For more granular control, monitor_function could be a wrapper that takes form.id
                # For now, monitor_all_forms will iterate through all forms.
                self.scheduler.add_job(
                    self.monitor_function, 
                    trigger, 
                    id=job_id, 
                    replace_existing=True,
                    # Run the first job shortly after startup to ensure initial check
                    next_run_time=datetime.now() + timedelta(seconds=5) 
                )
                logger.info(f"Scheduled '{form.name}' ({form.id}) to run {frequency} with job ID: {job_id}")
        
        logger.info(f"Total jobs scheduled: {len(self.scheduler.get_jobs())}")

    def get_scheduler_info(self):
        return {
            'running': self.is_running(),
            'jobs': [str(job) for job in self.scheduler.get_jobs()]
        }