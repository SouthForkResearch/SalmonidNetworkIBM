import random
import numpy as np
import math

from mesa import Model
from collections import Counter
from bokeh.plotting import figure
from bokeh.models import HoverTool, Label, ColumnDataSource, Arrow, VeeHead, TableColumn, DataTable, \
    NumberFormatter, LinearAxis, Range1d, Span, Axis, Div
from bokeh.layouts import column, row
from bokeh.io import export_png

import os
import shutil
from moviepy.editor import *

from .dominance_based_scheduler import DominanceBasedActivation
from .fish import Fish, LifeHistory, Activity
from .redd import Redd
from .stream_network import StreamNetwork
from .settings import time_settings, export_settings, network_settings


class FishModel(Model):
    """A model with several fish."""

    def __init__(self, initial_population_size):
        self.schedule = DominanceBasedActivation(self, time_settings['WEEKS_PER_YEAR'])
        # Load the network
        self.network = StreamNetwork(self)
        # Create initial fish population
        self.next_fish_index = 0
        self.next_redd_index = 0
        for i in range(initial_population_size):
            life_history = random.choice([LifeHistory.ANADROMOUS, LifeHistory.RESIDENT])
            network_reach = self.network.random_reach(life_history is LifeHistory.ANADROMOUS)
            self.add_fish(network_reach, life_history, None)

    def add_fish(self, network_reach, life_history, redd):
        fish = Fish(self.next_fish_index, self, network_reach, life_history, redd)
        fish.network_reach.small_fish_count += 1
        self.schedule.add_fish(fish)
        self.next_fish_index += 1

    def add_redd(self, mother):
        redd = Redd(self.next_redd_index, self, mother)
        self.schedule.add_redd(redd)
        self.next_redd_index += 1

    def step(self):
        """Advance the model by one step."""
        self.schedule.step()

    def fish_with_id(self, unique_id):
        """ Retrieves a fish by its unique_id attribute, regardless of living or dead."""
        live_fish = [fish for fish in self.schedule.fish if fish.unique_id == unique_id]
        if len(live_fish) == 1:
            return live_fish[0]
        dead_fish = [fish for fish in self.schedule.dead_fish if fish.unique_id == unique_id]
        if len(dead_fish) == 1:
            return dead_fish[0]
        raise ValueError("There are {0} live fish and {1} dead fish with unique_id {2}.".format(len(live_fish), len(dead_fish), unique_id))

    def fish_alive_at_timestep(self, timestep):
        return [fish for fish in self.schedule.fish + self.schedule.dead_fish if
                fish.birth_week <= timestep and fish.birth_week + fish.age_weeks > timestep]

    def plot_masses_at_timestep(self, timestep):
        fish_at_timestep = self.fish_alive_at_timestep(timestep)
        anad_masses = [fish.mass_at_age(fish.age_at_timestep(timestep)) for fish in fish_at_timestep if
                       fish.life_history is LifeHistory.ANADROMOUS]
        res_masses = [fish.mass_at_age(fish.age_at_timestep(timestep)) for fish in fish_at_timestep if
                      fish.life_history is LifeHistory.RESIDENT]
        max_mass = max([fish.mass for fish in self.schedule.fish + self.schedule.dead_fish])
        anad_hist, anad_edges = np.histogram(anad_masses, density=True, bins=50, range=(0, max_mass))
        res_hist, res_edges = np.histogram(res_masses, density=True, bins=50, range=(0, max_mass))
        fig = figure(plot_width=400, plot_height=300, tools='',
                     title="Masses at step {0}".format(timestep))
        fig.quad(top=anad_hist, bottom=0, left=anad_edges[:-1], right=anad_edges[1:], fill_color="#036564",
                 line_color="#033649", fill_alpha=0.5, line_alpha=0.5, legend='Anadromous')
        fig.quad(top=res_hist, bottom=0, left=res_edges[:-1], right=res_edges[1:], fill_color="#1fa774",
                 line_color="black", fill_alpha=0.5, line_alpha=0.5, legend='Resident')
        fig.xaxis.axis_label = 'Body mass (g)'
        fig.yaxis.axis_label = 'Proportion of fish'
        fig.legend.location = 'top_right'
        fig.toolbar.logo = None
        return fig

    def plot_activities_at_timestep(self, timestep):
        fish_at_timestep = self.fish_alive_at_timestep(timestep)
        anad_activities = [fish.activity_at_age(fish.age_at_timestep(timestep)).name for fish in fish_at_timestep if
                           fish.life_history is LifeHistory.ANADROMOUS]
        res_activities = [fish.activity_at_age(fish.age_at_timestep(timestep)).name for fish in fish_at_timestep if
                          fish.life_history is LifeHistory.RESIDENT]
        ac = Counter(anad_activities)
        rc = Counter(res_activities)
        # all_activities = list(set(list(Counter(res_activities).keys()) + list(Counter(anad_activities).keys())))
        # anad_pct = list(100 * np.array([ac[activity] for activity in all_activities]) / len(anad_activities))
        # res_pct = list(100 * np.array([rc[activity] for activity in all_activities]) / len(res_activities))
        # source = ColumnDataSource({'activity': all_activities,
        #                            'anad pct': anad_pct,
        #                            'res pct': res_pct})
        # columns = [
        #     TableColumn(field="activity", title="Current activity", width=250),
        #     TableColumn(field="anad pct", title="% of anadromous", width=125),
        #     TableColumn(field="res pct", title="% of resident", width=125)
        # ]
        # data_table = DataTable(source=source, columns=columns, row_headers=False, width=500, height=200)

        all_activity_names = [a.name for a in Activity]
        all_activity_names.reverse()
        all_life_histories = [l.name for l in LifeHistory]
        data = {'Activities': all_activity_names,
                'Anadromous': [ac[name] for name in all_activity_names],
                'Resident': [rc[name] for name in all_activity_names]
                }
        source = ColumnDataSource(data=data)

        fig = figure(y_range=all_activity_names, plot_width=600, plot_height=300, tools='',
                     title="Fish activities at step {0}".format(timestep))
        fig.toolbar.logo = None
        fig.hbar_stack(['Anadromous', 'Resident'], y='Activities', height=0.8, source=source,
                       color=['#036564', '#1fa774'], legend=all_life_histories)
        fig.xaxis.axis_label = 'Number of fish'
        return fig

    def plot_population_size(self, timestep=None):  # 'self' will be 'network'
        """ Plots a graph of the population size throughout the model run, regardless of timestep specified. The timestep
            just draws a vertical line indicating the current timestep relative to the plotted data."""
        history = self.network.history
        source = ColumnDataSource({'time': np.array([history_step['step'] for history_step in history]) /
                                           time_settings['WEEKS_PER_YEAR'],
                                   'total population': [history_step['anad pop'] + history_step['res pop'] for
                                                        history_step in history],
                                   'anadromous population': [history_step['anad pop'] for history_step in history],
                                   'resident population': [history_step['res pop'] for history_step in history],
                                   'anadromous redds': [history_step['anad redds'] for history_step in history],
                                   'resident redds': [history_step['res redds'] for history_step in history],
                                   'total redds': [history_step['anad redds'] + history_step['res redds'] for
                                                   history_step in history]})
        fig = figure(tools=[], plot_width=500, plot_height=300)
        fig.yaxis.axis_label = 'Population size'
        fig.line('time', 'total population', source=source, line_width=2, legend='Total fish', line_color='lightgray')
        fig.line('time', 'anadromous population', source=source, line_width=2, legend='Anadromous',
                 line_color='forestgreen')
        fig.line('time', 'resident population', source=source, line_width=2, legend='Resident', line_color='slateblue')
        rfig = figure(tools=[], plot_width=500, plot_height=300)
        rfig.yaxis.axis_label = 'Redds'
        rfig.line('time', 'total redds', source=source, line_width=2, legend='Total redds', line_color='lightgray')
        rfig.line('time', 'anadromous redds', source=source, line_width=2, legend='Anadromous',
                  line_color='forestgreen')
        rfig.line('time', 'resident redds', source=source, line_width=2, legend='Resident', line_color='slateblue')
        for f in (fig, rfig):
            fig.xaxis.axis_label = 'Time (years)'
            f.legend.location = 'top_left'
            f.toolbar.logo = None
            f.select(dict(type=Axis, layout="left"))[0].formatter.use_scientific = False
            if timestep is not None:
                f.add_layout(
                    Span(location=timestep / time_settings['WEEKS_PER_YEAR'], dimension='height', line_color='red',
                         line_dash='dashed', line_width=1))
        return row([fig, rfig])

    def survival_plot(self):
        # Survival function plot (based on dead fish only)
        anad_death_ages = np.array(
            [fish.age_weeks for fish in self.schedule.dead_fish if fish.life_history is LifeHistory.ANADROMOUS])
        anad_death_proportions = np.bincount(anad_death_ages) / len(anad_death_ages)
        anad_age_x = np.arange(len(anad_death_proportions)) / time_settings['WEEKS_PER_YEAR']
        anad_survival_y = [1 - np.sum(anad_death_proportions[:i]) for i in np.arange(len(anad_death_proportions))]
        res_death_ages = np.array(
            [fish.age_weeks for fish in self.schedule.dead_fish if fish.life_history is LifeHistory.RESIDENT])
        res_death_proportions = np.bincount(res_death_ages) / len(res_death_ages)
        res_age_x = np.arange(len(res_death_proportions)) / time_settings['WEEKS_PER_YEAR']
        res_survival_y = [1 - np.sum(res_death_proportions[:i]) for i in np.arange(len(res_death_proportions))]
        fig = figure(plot_width=400, plot_height=300, toolbar_location='above')
        fig.xaxis.axis_label = 'Age (years)'
        fig.yaxis.axis_label = 'Proportion surviving'
        fig.line(anad_age_x, anad_survival_y, line_width=2, legend='Anadromous', line_color='forestgreen')
        fig.line(res_age_x, res_survival_y, line_width=2, legend='Resident', line_color='slateblue')
        fig.legend.location = 'top_right'
        fig.toolbar.logo = None
        return fig

    def mortality_source_table(self):
        anad_reasons = [fish.mortality_reason for fish in self.schedule.dead_fish if
                        fish.life_history is LifeHistory.ANADROMOUS]
        res_reasons = [fish.mortality_reason for fish in self.schedule.dead_fish if
                       fish.life_history is LifeHistory.RESIDENT]
        all_reasons = set(list(Counter(res_reasons).keys()) + list(Counter(anad_reasons).keys()))
        ac = Counter(anad_reasons)
        rc = Counter(res_reasons)
        anad_pct = list(100 * np.array([ac[reason] for reason in all_reasons]) / len(anad_reasons))
        res_pct = list(100 * np.array([rc[reason] for reason in all_reasons]) / len(res_reasons))
        source = ColumnDataSource({'reason': list(all_reasons),
                                   'anad pct': anad_pct,
                                   'res pct': res_pct})
        columns = [
            TableColumn(field="reason", title="Mortality reason", width=250),
            TableColumn(field="anad pct", title="% of anadromous", width=125),
            TableColumn(field="res pct", title="% of resident", width=125)
        ]
        return DataTable(source=source, columns=columns, row_headers=False, width=500, height=200)

    def success_rate_table(self):
        """All the calculations below are done on dead fish only, to avoid biasing estimates with live fish that were
            going to succeed at the listed endeavor, but haven't yet. These calculations are still be biased for short
            runtimes, though, because many of those "going to succeed" fish aren't included in the "dead fish" array."""
        rates = {}
        dead_fish = self.schedule.dead_fish
        adult_fish = [fish for fish in dead_fish if fish.is_mature]
        res_adult_fish = [fish for fish in adult_fish if fish.life_history is LifeHistory.RESIDENT]
        anad_adult_fish = [fish for fish in adult_fish if fish.life_history is LifeHistory.ANADROMOUS]
        rates['Fry-to-adult survival (all)'] = len(adult_fish) / len(dead_fish)
        rates['Fry-to-adult survival (anadromous)'] = len(anad_adult_fish) / len(dead_fish)
        rates['Fry-to-adult survival (resident)'] = len(res_adult_fish) / len(dead_fish)
        fish_that_smolted = [fish for fish in dead_fish if
                             fish.life_history is LifeHistory.ANADROMOUS
                             and Activity.SMOLT_OUTMIGRATION in [item[2] for item in fish.activity_history]]
        fish_that_grew_in_salt = [fish for fish in fish_that_smolted if
                                  Activity.SALTWATER_GROWTH in [item[2] for item in fish.activity_history]]
        rates['Smolt-to-ocean survival'] = len(fish_that_grew_in_salt) / len(fish_that_smolted)
        fish_that_survived_salt = [fish for fish in fish_that_grew_in_salt if
                                   Activity.SPAWNING_MIGRATION in [item[2] for item in fish.activity_history]]
        rates['Saltwater growth survival'] = len(fish_that_survived_salt) / len(fish_that_grew_in_salt)
        anad_spawners = [fish for fish in fish_that_survived_salt if
                         fish.life_history is LifeHistory.ANADROMOUS and Activity.SPAWNING in [item[2] for item in
                                                                                               fish.activity_history]]
        res_spawner_migrants = [fish for fish in res_adult_fish if
                                Activity.SPAWNING_MIGRATION in [item[2] for item in fish.activity_history]]
        rates['Spawning migration survival (anadromous)'] = len(anad_spawners) / len(
            fish_that_survived_salt)  # combines failure to spawn with failure to reach spawning grounds
        rates['Survival of adulthood to spawning migration (residents)'] = len(res_spawner_migrants) / len(
            res_adult_fish)

        source = ColumnDataSource({'which_rate': list(rates.keys()), 'value': list(rates.values())})
        columns = [
            TableColumn(field="which_rate", title="Survival or success rate", width=350),
            TableColumn(field="value", title="Value", formatter=NumberFormatter(format='0.00%'), width=50),
        ]
        return DataTable(source=source, columns=columns, width=400, height=300, row_headers=False)

    def capacity_videoframe_function(self, frame, color_attr):
        """ which_attr should be proportion_capacity_small, proportion_capacity_medium, or proportion_capacity_redds"""
        fig = figure(plot_width=1024, plot_height=768, match_aspect=True, toolbar_location='above', tools=[])
        fig.xgrid.visible = False
        fig.ygrid.visible = False
        fig.xaxis.visible = False
        fig.yaxis.visible = False
        self.network.plot(fig, history_step=frame, color_attr=color_attr, color_attr_bounds=[0, 1])
        return fig

    def population_videoframe_function(self, frame, circle_attr):
        fig = figure(plot_width=1024, plot_height=768, match_aspect=True, toolbar_location='above', tools=[])
        fig.xgrid.visible = False
        fig.ygrid.visible = False
        fig.xaxis.visible = False
        fig.yaxis.visible = False
        self.network.plot(fig, history_step=frame, color_attr='temperature', circle_attr=circle_attr,
                          circle_attr_transform=lambda x: 1.0 * math.sqrt(x), circle_line_color='#cb7723',
                          circle_fill_color='#fcb001')
        return fig

    def mainpanel_videoframe_function(self, frame, circle_attr):
        network_fig = self.population_videoframe_function(frame, circle_attr)
        full_panel = column([network_fig,
                             row([self.plot_masses_at_timestep(frame),
                                  self.plot_activities_at_timestep(frame)]),
                             row([self.plot_population_size(frame)])
                             ])
        return full_panel

    def create_movie(self, frame_function, movie_name, attr):
        """ The frame_function should be a function that takes one parameter (frame) and return a figure."""
        temp_path = os.path.join(export_settings['RESULTS_PATH'], "temp_video_frames_" + str(random.randint(1, 999999)))
        os.mkdir(temp_path)
        frame_paths = []
        for step in np.arange(1, self.schedule.steps):
            frame_paths.append(os.path.join(temp_path, "frame {0:07d}.png".format(step)))
            frame_fig = frame_function(step, attr)
            export_png(frame_fig, frame_paths[-1])
            print("Exported frame {0} of {1} for movie {2}.".format(step, self.schedule.steps, movie_name))
        print("Making individual-frame movie 'clips' from exported files.")
        clips = [ImageClip(fp).set_duration(1 / 30) for fp in frame_paths]
        print("Concatenating frames into final video.")
        concat_clip = concatenate_videoclips(clips, method="compose")
        print("Writing final video file.")
        concat_clip.write_videofile(os.path.join(export_settings['RESULTS_PATH']), movie_name + '.mp4')#, fps=30)
        shutil.rmtree(temp_path, ignore_errors=True)
        print("Finished exporting {0}.mp4.".format(movie_name))

    def passage_plot(self, passage, title=""):
        passage_times_x = np.arange(self.schedule.steps) / time_settings['WEEKS_PER_YEAR']
        passage_times_y = np.bincount([item[0] for item in passage])
        passage_times_y = np.pad(passage_times_y, (0, len(passage_times_x) - len(passage_times_y)), 'constant')
        passage_ages = np.array([item[2] for item in passage]) / time_settings['WEEKS_PER_YEAR']
        passage_lengths = np.array([item[3] for item in passage])
        passage_masses = np.array([item[4] for item in passage])
        age_hist, age_edges = np.histogram(passage_ages, density=True, bins=15)
        length_hist, length_edges = np.histogram(passage_lengths, density=True, bins=15)
        mass_hist, mass_edges = np.histogram(passage_masses, density=True, bins=15)
        age_fig = figure(plot_width=400, plot_height=300, tools=[])
        mass_fig = figure(plot_width=400, plot_height=300, tools=[])
        length_fig = figure(plot_width=400, plot_height=300, tools=[])
        age_fig.quad(top=age_hist, bottom=0, left=age_edges[:-1], right=age_edges[1:], fill_color="green",
                     line_color="black", fill_alpha=0.5, line_alpha=0.5)
        mass_fig.quad(top=mass_hist, bottom=0, left=mass_edges[:-1], right=mass_edges[1:], fill_color="#036564",
                      line_color="#033649", fill_alpha=0.5, line_alpha=0.5)
        length_fig.quad(top=length_hist, bottom=0, left=length_edges[:-1], right=length_edges[1:], fill_color="red",
                        line_color="black", fill_alpha=0.5, line_alpha=0.5)
        timing_fig = figure(plot_width=400, plot_height=300, toolbar_location='above')
        timing_fig.line(passage_times_x, passage_times_y, line_width=2, line_color='black')
        age_fig.xaxis.axis_label = 'Fish age (years)'
        age_fig.yaxis.axis_label = 'Proportion of fish'
        age_fig.toolbar.logo = None
        mass_fig.xaxis.axis_label = 'Body mass (g)'
        mass_fig.yaxis.axis_label = 'Proportion of fish'
        mass_fig.toolbar.logo = None
        length_fig.xaxis.axis_label = 'Fork length (mm)'
        length_fig.yaxis.axis_label = 'Proportion of fish'
        length_fig.toolbar.logo = None
        timing_fig.xaxis.axis_label = 'Simulation time (years)'
        timing_fig.yaxis.axis_label = 'Weekly fish passage'
        timing_fig.toolbar.logo = None
        overall_title = Div(text="<h2 style='width:900px'>{0}</h2>".format(title))
        return column([overall_title, row([timing_fig, age_fig]), row([mass_fig, length_fig])])

    def passage_report(self):
        mainstem_smolt_passage = self.network.reach_with_id(
            network_settings['MOST_DOWNSTREAM_REACH']).passage_stats(Activity.SMOLT_OUTMIGRATION, 'downstream',
                                                                     'anadromous')
        mainstem_spawner_passage = self.network.reach_with_id(
            network_settings['MOST_DOWNSTREAM_REACH']).passage_stats(Activity.SPAWNING_MIGRATION, 'upstream',
                                                                     'anadromous')
        lemhi_smolt_passage = self.network.reach_with_id(network_settings['LEMHI_MOUTH']).passage_stats(
            Activity.SMOLT_OUTMIGRATION, 'downstream', 'anadromous')
        lemhi_spawner_passage = self.network.reach_with_id(network_settings['LEMHI_MOUTH']).passage_stats(
            Activity.SPAWNING_MIGRATION, 'upstream', 'anadromous')
        pahsimeroi_smolt_passage = self.network.reach_with_id(network_settings['PAHSIMEROI_MOUTH']).passage_stats(
            Activity.SMOLT_OUTMIGRATION, 'downstream', 'anadromous')
        pahsimeroi_spawner_passage = self.network.reach_with_id(
            network_settings['PAHSIMEROI_MOUTH']).passage_stats(Activity.SPAWNING_MIGRATION, 'upstream', 'anadromous')
        yankee_smolt_passage = self.network.reach_with_id(network_settings['YANKEE_FORK_MOUTH']).passage_stats(
            Activity.SMOLT_OUTMIGRATION, 'downstream', 'anadromous')
        yankee_spawner_passage = self.network.reach_with_id(network_settings['YANKEE_FORK_MOUTH']).passage_stats(
            Activity.SPAWNING_MIGRATION, 'upstream', 'anadromous')
        return column([
            self.passage_plot(mainstem_smolt_passage, "Smolt passage at Middle Fork confluence"),
            self.passage_plot(mainstem_spawner_passage, "Spawner passage at Middle Fork confluence"),
            self.passage_plot(lemhi_smolt_passage, "Smolt passage at the Lemhi River mouth"),
            self.passage_plot(lemhi_spawner_passage, "Spawner passage at the Lemhi River mouth"),
            self.passage_plot(yankee_smolt_passage, "Smolt passage at the Yankee Fork mouth"),
            self.passage_plot(yankee_spawner_passage, "Spawner passage at the Yankee Fork mouth"),
            self.passage_plot(pahsimeroi_smolt_passage, "Smolt passage at the Pahsimeroi River mouth"),
            self.passage_plot(pahsimeroi_spawner_passage, "Spawner passage at the Pahsimeroi River mouth")
        ])

    def create_all_movies(self):
        self.create_movie(self.mainpanel_videoframe_function, 'Total Population Details', 'population')
        self.create_movie(self.population_videoframe_function, 'Total Population', 'population')
        self.create_movie(self.population_videoframe_function, 'Resident Population', 'resident')
        self.create_movie(self.population_videoframe_function, 'Anadromous Population', 'anadromous')
        self.create_movie(self.population_videoframe_function, 'Redd Count', 'n_redds')
        self.create_movie(self.capacity_videoframe_function, 'Small Fish Capacity',
                          'proportion_capacity_small')
        self.create_movie(self.capacity_videoframe_function, 'Medium Fish Capacity',
                          'proportion_capacity_medium')
        self.create_movie(self.capacity_videoframe_function, 'Redd Capacity', 'proportion_capacity_redds')

    def generate_report(self, movies=True, passage=True, individuals=10):
        export_path = export_settings['RESULTS_PATH']
        print("Exporting basic plots.")
        export_png(self.survival_plot(), os.path.join(export_path, "Survival Curves.png"))
        export_png(self.plot_population_size(), os.path.join(export_path, "Population Size.png"))
        export_png(self.mortality_source_table(), os.path.join(export_path, "Mortality Source Table.png"))
        export_png(self.success_rate_table(), os.path.join(export_path, "Success Rate Table.png"))
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
