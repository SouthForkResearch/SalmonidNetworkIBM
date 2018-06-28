import math
import random
import os

from moviepy.editor import *
from bokeh.io import export_png
from bokeh.io.output import reset_output
from bokeh.plotting import figure, show
from bokeh.models import HoverTool, Label, ColumnDataSource, Arrow, VeeHead, TableColumn, DataTable, \
    NumberFormatter, LinearAxis, Range1d, Span, Axis, Div

from SalNetIBM.fish import LifeHistory, Activity, Sex, Movement
from SalNetIBM.fish_model import FishModel
from SalNetIBM.settings import export_settings, time_settings


def clean_show(item):
    reset_output()
    show(item)

test_model = FishModel(100000)

# fig = figure(plot_width=1024, plot_height=768, toolbar_location='above')
# test_model.network.plot(fig)
# clean_show(fig)

def run_model(n_steps):
    for i in range(n_steps):
        if test_model.schedule.fish_count > 0:
            test_model.step()
            print("Step {0:4d}: {1:8d} fish, {2:8d} redds".format(test_model.schedule.steps,
                                                                  test_model.schedule.fish_count,
                                                                  test_model.schedule.redd_count))

run_model(10)


import cProfile
cProfile.run('run_model(20)', 'runstats')

import pstats
p = pstats.Stats('runstats')
p.sort_stats('time').print_stats(30)

# So the bad ones were already disconnected for pickling, and somehow were still included....

test_model.generate_report(movies=False, passage=False, individuals=30)
test_model.create_movie(test_model.mainpanel_videoframe_function, 'Total Population Details', 'population')

# Find individuals in reach 2817 on timestep 433

live_fish_at_time = test_model.fish_alive_at_timestep(433)
test_fish = [fish for fish in live_fish_at_time if fish.reach_at_timestep(432) == 2817] # seems to really show what's going on at 433
for fish in test_fish:
    if fish.mass_at_timestep(432) > 1:
        print(fish.mass_at_timestep(432))
# I've got some things to sort with the indexing to be able to get a list of fish IDs in a given reach at a given time, some indices off by 1 somewhere
# Also check that dispersal fish are doing some freshwater growth
# Add territory size to log



for i in range(20):
    clean_show(test_fish[i].plot())

# Todo new plots:

# - Spawner size distributions, by year and life history

# Plot number of anadromous spawners per year, although Redd plot is kind of similar to that

# - Plot the spawner-recruit relationship? Although it would have very poor contrast without some more stochasticity.

# - Mean lifespan of now-dead fish as a function of birth timestep and life history

# - Plot the population of a given reach over time, by life history and size

# - Need to figure out if they were mature at the beginning of the spawning period
# - Then figure out if their event history include successful or unsuccesful spawning
# - If neither, they didn't spawn: but figure out if they tried to do the migration

import numpy as np
import pandas as pd
from bokeh.layouts import column, row
from SalNetIBM.settings import resident_fish_settings, anadromous_fish_settings
from bokeh.palettes import viridis

len(test_model.schedule.recent_dead_fish)

import pickle

bad_fish = None
with open("/Users/Jason/Desktop/temp.pickle", mode='wb') as log_file:
    p = pickle.Pickler(log_file)
    p.dump(test_model.schedule.recent_dead_fish[41535])
    # for fish in test_model.schedule.recent_dead_fish:
    #     # try to pickle fish one-by-one
    #     bad_fish = fish
    #     p.dump(fish)
    #     break

temp_fish = test_model.schedule.recent_dead_fish[41535]

# -- Investigate Yankee Fork zero smolt passage??




fig = test_model.plot_freshwater_growth_rates()
clean_show(fig)
export_png(fig, os.path.join(export_settings['RESULTS_PATH'], "Freshwater Growth Rates.png"))




# EXAMPLE OF HOW TO MODIFY A FUNCTION FOR A LIVE OBJECT

