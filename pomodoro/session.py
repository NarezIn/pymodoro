'''
NOTE: session is more than jsut a timer, it alternates between work and break for however many iterations
'''
from pomodoro.timer import Timer

class PomodoroSession:

    def __init__(self, work_duration: int, break_duration: int, total_cycles: int = 4):
        self.work_timer = Timer(work_duration)
        self.break_timer = Timer(break_duration)
        self.current_phase = "work"
        self.completed_cycles = 0
        self.total_cycles = total_cycles

    def start(self): 
        if self.current_phase == "work":
            self.work_timer.start()
        else:
            self.break_timer.start()
   
    def pause(self): 
        if self.current_phase == "work":
            self.work_timer.pause()
        else:
            self.break_timer.pause()
            
    def reset(self):
        self.work_timer.reset()
        self.break_timer.reset()
        self.current_phase = "work"
        self.completed_cycles = 0 

    def tick(self):
        if self.current_phase is None:
            return
        elif self.current_phase == "work":
            self.work_timer.tick()

            if self.work_timer.remaining <=0:
                self.switch_phase()
        else:
            self.break_timer.tick()
            if self.break_timer.remaining <= 0:
                self.switch_phase()

    def switch_phase(self):
        if self.current_phase == "work":
            self.current_phase = "break"
            self.break_timer.reset()
            self.break_timer.start()

        else:
            self.completed_cycles += 1
            if self.completed_cycles >= self.total_cycles:
                self.current_phase = None
            else:
                self.current_phase = "work"
                self.work_timer.reset()
                self.work_timer.start()
    
    def get_status(self):
        if self.current_phase is None:
            return {
                "phase": None,
                "remaining_seconds": 0,
                "total_seconds": 0,
                "display_time": "00:00",
                "status": "finished",
                "completed_cycles": self.completed_cycles,
                "total_cycles": self.total_cycles,
            }

        active = self.work_timer if self.current_phase == "work" else self.break_timer
        return {
            "phase": self.current_phase,
            "remaining_seconds": active.remaining,
            "total_seconds": active.duration,
            "display_time": active.get_display_time(),
            "status": active.status,
            "completed_cycles": self.completed_cycles,
            "total_cycles": self.total_cycles,
        }
            
