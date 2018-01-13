import math
import random
import os

from moviepy.editor import *
from bokeh.io import export_png
from bokeh.io.output import reset_output
from bokeh.plotting import figure, show

from SalNetIBM.fish import LifeHistory
from SalNetIBM.fish_model import FishModel
from SalNetIBM.settings import export_settings


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

run_model(300)

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



# Network property plots -- put basic capacity plots

fig = figure(plot_width=1024, plot_height=768, match_aspect=True, toolbar_location='above')
fig.xgrid.visible = False
fig.ygrid.visible = False
fig.xaxis.visible = False
fig.yaxis.visible = False
test_model.network.plot(fig)
# test_model.network.plot(fig, color_attr='capacity_redds')
# test_model.network.plot(fig, color_attr='capacity_small_fish')
# test_model.network.plot(fig, history_step=25, color_attr='proportion_capacity_small', color_attr_bounds=[0, 1])
test_model.network.plot(fig, history_step=99, color_attr='temperature', circle_attr='population',
                        circle_attr_transform=lambda x: 1.0 * math.sqrt(x), circle_line_color='#cb7723',
                        circle_fill_color='#fcb001')#,
                        # circle_hover_attrs=['id', 'length', 'population', 'anadromous', 'resident',
                        #                     'capacity_small_fish', 'small', 'proportion_capacity_small',
                        #                     'capacity_medium_fish', 'medium', 'proportion_capacity_medium',
                        #                     'capacity_redds', 'redds', 'proportion_capacity_redds'])
clean_show(fig)