# from SalNetIBM.fish import Fish
# def activity_at_age(self, age_weeks):
#     previous_activity = self.activity_history[0][2]
#     for event_log_index, activity_age, activity in self.activity_history:
#         if activity_age >= age_weeks:
#             return previous_activity
#         previous_activity = activity
#     return self.activity_history[-1][2]
# Fish.activity_at_age = activity_at_age

test_model.create_movie(test_model.mainpanel_videoframe_function, 'Total Population Details', 'population')
export_png(test_model.passage_report(), os.path.join(export_settings['RESULTS_PATH'], "Passage Plots.png"))

# RUN TIMING TEST


# cProfile.run('run_model(500)', 'runstats')
# p = pstats.Stats('runstats')
# p.strip_dirs().sort_stats('tottime').print_stats(25)
#p.print_callers(25)

# PLOTS COMPLETED AND SENT OFF TO THEIR HOME OBJECTS

# The standard suite of export results should include all of these, all the passage plots (as an option),
# and videos (as an option)

survival_plot = test_model.survival_plot()
clean_show(survival_plot)

population_size_plot = test_model.plot_population_size(45) # SHOULD MOVE TO MODEL, NOT NETWORK, AND SPLIT NETWORK INTO 2 FILES
clean_show(population_size_plot)

mortality_source_table = test_model.mortality_source_table()
clean_show(mortality_source_table)

success_rate_table = test_model.success_rate_table()
clean_show(success_rate_table)

# PLOTS FOR INDIVIDUAL FISH

dead_fish = test_model.schedule.dead_fish
interesting_dead_fish = [fish for fish in dead_fish if len(fish.activity_history) > 7 and fish.life_history is LifeHistory.ANADROMOUS]
random_fish = random.choice(interesting_dead_fish)
fish_fig = random_fish.plot()

test_model.schedule.dead_fish.sort(key=lambda x: -x.age_weeks)

# Ferreting out specific anoomalies

all_fish = test_model.schedule.fish + test_model.schedule.dead_fish

fish_stuck_spawning = [fish for fish in all_fish if fish.activity is Activity.SPAWNING and fish.activity_duration > 20]
fish_stuck_migration = [fish for fish in all_fish if fish.activity is Activity.SPAWNING_MIGRATION and fish.activity_duration > 20]
spawning_in_ocean = [fish for fish in all_fish if fish.activity is Activity.SPAWNING and fish.network_reach.is_ocean]
spawning_in_migration_reach = [fish for fish in all_fish if fish.activity is Activity.SPAWNING and fish.network_reach.is_migration_reach]

anad_stuck_migration = [fish for fish in fish_stuck_migration if fish.life_history is LifeHistory.ANADROMOUS]

# problem for migration-stuck fish

show(fish_stuck_spawning[0].plot())

# todo check territory sizes
# todo check amount of time fish are taking to die and whether they eat at all during dispersion
# todo see if large fish are using very large territories inefficiently and occupying space to block out small fish

# Network property plots -- put basic capacity plots

fig = figure(plot_width=1024, plot_height=768, match_aspect=True, toolbar_location='above')
fig.xgrid.visible = False
fig.ygrid.visible = False
fig.xaxis.visible = False
fig.yaxis.visible = False
# test_model.network.plot(fig)
# test_model.network.plot(fig, history_step=433, color_attr='temperature', circle_attr='population', circle_hover_attrs=['id','population','anadromous','resident'])
# test_model.network.plot(fig, color_attr='capacity_redds')
# test_model.network.plot(fig, color_attr='capacity_small_fish')
# test_model.network.plot(fig, history_step=25, color_attr='proportion_capacity_small', color_attr_bounds=[0, 1])
test_model.network.plot(fig, history_step=433, color_attr='temperature', circle_attr='population',
                        circle_attr_transform=lambda x: 1.0 * math.sqrt(x), circle_line_color='#cb7723',
                        circle_fill_color='#fcb001',
                        circle_hover_attrs=['id', 'population', 'anadromous', 'resident'])
clean_show(fig)

