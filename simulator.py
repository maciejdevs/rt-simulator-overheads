from queue import PriorityQueue

from task import *

import numpy as np
from draw import draw_schedule
from task_set import TaskSet
from timer_control_block import TimerControlBlock
from utils import ExecutionType, parse_input_file, parse_arguments

TICK_RATE = 1
SAVING_CONTEXT_OVERHEAD = 0.00
LOADING_CONTEXT_OVERHEAD = 0.00
DECREMENT_TIMER_OVERHEAD = 0.00
RESTART_TIMER_OVERHEAD = 0.00
RESUME_OVERHEAD = 0.00
ADD_READY_OVERHEAD = 0.00
GET_HPT_OVERHEAD = 0.00
END_TASK_OVERHEAD = 0
PREEMPTION_OVERHEAD = 0
CONSIDER_TICK_OVERHEADS = False


class Simulator:
    def __init__(self, task_set: TaskSet):
        self.task_set = task_set
        self.tasks = task_set.get_tasks()
        self.current_time = 0
        self.ready_queue = PriorityQueue()
        self.timer_list = []
        self.current_job = None
        self.history = []
        self.time_before_tick = TICK_RATE
        self.has_missed_deadline = False
        self.context_switch_flag = False
        self.cumulative_overhead_time = 0.0
        self.tasks_state = {}
        self.last_interrupted_job = None
        self.deadline_miss_time = 0

        for task in self.tasks:
            self.timer_list.append(TimerControlBlock(task))
            if task.offset == 0:
                self.ready_queue.put(task.get_new_job(self.current_time))

        idle_task = Task(IDLE_TASK, 0, math.inf, math.inf, math.inf, 0)
        self.ready_queue.put(idle_task.get_new_job(self.current_time))

    def dispatch(self):
        if self.ready_queue.queue[0].name == IDLE_TASK:
            self.current_job = self.ready_queue.queue[0]
        else:
            self.current_job = self.ready_queue.get()

    # This function simulates the working of a real-time task. Indeed, we need to simulate some work by decrementing
    # the time left from the WCET.
    def execute_job(self):
        self.last_interrupted_job = self.current_job
        if self.current_job.task.remaining_init_time > 0:
            self.__execute_job_til_tick(init_phase=True)
            if self.time_before_tick <= 0:
                return

        self.__execute_job_til_tick(init_phase=False)
        if self.current_job.remaining_time <= 0:
            if self.__is_ctx_flag_needed():
                self.context_switch_flag = True
            self.__add_end_task_overhead()
            self.dispatch()

    def tick(self):
        self.current_time += TICK_RATE
        self.time_before_tick = TICK_RATE

        self.__save_tasks_state()
        self.__reset_ctx_flag()

        some_task_awaken = self.__decrement_timers()

        if self.__is_preemption_required(some_task_awaken):
            # If the head of the ready queue has a higher priority than the current job
            # then, a preemption is required
            self.__handle_preemption()
            self.__add_preemption_overhead()
        else:
            self.__add_get_hpt_overhead()

        if self.current_job.name != IDLE_TASK:
            self.__add_tick_overhead(LOADING_CONTEXT_OVERHEAD, "LOAD")

        self.__add_tick_overhead(RESUME_OVERHEAD, "RESUME")

    def __add_get_hpt_overhead(self):
        # The overhead get_hpt is required when the currently interrupted job has already finished. The check is
        # required when the tick interrupted the end of jobs overheads.
        if self.__has_interrupted_job_finished():
            self.history.append((TICK_TASK, GET_HPT_OVERHEAD, ExecutionType.PREEMPTION_OVERHEAD, "GET HPT"))
            self.time_before_tick -= GET_HPT_OVERHEAD
            self.cumulative_overhead_time += GET_HPT_OVERHEAD
            self.__decrement_time_til_deadlines(GET_HPT_OVERHEAD)

        if self.current_job.name == IDLE_TASK:
            self.dispatch()

    def __has_interrupted_job_finished(self):
        return self.last_interrupted_job is not None and self.last_interrupted_job.remaining_time == 0

    def run(self, total_time=-1):
        if total_time == -1:
            return self.__find_simulation_interval()
        else:
            return self.__simulate_for(total_time)

    def get_history(self):
        return self.history

    def __is_preemption_required(self, some_task_awaken):
        awaken_higher_priority = self.last_interrupted_job is not None and (
                self.ready_queue.queue[0] < self.last_interrupted_job)
        return some_task_awaken and awaken_higher_priority

    def __simulate_for(self, total_time):
        self.dispatch()

        while self.current_time < total_time and not self.has_missed_deadline:
            # if self.last_interrupted_job is None and self.last_interrupted_job.remaining and self.time_before_tick == 0:
            #     self.last_interrupted_job = self.current_job
            if self.time_before_tick > 0:
                self.execute_job()
            else:
                self.tick()

        return self.has_missed_deadline, self.deadline_miss_time

    def __find_simulation_interval(self):
        self.dispatch()
        k = 0
        h = self.task_set.hyperperiod
        previous_system_state = None
        previous_system_state_time = 0

        while not self.has_missed_deadline:
            if self.current_time > 0 and self.current_time % (h + k * h) == 0:
                current_system_state = (self.cumulative_overhead_time, self.tasks_state.copy())
                if previous_system_state == current_system_state:
                    break
                previous_system_state = current_system_state
                previous_system_state_time = self.current_time
                self.cumulative_overhead_time = 0.0
                k += 1

            if self.time_before_tick > 0:
                self.execute_job()
            else:
                self.tick()

        return (self.has_missed_deadline, self.deadline_miss_time), previous_system_state_time

    def __execute_job_til_tick(self, init_phase):
        updated_time_before_tick = 0.0
        used_cpu_time = 0.0

        if init_phase:
            updated_time_before_tick = max(0, self.time_before_tick - self.current_job.task.remaining_init_time)
            used_cpu_time = min(self.time_before_tick, self.current_job.task.remaining_init_time)
            self.cumulative_overhead_time += used_cpu_time
            self.current_job.task.remaining_init_time -= used_cpu_time
            self.history.append((self.current_job.name, used_cpu_time, ExecutionType.INIT_OVERHEAD))
        else:
            updated_time_before_tick = max(0, self.time_before_tick - self.current_job.remaining_time)
            used_cpu_time = min(self.time_before_tick, self.current_job.remaining_time)
            self.current_job.remaining_time -= used_cpu_time
            self.history.append((self.current_job.name, used_cpu_time, ExecutionType.TASK))

        self.time_before_tick = updated_time_before_tick
        self.current_job.task.cumulative_cpu_time += used_cpu_time
        self.__decrement_time_til_deadlines(used_cpu_time)

    def __add_end_task_overhead(self):
        timeleft = self.time_before_tick
        overheads = 0

        # Check if there is enough time to execute the whole context saving overhead
        if SAVING_CONTEXT_OVERHEAD <= timeleft:
            self.history.append(
                (self.current_job.name, SAVING_CONTEXT_OVERHEAD, ExecutionType.END_JOB_OVERHEAD, "SAVE"))
            timeleft -= SAVING_CONTEXT_OVERHEAD
            overheads += SAVING_CONTEXT_OVERHEAD

            # Check if there is enough time to execute the whole get_hpt overhead
            if GET_HPT_OVERHEAD <= timeleft:
                self.history.append(
                    (self.current_job.name, GET_HPT_OVERHEAD, ExecutionType.END_JOB_OVERHEAD, "GET_HPT"))
                timeleft -= GET_HPT_OVERHEAD
                overheads += GET_HPT_OVERHEAD

                if self.ready_queue.queue[0].name != IDLE_TASK:
                    # Check if there is enough time to execute the whole context loading overhead
                    if LOADING_CONTEXT_OVERHEAD <= timeleft:
                        self.history.append(
                            (self.current_job.name, LOADING_CONTEXT_OVERHEAD, ExecutionType.END_JOB_OVERHEAD, "LOAD"))
                        overheads += LOADING_CONTEXT_OVERHEAD
                    else:
                        self.history.append((self.current_job.name, timeleft, ExecutionType.END_JOB_OVERHEAD, "LOAD"))
                        overheads += timeleft
            else:
                self.history.append((self.current_job.name, timeleft, ExecutionType.END_JOB_OVERHEAD, "GET_HPT"))
                overheads += timeleft
        else:
            self.history.append((self.current_job.name, timeleft, ExecutionType.END_JOB_OVERHEAD, "SAVE"))
            overheads += timeleft

        self.time_before_tick -= overheads
        self.cumulative_overhead_time += overheads
        self.__decrement_time_til_deadlines(overheads)

    def __add_tick_overhead(self, overheads, label=""):
        if CONSIDER_TICK_OVERHEADS:
            self.history.append((TICK_TASK, overheads, ExecutionType.TICK_OVERHEAD, label))
            self.time_before_tick -= overheads
            self.cumulative_overhead_time += overheads
            self.__decrement_time_til_deadlines(overheads)

    def __add_preemption_overhead(self):
        preemption_overheads = GET_HPT_OVERHEAD
        if not self.__has_interrupted_job_finished() and self.last_interrupted_job.name != IDLE_TASK:
            self.history.append((TICK_TASK, ADD_READY_OVERHEAD, ExecutionType.PREEMPTION_OVERHEAD, "ADD READY"))
            preemption_overheads += ADD_READY_OVERHEAD
        self.history.append((TICK_TASK, GET_HPT_OVERHEAD, ExecutionType.PREEMPTION_OVERHEAD, "GET HPT"))
        self.time_before_tick -= preemption_overheads
        self.cumulative_overhead_time += preemption_overheads
        self.__decrement_time_til_deadlines(preemption_overheads)

    def __add_initialization_overhead(self):
        init_overhead = self.current_job.get_init_overhead()
        self.history.append((self.current_job.name, init_overhead, ExecutionType.INIT_OVERHEAD))
        self.time_before_tick -= init_overhead
        self.cumulative_overhead_time += init_overhead
        self.__decrement_time_til_deadlines(init_overhead)

    def __save_tasks_state(self):
        for task in self.tasks:
            self.tasks_state[task.name] = [task.time_since_last_quest, task.cumulative_cpu_time]

    def __is_ctx_flag_needed(self):
        return SAVING_CONTEXT_OVERHEAD <= self.time_before_tick \
            and GET_HPT_OVERHEAD + LOADING_CONTEXT_OVERHEAD > (self.time_before_tick - SAVING_CONTEXT_OVERHEAD)

    def __handle_preemption(self):
        if self.current_job.name != IDLE_TASK:
            self.ready_queue.put(self.current_job)
        self.dispatch()

    def __decrement_timers(self):
        some_task_awaken = False
        timers_overheads_included = False
        for timer in self.timer_list:
            current_task_awaken = False
            if timer.decrement(TICK_RATE):
                self.ready_queue.put(timer.get_task().get_new_job(self.current_time))
                some_task_awaken = True
                current_task_awaken = True

            if not timers_overheads_included:
                self.__add_tick_overhead(DECREMENT_TIMER_OVERHEAD, "DECREMENT TIMER")
                timers_overheads_included = True

            if current_task_awaken:
                self.__add_tick_overhead(RESTART_TIMER_OVERHEAD, "RESTART TIMER")
                self.__add_tick_overhead(ADD_READY_OVERHEAD, "ADD READY")

        return some_task_awaken

    def __decrement_time_til_deadlines(self, duration):
        if not self.has_missed_deadline:
            for job in self.ready_queue.queue + [self.current_job]:
                job.decrement_time_til_deadline(duration)
                if job.absolute_deadline - self.current_time - (TICK_RATE - self.time_before_tick) < job.remaining_time:
                    # if job.remaining_time > 0 and job.time_til_deadline <= 0:
                    self.has_missed_deadline = True
                    self.deadline_miss_time = job.absolute_deadline
                    self.history.append((job.name, 2, ExecutionType.MISSED_DEADLINE, job.absolute_deadline))
                    return True
            return False

    def __reset_ctx_flag(self):
        if not self.context_switch_flag and (
                self.last_interrupted_job is not None and self.last_interrupted_job.name != IDLE_TASK):
            self.__add_tick_overhead(SAVING_CONTEXT_OVERHEAD, "SAVE")
        else:
            self.context_switch_flag = False


