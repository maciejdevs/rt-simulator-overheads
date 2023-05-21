import matplotlib.pyplot as plt
from math import sqrt, floor

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Ellipse

from task import IDLE_TASK
from utils import ExecutionType, PHI


def draw_schedule(history, task_set, tick_rate, filename, show_tick, show_hyperperiod, show_overheads_labels,
                  interval=-1):
    tasks = task_set.get_tasks()
    if interval == -1:
        feasibility_interval = task_set.feasibility_interval
    else:
        feasibility_interval = interval

    # Declaring a figure "gnt"
    fig, gnt = plt.subplots()
    set_fig_properties()

    tasks_amount = len(tasks)
    fig_height = tasks_amount + 1 if tasks_amount < 9 else 10
    fig.set_figheight(fig_height)
    fig.set_figwidth(16)
    x_lim = feasibility_interval
    y_lim = tasks_amount * 100
    task_height = (y_lim / tasks_amount)
    set_axis_limits(gnt, x_lim, y_lim)

    # Setting labels for x-axis and y-axis
    gnt.set_xlabel('')
    gnt.set_ylabel('')

    set_ticks_on_x_axis(gnt, x_lim)
    set_ticks_on_y_axis(gnt, tasks_amount, y_lim, task_height)
    set_y_ticks_labels(gnt, tasks, tasks_amount)

    gnt.xaxis.grid(True, linestyle='--', lw=1.15, alpha=0.7, color='black')
    gnt.yaxis.grid(True, color='black', lw=1)

    draw_periods_and_deadlines(feasibility_interval, gnt, task_height, tasks, x_lim)

    if show_tick:
        draw_ticks(feasibility_interval, gnt, tick_rate)

    if show_hyperperiod:
        draw_hyperperiods(gnt, task_set)

    draw_tasks(gnt, history, show_overheads_labels, task_height, x_lim, y_lim)
    plt.savefig(filename + ".png", bbox_inches='tight')


