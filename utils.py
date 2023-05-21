import sys
from math import gcd, sqrt
from enum import Enum
import argparse

PHI = (1 + sqrt(5)) / 2


class ExecutionType(Enum):
    TASK = 1
    END_JOB_OVERHEAD = 2
    TICK_OVERHEAD = 3
    PREEMPTION_OVERHEAD = 4
    INIT_OVERHEAD = 5
    MISSED_DEADLINE = 6


class SchedulerType(Enum):
    RM = 1
    EDF = 2

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-input",
                        help="Filename of the system settings including the task set, algorithm and overheads",
                        required=True)
    group = parser.add_argument_group('draw arguments')
    parser.add_argument("-draw",
                        nargs=2,
                        metavar=('OUTPUT', 'INTERVAL'),
                        help="Filename of the output image and the time interval for the simulation")
    group.add_argument("-ticks",
                       help="Specify if you want to display the ticks on the schedule",
                       action="store_true")
    group.add_argument("-hps",
                       help="Specify if you want to display the hyperperiods on the schedule",
                       action="store_true")
    group.add_argument("-labels",
                       help="Specify if you want to display the overheads labels",
                       action="store_true")
    args = parser.parse_args()
    group.required = '-draw' in sys.argv
    return args


def parse_input_file(filename: str):
    with open(filename) as f:
        lines = f.readlines()

    # Parse task set
    # First line is always "Task set".
    if lines[0] != "Task set\n":
        raise Exception(
            f"Expected first line 'Task set:' in {filename}, got {lines[0]}"
        )

    task_set_lines = []
    task_set_end_at_line = 0  # line on which the task_set end
    for i in range(1, len(lines)):
        if lines[i] == "\n":
            task_set_end_at_line = i
            break
        task_set_lines.append(lines[i])

    task_set = []
    for idx, task in enumerate(task_set_lines):
        from task import Task
        task_params = task.split()
        task_set.append(
            Task(len(task_set_lines) - idx, float(task_params[0]), float(task_params[1]), float(task_params[2]), float(task_params[3]),
                 float(task_params[4])))

    # Parse scheduling algorithm
    if lines[task_set_end_at_line + 1] != "Algorithm\n":
        raise Exception(
            f"Expected 'Algorithm' after Task set but not found in {filename}"
        )

    algorithm_end_at_line = 0
    for i in range(task_set_end_at_line + 1, len(lines)):
        if lines[i] == "\n":
            algorithm_end_at_line = i
            break

    algorithm_text = (lines[algorithm_end_at_line - 1]).strip().upper()
    known_schedulers = [scheduler.name for scheduler in SchedulerType]
    if algorithm_text not in known_schedulers:
        raise Exception(
            f"Unknown scheduling algorithm used in {filename}, got {algorithm_text}, but known are {known_schedulers}"
        )
    algorithm = SchedulerType[algorithm_text]

    # Parse system overheads
    if lines[algorithm_end_at_line + 1] != "System overheads\n":
        raise Exception(
            f"Expected 'System overheads' after Algorithm but not found in {filename}"
        )

    overheads_lines = []
    for i in range(algorithm_end_at_line + 2, len(lines)):
        overheads_lines.append(lines[i])

    overheads = {}
    for overhead_line in overheads_lines:
        key, value = overhead_line.strip().split(' = ')
        overheads[key] = float(value)

    from task_set import TaskSet
    return TaskSet(task_set), algorithm, overheads



def calculate_max_offset(tasksList):
    """
    Calculates the maximum offset of a task from a task list.

    :return: the maximum offset of a task from a task list.
    """
    return max(int(task.offset) for task in tasksList)


def calculate_hyperperiod(tasksList):
    """
    Calculates the hyper period from a task list.

    :return: the hyper period.
    """
    periods = []
    for task in tasksList:
        periods.append(int(task.period))
    lcm = 1
    for i in periods:
        lcm = lcm * i // gcd(lcm, i)
    return lcm
