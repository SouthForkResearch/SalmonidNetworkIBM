import math
import random
import os

from moviepy.editor import *
from bokeh.io import export_png
from bokeh.io.output import reset_output
from bokeh.plotting import figure, show

from SalNetIBM.fish import LifeHistory, Activity, Sex, Movement
from SalNetIBM.fish_model import FishModel
from SalNetIBM.settings import export_settings


def clean_show(item):
    reset_output()
    show(item)

test_model = FishModel(200000)

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

run_model(1000)


test_model.generate_report(movies=False, passage=False, individuals=30)

# ran into error:
#   File "/Users/Jason/Dropbox/SFR/Projects/SalmonidNetworkIBM/SalNetIBM/fish_model.py", line 223, in success_rate_table
#     rates['Smolt-to-ocean survival'] = len(fish_that_grew_in_salt) / len(fish_that_smolted)
# ZeroDivisionError: division by zero


def generate_report(self, movies=True, passage=True, individuals=10):
    export_path = export_settings['RESULTS_PATH']
    # print("Exporting basic plots.")
    # export_png(self.survival_plot(), os.path.join(export_path, "Survival Curves.png"))
    # export_png(self.plot_population_size(), os.path.join(export_path, "Population Size.png"))
    # export_png(self.mortality_source_table(), os.path.join(export_path, "Mortality Source Table.png"))
    # export_png(self.success_rate_table(), os.path.join(export_path, "Success Rate Table.png"))
    if individuals > 0:
        print("Exporting representative individual fish histories.")
        self.schedule.dead_fish.sort(key=lambda x: -x.age_weeks)
        oldest_fish = self.schedule.dead_fish[0:individuals]
        interesting_anad_fish = [fish for fish in self.schedule.dead_fish if
                                 len(fish.activity_history) > 7 and fish.life_history is LifeHistory.ANADROMOUS]
        interesting_res_fish = [fish for fish in self.schedule.dead_fish if
                                len(fish.activity_history) > 7 and fish.life_history is LifeHistory.RESIDENT]
        anad_fish = random.sample(interesting_anad_fish, individuals)
        res_fish = random.sample(interesting_res_fish, individuals)
        old_path = os.path.join(export_path, "oldest individuals")
        anad_path = os.path.join(export_path, "selected anadromous individuals")
        res_path = os.path.join(export_path, "selected resident individuals")
        for path in (old_path, anad_path, res_path):
            if not os.path.exists(path):
                os.mkdir(path)
        for fish in oldest_fish:
            export_png(fish.plot(), os.path.join(old_path, "fish {0}.png".format(fish.unique_id)))
        for fish in anad_fish:
            export_png(fish.plot(), os.path.join(anad_path, "fish {0}.png".format(fish.unique_id)))
        for fish in res_fish:
            export_png(fish.plot(), os.path.join(res_path, "fish {0}.png".format(fish.unique_id)))
    if movies:
        print("Exporting movies.")
        self.create_all_movies()
    if passage:
        print("Exporting passage statistics.")
        export_png(self.passage_report(), os.path.join(export_path, "Passage Plots.png"))
    print("Report export complete.")
generate_report(test_model, movies=False, passage=True, individuals=0)


import numpy as np
import shutil
def create_movie(self, frame_function, movie_name, attr):
    """ The frame_function should be a function that takes one parameter (frame) and return a figure."""
    temp_path = os.path.join(export_settings['RESULTS_PATH'], "temp_video_frames_533016")
    frame_paths = []
    for step in np.arange(1, self.schedule.steps):
        frame_paths.append(os.path.join(temp_path, "frame {0:07d}.png".format(step)))
    print("Making individual-frame movie 'clips' from exported files.")
    # clips = [ImageClip(fp).set_duration(1 / 30) for fp in frame_paths]
    clips = [ImageClip(fp) for fp in frame_paths]
    print("Concatenating frames into final video.")
    concat_clip = concatenate_videoclips(clips, method="compose")
    print("Writing final video file.")
    concat_clip.write_videofile(os.path.join(export_settings['RESULTS_PATH']), movie_name + '.mp4', fps=30)
    shutil.rmtree(temp_path, ignore_errors=True)
    print("Finished exporting {0}.mp4.".format(movie_name))
create_movie(test_model, test_model.population_videoframe_function, 'Total Population', 'population')

# fish 117947: going from reach 478 to seek reach 478 for spawning, somehow ends up in reach 498, doesn't spawn, gets stuck for 3 years
# fish 146035: somehow jumps from the ocean to the headwaters (reach 3022) instantly during its second / kelt spawning run

# fish 1667879 : teleports way far away in first timestep / dispersal -- NOT SOLVED YET

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

