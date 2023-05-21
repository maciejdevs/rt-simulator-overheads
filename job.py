import math

from utils import SchedulerType


class Job:
    # RM by default but is changed by the simulator if another algorithm is chosen
    Scheduler = SchedulerType.RM

    def __init__(self, task, absolute_deadline, time_til_deadline):
        self.name = task.name
        self.offset = task.offset
        self.WCET = task.WCET
        self.deadline = task.deadline
        self.period = task.period
        self.remaining_time = task.WCET
        self.time_til_deadline = time_til_deadline
        self.task = task
        self.absolute_deadline = absolute_deadline

    def get_init_overhead(self):
        return self.task.init_overhead

    def decrement_time_til_deadline(self, tick_rate):
        self.time_til_deadline -= tick_rate

    def __lt__(self, other):
        if Job.Scheduler == SchedulerType.RM:
            if self.period == other.period:
                if self.name == other.name:
                    return self.absolute_deadline < other.absolute_deadline
                else:
                    return self.name > other.name
            else:
                return self.period < other.period

        elif Job.Scheduler == SchedulerType.EDF:
            if math.isnan(self.absolute_deadline):
                return False
            elif math.isnan(other.absolute_deadline):
                return True
            else:
                return self.absolute_deadline < other.absolute_deadline
