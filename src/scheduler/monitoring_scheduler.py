import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    def __init__(self, config_loader, monitor_function):
        self.config_loader = config_loader
        self.monitor_function = monitor_function # This function will be called by jobs
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
        Adds monitoring jobs to the scheduler based on configured frequencies.
        This is a placeholder and would typically load forms from the DB
        and add specific jobs for each.
        """
        logger.info("Adding monitoring jobs (placeholder).")
        # Example: Add a daily job to run monitor_all_forms
        # self.scheduler.add_job(self.monitor_function, 'interval', days=1, id='full_monitor_job', replace_existing=True)
        # For a real system, you'd iterate through forms and add jobs based on form.check_frequency
        pass

    def get_scheduler_info(self):
        return {
            'running': self.is_running(),
            'jobs': [str(job) for job in self.scheduler.get_jobs()]
        }