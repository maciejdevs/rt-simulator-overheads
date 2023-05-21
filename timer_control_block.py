from task import Task


class TimerControlBlock:
    def __init__(self, task: Task):
        self.task = task
        self.period = task.period
        self.timer = self.get_initial_timer()

    def get_initial_timer(self):
        if self.task.offset == 0:
            return self.period
        else:
            return self.task.offset

    def restart(self):
        self.task.time_since_last_quest = 0
        self.task.cumulative_cpu_time = 0
        self.timer = self.period + self.timer  # Add the negative value of the timer to handle release jiter

    def decrement(self, tick_rate):
        self.task.time_since_last_quest += tick_rate
        self.timer -= tick_rate

        if self.timer <= 0:
            self.restart()
            return True

        return False

    def get_task(self):
        return self.task
