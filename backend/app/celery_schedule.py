from app.workers.cleanup_worker import cleanup_outbox_events, cleanup_galaxy_outbox
from celery import Celery

# Assuming 'app' is your main Celery application instance
# In a real setup, you'd likely import 'app' from your main celery configuration file
# e.g., from app.worker import celery_app

def setup_periodic_tasks(sender, **kwargs):
    # Execute daily at midnight
    sender.add_periodic_task(
        86400.0, 
        cleanup_outbox_events.s(), 
        name='cleanup-outbox-every-day'
    )
    
    sender.add_periodic_task(
        86400.0,
        cleanup_galaxy_outbox.s(),
        name='cleanup-galaxy-outbox-every-day'
    )