def draw_tasks(gnt, history, show_overheads_labels, task_height, x_lim, y_lim):
    cpu_time = 0
    init_overhead_legend = False
    tick_overhead_legend = False
    preemption_overhead_legend = False
    endofjob_overhead_legend = False
    missed_deadline_legend = False

    for idx, task_entry in enumerate(history):
        task_id = task_entry[0]
        used_time = task_entry[1]

        if used_time <= 0:
            continue

        exec_type = task_entry[2]
        color = get_color(task_entry)
        if exec_type == ExecutionType.MISSED_DEADLINE:
            deadline_missed_at = int(task_entry[3])
        else:
            if len(task_entry) > 3:
                overhead_label = task_entry[3]
            else:
                overhead_label = ""

        if exec_type == ExecutionType.TICK_OVERHEAD:
            start = 0
            gnt.broken_barh([(cpu_time, used_time)], (start, y_lim), color='none', alpha=0.5, edgecolor='black', lw=0.8,
                            hatch='X', zorder=4, label="Tick overhead" if not tick_overhead_legend else "")
            gnt.broken_barh([(cpu_time, used_time)], (start, y_lim), facecolor=color, alpha=0.1, edgecolor='black',
                            zorder=5)
            tick_overhead_legend = True
            display_overhead_label(cpu_time, gnt, overhead_label, show_overheads_labels, start, task_height, used_time,
                                   x_lim, y_lim, ExecutionType.TICK_OVERHEAD)
        elif exec_type == ExecutionType.PREEMPTION_OVERHEAD:
            start = 0
            gnt.broken_barh([(cpu_time, used_time)], (start, y_lim), color='none', alpha=0.5, edgecolor='black', lw=0.8,
                            hatch='-', zorder=4,
                            label="Preemption overhead" if not preemption_overhead_legend else "")
            gnt.broken_barh([(cpu_time, used_time)], (start, y_lim), facecolor=color, alpha=0.1, edgecolor='black',
                            zorder=5)
            preemption_overhead_legend = True
            display_overhead_label(cpu_time, gnt, overhead_label, show_overheads_labels, start, task_height, used_time,
                                   x_lim, y_lim, ExecutionType.PREEMPTION_OVERHEAD)
        elif exec_type == ExecutionType.INIT_OVERHEAD:
            start = task_id * task_height
            gnt.broken_barh([(cpu_time, used_time)], (start, task_height), color='none', alpha=0.5, edgecolor='black',
                            lw=0.8,
                            hatch='//', zorder=4, label="Initialization overhead" if not init_overhead_legend else "")
            gnt.broken_barh([(cpu_time, used_time)], (start, task_height), facecolor=color, alpha=0.1,
                            edgecolor='black',
                            zorder=5)
            init_overhead_legend = True
        elif exec_type == ExecutionType.END_JOB_OVERHEAD:
            start = task_id * task_height
            gnt.broken_barh([(cpu_time, used_time)], (start, task_height), facecolor='none', alpha=0.5,
                            edgecolor='black', lw=0.8,
                            hatch='\\\\', zorder=4, label="End of job overhead" if not endofjob_overhead_legend else "")
            gnt.broken_barh([(cpu_time, used_time)], (start, task_height), facecolor=color, alpha=0.1,
                            edgecolor='black',
                            zorder=5)
            endofjob_overhead_legend = True
            display_overhead_label(cpu_time, gnt, overhead_label, show_overheads_labels, start, task_height, used_time,
                                   x_lim, y_lim, ExecutionType.END_JOB_OVERHEAD)
        elif exec_type == ExecutionType.MISSED_DEADLINE:
            start = task_id * task_height
            # if cpu_time <= deadline_missed_at:
            #     cpu_time += (deadline_missed_at - cpu_time)

            gnt.broken_barh([(deadline_missed_at, used_time)], (start, task_height), color='red', alpha=0.8, edgecolor='black',
                            hatch='x*', zorder=4, lw=2, label="Deadline missed" if not missed_deadline_legend else "")
            gnt.broken_barh([(deadline_missed_at, used_time)], (start, task_height), facecolor=color, alpha=0.1,
                            edgecolor='black',
                            zorder=5)
            break
        else:
            if task_id == IDLE_TASK:
                start = 0
            else:
                start = task_id * task_height
            gnt.broken_barh([(cpu_time, used_time)], (start, task_height), facecolor=color, zorder=1)

        cpu_time += used_time

    # update the legend
    if init_overhead_legend or tick_overhead_legend or missed_deadline_legend or preemption_overhead_legend:
        plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left', mode="expand", borderaxespad=0.)


def draw_hyperperiods(gnt, task_set):
    # Draw hyperperiods
    for t in range(0, 100, task_set.hyperperiod):
        gnt.annotate('',
                     xy=(t, 0), xycoords='data',
                     xytext=(t, -20), textcoords='data',
                     arrowprops=dict(arrowstyle='fancy', lw=1.5, zorder=9, clip_on=False))


def draw_ticks(feasibility_interval, gnt, tick_rate):
    # Draw tick interrupts
    for t in np.arange(tick_rate, feasibility_interval + 1, tick_rate):
        gnt.annotate('',
                     xy=(t, 30), xycoords='data',
                     xytext=(t, 0), textcoords='data',
                     arrowprops=dict(arrowstyle='wedge', lw=2, mutation_scale=30, zorder=10, facecolor='black'))


def draw_periods_and_deadlines(feasibility_interval, gnt, task_height, tasks, x_lim):
    for idx, task in enumerate(tasks[:-1]):
        task_id = task.name
        start = (task_id + 1) * task_height
        period = int(task.period)
        deadline = int(task.deadline)
        offset = int(task.offset)

        # Draw downward arrows every period
        for t in range(offset, feasibility_interval + 1, period):
            gnt.annotate('',
                         xy=(t, start - 50), xycoords='data',
                         xytext=(t, start), textcoords='data',
                         arrowprops=dict(arrowstyle='->', lw=2.5, mutation_scale=25, zorder=9))

        # Draw circles every deadline
        for t in range(offset + deadline, feasibility_interval + 1, period):
            # gnt.add_patch(plt.Circle((t, start), radius=2, fill=False, ec='black'))
            gnt.add_patch(
                Ellipse((t, start), width=x_lim / 75, height=15, lw=2, clip_on=False, fill=False, ec='black',
                        zorder=10))


