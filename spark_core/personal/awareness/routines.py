import asyncio
from datetime import datetime

class RoutineManager:
    """
    Time-based automatic routines.
    Triggers 'morning brief' at 8 AM, 'end-of-day summary' at 6 PM.
    """
    def __init__(self):
        self.routines_enabled = True

    async def start_routine_scheduler(self):
        """Background task to evaluate time-based routines."""
        print("[Routines] Scheduler active.")
        while self.routines_enabled:
            now = datetime.now()
            
            # 8:00 AM Morning Briefing
            if now.hour == 8 and now.minute == 0:
                print("\n[Routines] Triggering Morning Briefing...")
                from ..agents.pentagi import pentagi_pipeline
                await pentagi_pipeline.run("prepare my morning briefing")
                await asyncio.sleep(60) # Prevent multiple triggers
                
            # 6:00 PM Activity Summary
            elif now.hour == 18 and now.minute == 0:
                print("\n[Routines] Triggering End-of-Day Summary...")
                # trigger summary agent
                await asyncio.sleep(60)

            await asyncio.sleep(30) # Poll every 30 seconds

routine_manager = RoutineManager()
