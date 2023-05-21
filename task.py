import math

from job import Job

IDLE_TASK = -1
TICK_TASK = -2

class Task:
    def __init__(self, name, offset, WCET, period, deadline, init_overhead=0):
        self.name = name
        self.offset = offset
        self.period = period
        self.deadline = deadline
        self.WCET = WCET
        self.init_overhead = init_overhead
        self.remaining_init_time = init_overhead  # TODO: Delete because useless with constrained deadlines
        self.cumulative_cpu_time = 0
        self.time_since_last_quest = 0
        self.job_counter = 0

    def get_new_job(self, current_time):
        """
        Creates a new job for the current task

        :return: a new Job for the current task
        """
        absolute_deadline = self.offset + self.job_counter * self.period + self.deadline
        time_til_deadline = absolute_deadline - current_time
        self.job_counter += 1
        return Job(self, absolute_deadline, time_til_deadline)

    def __repr__(self):
        return f"Task(name='{self.name}', offset={self.offset}, WCET={self.WCET}, period={self.period}, deadline={self.deadline})"