def set_y_ticks_labels(gnt, tasks, tasks_amount):
    # Labelling ticks of y-axis
    y_ticks_label = []
    for idx, task in enumerate(tasks):
        if idx == 0:
            task_label = "Idle task"
        else:
            task_label = "Task " + str(tasks_amount - idx)
        y_ticks_label.append(task_label)
        y_ticks_label.append(task_label)  # Added second time to hide it
    gnt.set_yticklabels(y_ticks_label)


def set_ticks_on_y_axis(gnt, tasks_amount, y_lim, task_height):
    # Setting ticks on y-axis
    y_ticks = []
    y_pos = 0
    for _ in range(0, tasks_amount * 2):
        y_pos += task_height / 2
        y_ticks.append(y_pos)
    gnt.set_yticks(y_ticks)
    # Hide y axis labels
    for index, label in enumerate(gnt.yaxis.get_ticklabels()):
        if index % 2 != 0:
            label.set_visible(False)
    # Hide the horizontal grid lines
    for index, tickLine in enumerate(gnt.yaxis.get_gridlines()):
        if index % 2 == 0:
            tickLine.set_linestyle('None')


def set_ticks_on_x_axis(gnt, x_lim):
    # Setting ticks on x-axis
    gnt.tick_params(axis='x', which='major', length=5, width=1, direction='out', pad=10)
    gnt.tick_params(axis='x', which='minor', length=3, width=2, direction='out')
    # set the tick labels
    xticks = range(x_lim + 1)
    # set tick locations and labels for every fifth tick
    tick_labels = ['' if i % 5 != 0 else str(i) for i in xticks]
    gnt.set_xticks(xticks)
    gnt.set_xticklabels(tick_labels)
    # Make x axis tick lines thin/thick
    for index, tickLine in enumerate(gnt.xaxis.get_ticklines()):
        if index % 5 != 0:
            tickLine.set_markersize(8)
        else:
            tickLine.set_markeredgewidth(1.2)
            tickLine.set_markersize(15)


def set_fig_properties():
    plt.xticks(fontsize=18)
    plt.yticks(fontsize=18)
    plt.xlabel('xlabel', fontsize=30)
    plt.ylabel('ylabel', fontsize=30)

    params = {'legend.fontsize': 16,
              'legend.handlelength': 1,
              'legend.handleheight': 1.55}
    plt.rcParams.update(params)


def set_axis_limits(gnt, x_lim, y_lim):
    # Setting Y-axis limits
    gnt.set_ylim(0, y_lim)
    # Setting X-axis limits
    gnt.set_xlim(0, x_lim)


def set_figure_properties():
    plt.xticks(fontsize=18)
    plt.yticks(fontsize=18)
    plt.xlabel('xlabel', fontsize=30)
    plt.ylabel('ylabel', fontsize=30)


def display_overhead_label(cpu_time, gnt, overhead_label, show_overheads_labels, start, task_height, used_time, x_lim,
                           y_lim,
                           exec_type):
    if show_overheads_labels:
        text_x = cpu_time + (used_time / 2) + 0.1
        if exec_type == ExecutionType.END_JOB_OVERHEAD:
            text_y = start + (task_height / 2)
        else:
            text_y = start + (y_lim / 2)

        if text_x < x_lim:
            fontprops = FontProperties()
            fontprops.set_size(10.2)
            fontprops.set_weight(800)
            fontprops.set_variant('small-caps')

            gnt.text(text_x, text_y, overhead_label, rotation='vertical', va='center', ha='center', alpha=1,
                     fontproperties=fontprops, zorder=12)


def get_color(task_entry):
    if task_entry[2] not in [ExecutionType.TASK, ExecutionType.MISSED_DEADLINE]:
        return 'black'
    elif task_entry[0] == IDLE_TASK:
        return 'dimgray'
    else:
        task_id = task_entry[0]
        n = task_id * PHI - floor(task_id * PHI)
        return n, 0.5, 0.25
