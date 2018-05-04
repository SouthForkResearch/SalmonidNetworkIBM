import math
import random
import os

from moviepy.editor import *
from bokeh.io import export_png
from bokeh.io.output import reset_output
from bokeh.plotting import figure, show
from bokeh.models import HoverTool, Label, ColumnDataSource, Arrow, VeeHead, TableColumn, DataTable, LinearAxis, Range1d


from SalNetIBM.fish import LifeHistory, Activity, Sex, Movement
from SalNetIBM.fish_model import FishModel
from SalNetIBM.settings import export_settings


def clean_show(item):
    reset_output()
    show(item)

test_model = FishModel(2000)



# all_gpps ranges from 0.0008 to 0.74 (for annual mean)

# site with lineOID 3799 has conductivity of 113102 (next highest is 345), so i'm capping at 350 in the gpp equation


from SalNetIBM.bioenergetics import daily_growth_from_grams_consumed, daily_growth_from_p
import numpy as np
import scipy


def elliott_territory_size_m2(fork_length_mm):
    if fork_length_mm < 40:
        territory_size_cm2 = 10 ** (-2.844 + 3.453 * np.log10(fork_length_mm))
    else:
        territory_size_cm2 = 10 ** (-0.901 + 2.24 * np.log10(fork_length_mm))
    return territory_size_cm2 / 10000


def food_per_m2_for_target_growth_rate(fish, specific_growth_rate_g_per_g):
    # Want find food_per_m2 to minimize this objective function, achieving the desired growth rate
    def objective_function(food_g_per_day_per_m2):
        consumption_g_per_day = float(elliott_territory_size_m2(fish.fork_length) * food_g_per_day_per_m2)
        return abs(daily_growth_from_grams_consumed(15, fish.mass, consumption_g_per_day) - specific_growth_rate_g_per_g)
    result = scipy.optimize.minimize(objective_function, [1], method='SLSQP', bounds=[(1e-12, 1e5)])
    if result.success == True:
        return result.x[0]
    else:
        print("WARNING: Optimization of food quantity to target consumption rate didn't work. Result: ", result)
        return -1

fish = test_model.random_live_fish()
target_rate = 0.01
food_concentration = food_per_m2_for_target_growth_rate(fish, target_rate)
dg = daily_growth_from_grams_consumed(15, fish.mass, elliott_territory_size_m2(fish.fork_length)*food_concentration)
print("Got actual growth {0:.2f} for target growth {1:.2f}, with food concentration {2} g/m2/day.".format(dg, target_rate, food_concentration))


# Look at the food concentration to achieve a fairly good p-value from a standard-sized territory as the fish increases in size.
fish = test_model.random_live_fish()
fish.model.schedule.time = 24  # set to a summer temperature for +growth
fish.p = 0.4  # give it a good ration
masses = []
food_concs = []
for i in range(200):
    masses.append(fish.mass)
    well_fed_fish_daily_specific_growth = daily_growth_from_p(fish.temperature, fish.mass, fish.p)
    food_concs.append(food_per_m2_for_target_growth_rate(fish, well_fed_fish_daily_specific_growth))
    fish.grow()
source = ColumnDataSource({'mass': masses, 'food_concs': food_concs})
fig = figure(tools=[], plot_width=450, plot_height=320)
fig.xaxis.axis_label = 'Mass of fish (g)'
fig.yaxis.axis_label = 'Food concentration to get p={0:2f} from avg territory'.format(fish.p)
fig.line('mass', 'food_concs', source=source, line_width=2, legend='Mass', line_color='forestgreen')
fig.toolbar.logo = None
clean_show(fig)

# This approaches an asymptote right around 2 g/m2/day for p=0.4.
# For p=0.2, the asymptote is down around 1.5 g/m2/day.
# For p=0.5, it's around 2.3 g/m2/day.
# We want the median GPP (percentile 0.5) to line up pretty well with about 2 g/m2/day.
# To create decent contrast in the extremes without territory sizes getting unrealistically out of hand,
# we can allow it to range from around 1.5 to 2.5 g/m2/day.
# Therefore food_production_g_per_m2_per_day = 1.5 + mean_gpp_percentile


# Food concentration to achieve a given specific growth rate in a standard territory increases with mass, not surprisingly,
# because big fish should generally have lower specific growth rates. To find a good "average" food concentration to match
# with average GPP, we need to also know "average" specific growth rates for fish at different sizes.












#

for i in range(2):
    test_reach = test_model.network.random_reach(True)
    gpp_plot = test_reach.gpp_plot()
    clean_show(gpp_plot)

# in this one, ascent_path includes 1483, but the final route doesn't get it
# problem_route = test_model.network.route(test_model.network.ocean_reach, test_model.network.reach_with_id(1483), -23, 50)
# [(item[0].id, item[1]) for item in problem_route]  # needs to end on 1483

# problem_route = test_model.network.route(test_model.network.reach_with_id(1612), test_model.network.reach_with_id(1613), 0.701, 5)
# [(item[0].id, item[1]) for item in problem_route]  # needs to end on 1613


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

run_model(100)


test_model.generate_report(movies=False, passage=False, individuals=30)

# ran into error:
#   File "/Users/Jason/Dropbox/SFR/Projects/SalmonidNetworkIBM/SalNetIBM/fish_model.py", line 223, in success_rate_table
#     rates['Smolt-to-ocean survival'] = len(fish_that_grew_in_salt) / len(fish_that_smolted)
# ZeroDivisionError: division by zero

show(test_model.fish_with_id(9879).plot())



test_model.generate_report()
test_model.create_movie(test_model.population_videoframe_function, 'Total Population', 'population')
test_model.create_movie(test_model.population_videoframe_function, 'Redd Count', 'redds')
test_model.create_movie(test_model.capacity_videoframe_function, 'Redd Capacity', 'proportion_capacity_redds')
export_png(test_model.passage_report(), os.path.join(export_settings['RESULTS_PATH'], "Passage Plots.png"))

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






# Network property plots -- put basic capacity plots

fig = figure(plot_width=1024, plot_height=768, match_aspect=True, toolbar_location='above')
fig.xgrid.visible = False
fig.ygrid.visible = False
fig.xaxis.visible = False
fig.yaxis.visible = False
# test_model.network.plot(fig)
test_model.network.plot(fig, color_attr='mean_gpp_percentile')
# test_model.network.plot(fig, color_attr='capacity_redds')
# test_model.network.plot(fig, color_attr='capacity_small_fish')
# test_model.network.plot(fig, history_step=25, color_attr='proportion_capacity_small', color_attr_bounds=[0, 1])
# test_model.network.plot(fig, history_step=99, color_attr='temperature', circle_attr='population',
#                         circle_attr_transform=lambda x: 1.0 * math.sqrt(x), circle_line_color='#cb7723',
#                         circle_fill_color='#fcb001')#,
                        # circle_hover_attrs=['id', 'length', 'population', 'anadromous', 'resident',
                        #                     'capacity_small_fish', 'small', 'proportion_capacity_small',
                        #                     'capacity_medium_fish', 'medium', 'proportion_capacity_medium',
                        #                     'capacity_redds', 'redds', 'proportion_capacity_redds'])
clean_show(fig)

