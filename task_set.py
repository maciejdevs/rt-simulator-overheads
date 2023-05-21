from utils import calculate_max_offset, calculate_hyperperiod


class TaskSet:
    def __init__(self, tasks):
        self.tasks = tasks
        self.max_offset = calculate_max_offset(tasks)
        self.hyperperiod = calculate_hyperperiod(tasks)
        self.feasibility_interval = self.max_offset + 2 * self.hyperperiod

    def add_task(self, task):
        self.tasks.append(task)

    def get_tasks(self):
        return self.tasks