def set_system_settings(s_overheads, s_algorithm):
    global TICK_RATE
    TICK_RATE = s_overheads['Tick_rate']
    global SAVING_CONTEXT_OVERHEAD
    SAVING_CONTEXT_OVERHEAD = s_overheads['Save']
    global LOADING_CONTEXT_OVERHEAD
    LOADING_CONTEXT_OVERHEAD = s_overheads['Load']
    global DECREMENT_TIMER_OVERHEAD
    DECREMENT_TIMER_OVERHEAD = s_overheads['Decrement_timer']
    global RESTART_TIMER_OVERHEAD
    RESTART_TIMER_OVERHEAD = s_overheads['Restart_timer']
    global RESUME_OVERHEAD
    RESUME_OVERHEAD = s_overheads['Resume']
    global ADD_READY_OVERHEAD
    ADD_READY_OVERHEAD = s_overheads['Add_ready']
    global GET_HPT_OVERHEAD
    GET_HPT_OVERHEAD = s_overheads['Get_hpt']
    global END_TASK_OVERHEAD
    END_TASK_OVERHEAD = SAVING_CONTEXT_OVERHEAD + GET_HPT_OVERHEAD + LOADING_CONTEXT_OVERHEAD
    global PREEMPTION_OVERHEAD
    PREEMPTION_OVERHEAD = ADD_READY_OVERHEAD + GET_HPT_OVERHEAD
    global CONSIDER_TICK_OVERHEADS
    CONSIDER_TICK_OVERHEADS = True

    Job.Scheduler = s_algorithm


if __name__ == '__main__':
    args = parse_arguments()

    task_set, algorithm, overheads = parse_input_file(args.input)
    set_system_settings(overheads, algorithm)

    if args.draw:
        output = args.draw[0]
        interval = int(args.draw[1])

        simulator = Simulator(task_set)
        simulator.run(interval)

        print("The schedule was saved to file ", output)
        task_set.add_task(Task(IDLE_TASK, 0, math.inf, math.inf, 0, 0))
        draw_schedule(simulator.get_history(), task_set, TICK_RATE, output, show_tick=args.ticks,
                      show_hyperperiod=args.hps, show_overheads_labels=args.labels, interval=interval)
    else:
        simulator = Simulator(task_set)
        missed_deadline, sim_interval = simulator.run()

        if missed_deadline[0]:
            print("A deadline was missed at time instant ", missed_deadline[1])
        else:
            print("The simulation interval is [0, ", sim_interval, "]")
