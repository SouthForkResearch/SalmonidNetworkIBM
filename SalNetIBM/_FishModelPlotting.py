# Mixin for FishModel to hold plotting functions in a separate file.

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
from bokeh.palettes import viridis

import pandas as pd

import os
import shutil
from moviepy.editor import *

from .dominance_based_scheduler import DominanceBasedActivation
from .fish import Fish, LifeHistory, Activity
from .redd import Redd
from .stream_network import StreamNetwork
from .settings import time_settings, export_settings, network_settings, resident_fish_settings, anadromous_fish_settings

class FishModelPlotting:

    def plot_masses_at_timestep(self, timestep):
        fish_at_timestep = self.fish_alive_at_timestep(timestep)
        anad_masses = [fish.mass_at_age(fish.age_at_timestep(timestep)) for fish in fish_at_timestep if
                       fish.life_history is LifeHistory.ANADROMOUS]
        res_masses = [fish.mass_at_age(fish.age_at_timestep(timestep)) for fish in fish_at_timestep if
                      fish.life_history is LifeHistory.RESIDENT]
        max_mass = max([fish.mass for fish in self.schedule.fish + self.schedule.dead_fish])
        # todo fix the ylim to overall max based on anad_hist and res_hist https://stackoverflow.com/questions/29294957/how-can-i-accomplish-set-xlim-or-set-ylim-in-bokeh
        anad_hist, anad_edges = np.histogram(anad_masses, density=True, bins=50, range=(0, max_mass))
        res_hist, res_edges = np.histogram(res_masses, density=True, bins=50, range=(0, max_mass))
        fig = figure(plot_width=400, plot_height=300, tools='',
                     title="Masses at step {0}".format(timestep))
        fig.quad(top=anad_hist, bottom=0, left=anad_edges[:-1], right=anad_edges[1:], fill_color="#036564",
                 line_color="#033649", fill_alpha=0.5, line_alpha=0.5, legend='Anadromous')
        fig.quad(top=res_hist, bottom=0, left=res_edges[:-1], right=res_edges[1:], fill_color="#1fa774",
                 line_color="black", fill_alpha=0.5, line_alpha=0.5, legend='Resident')
        fig.select(dict(type=Axis, layout="left"))[0].formatter.use_scientific = False
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
        overall_title = Div(text="<h2>{0}</h2>".format(title))
        return (column([overall_title, row([timing_fig, age_fig]), row([mass_fig, length_fig])]), title)

    def passage_report(self):
        mainstem_smolt_passage = self.network.reach_with_id(
            network_settings['MOST_DOWNSTREAM_REACH']).passage_stats(Activity.SMOLT_OUTMIGRATION, 'downstream', 'anadromous')

        mainstem_spawner_passage = self.network.reach_with_id(
            network_settings['MOST_DOWNSTREAM_REACH']).passage_stats(Activity.SPAWNING_MIGRATION, 'upstream', 'anadromous')

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

        return [ # todo standardize horizontal axes, figure out why yankee fork showed 0 passage
            self.passage_plot(mainstem_smolt_passage, "Smolt passage at Middle Fork confluence"),
            self.passage_plot(mainstem_spawner_passage, "Spawner passage at Middle Fork confluence"),
            self.passage_plot(lemhi_smolt_passage, "Smolt passage at the Lemhi River mouth"),
            self.passage_plot(lemhi_spawner_passage, "Spawner passage at the Lemhi River mouth"),
            self.passage_plot(yankee_smolt_passage, "Smolt passage at the Yankee Fork mouth"),
            self.passage_plot(yankee_spawner_passage, "Spawner passage at the Yankee Fork mouth"),
            self.passage_plot(pahsimeroi_smolt_passage, "Smolt passage at the Pahsimeroi River mouth"),
            self.passage_plot(pahsimeroi_spawner_passage, "Spawner passage at the Pahsimeroi River mouth")
        ]

    def plot_survivor_proportion(self, n_weeks):
        lifespan_rows = [
            {'BirthWeek': fish.birth_week / time_settings['WEEKS_PER_YEAR'],
             'Lifespan': fish.death_week - fish.birth_week}
            for
            fish in self.schedule.dead_fish]
        ldf = pd.DataFrame(lifespan_rows)
        survivor_df = ldf[ldf['Lifespan'] > n_weeks]
        gsdf = survivor_df.groupby(['BirthWeek'], axis=0, as_index=False).count()
        gadf = ldf.groupby(['BirthWeek'], axis=0, as_index=False).count()
        df_merged = gsdf.merge(gadf, on='BirthWeek')
        df_merged['Proportion_Surviving'] = df_merged['Lifespan_x'] / df_merged['Lifespan_y']
        source = ColumnDataSource(df_merged)
        fig = figure(tools=[], plot_width=1500, plot_height=800,
                     title='Proportion of Fish Born Per Week that Survived {0} Weeks'.format(n_weeks))
        fig.line('BirthWeek', 'Proportion_Surviving', source=source, line_width=2, line_color='slateblue')
        fig.yaxis.axis_label = 'Proportion of survivors'
        fig.xaxis.axis_label = 'Date of birth (years)'
        fig.toolbar.logo = None
        return fig

    def plot_survivor_count(self, n_weeks):
        lifespan_rows = [
            {'BirthWeek': fish.birth_week / time_settings['WEEKS_PER_YEAR'], 'Lifespan': fish.death_week - fish.birth_week}
            for
            fish in self.schedule.dead_fish]
        ldf = pd.DataFrame(lifespan_rows)
        survivor_df = ldf[ldf['Lifespan'] > n_weeks]
        gsdf = survivor_df.groupby(['BirthWeek'], axis=0, as_index=False).count()
        source = ColumnDataSource(gsdf)
        fig = figure(tools=[], plot_width=1500, plot_height=800, title='Fish Born Per Week that Survived {0} Weeks'.format(n_weeks))
        fig.line('BirthWeek', 'Lifespan', source=source, line_width=2, line_color='slateblue')
        fig.yaxis.axis_label = 'Number of survivors'
        fig.xaxis.axis_label = 'Date of birth (years)'
        fig.toolbar.logo = None
        return fig

    def plot_lifespan_by_birth_week(self):
        lifespan_rows = [{'BirthWeek': fish.birth_week / time_settings['WEEKS_PER_YEAR'],
                          'Lifespan': fish.death_week - fish.birth_week} for fish in self.schedule.dead_fish]
        ldf = pd.DataFrame(lifespan_rows)
        gldf = ldf.groupby(['BirthWeek'], axis=0, as_index=False).mean()
        source = ColumnDataSource(gldf)
        fig = figure(tools=[], plot_width=1500, plot_height=800, title='Mean Lifespan')
        fig.line('BirthWeek', 'Lifespan', source=source, line_width=2, line_color='slateblue')
        fig.yaxis.axis_label = 'Mean lifespan (weeks)'
        fig.xaxis.axis_label = 'Date of birth (years)'
        fig.toolbar.logo = None
        return fig

    def plot_fish_born_per_year(self):
        all_fish_birth_years = np.array([math.floor(fish.birth_week / time_settings['WEEKS_PER_YEAR']) for fish in self.schedule.fish + self.schedule.dead_fish])
        birth_years, birth_year_counts = np.unique(all_fish_birth_years, return_counts=True)
        source = ColumnDataSource({
            'Year': birth_years,
            'FishBorn': birth_year_counts
        })
        fig = figure(tools=[], plot_width=500, plot_height=300, title="Fish born per year")
        fig.yaxis.axis_label = 'Fish'
        fig.line('Year', 'FishBorn', source=source, line_width=2, line_color='slateblue')
        fig.xaxis.axis_label = 'Time (years)'
        fig.toolbar.logo = None
        fig.select(dict(type=Axis, layout="left"))[0].formatter.use_scientific = False
        return fig

    def plot_spawning_success_rates(self):
        # spawn status codes: 0 = never became spawner that year, 1 = became spawner but failed to spawn, 2 = spawned successfully
        num_years = int(np.ceil(self.schedule.time / time_settings['WEEKS_PER_YEAR']))
        resident_spawn_statuses = []
        anadromous_spawn_statuses = []
        resident_spawn_start_weeks = [resident_fish_settings['SPAWNING_MIGRATION_START'] + y * time_settings['WEEKS_PER_YEAR'] for y in range(num_years)]
        anadromous_spawn_start_weeks = [anadromous_fish_settings['SPAWNING_MIGRATION_START'] + y * time_settings['WEEKS_PER_YEAR'] for y in range(num_years)]
        for fish in self.schedule.dead_fish + self.schedule.fish:
            if fish.age_weeks >= fish.settings['AGE_AT_MATURITY']:
                spawn_period_duration = fish.settings['SPAWNING_MIGRATION_END'] - fish.settings['SPAWNING_MIGRATION_START']
                maturation_week = fish.birth_week + fish.settings['AGE_AT_MATURITY']
                spawn_start_weeks = resident_spawn_start_weeks if fish.is_resident else anadromous_spawn_start_weeks
                death_week = fish.death_week if fish.death_week is not None else 1e10
                possible_spawn_start_weeks = [week for week in spawn_start_weeks if week + spawn_period_duration >= maturation_week and week <= death_week]
                if len(possible_spawn_start_weeks) > 0:
                    possible_spawn_years = [math.floor(week / time_settings['WEEKS_PER_YEAR']) for week in possible_spawn_start_weeks]
                    spawn_status = {year : 0 for year in possible_spawn_years}
                    for log_index, event_age_weeks, event in fish.event_history:
                        if event in ("Failed to spawn", "Successfully spawned"):
                            event_timestep = event_age_weeks + fish.birth_week
                            most_recent_spawn_start_week = [week for week in spawn_start_weeks if week < event_timestep][-1]
                            spawn_year = math.floor(most_recent_spawn_start_week / time_settings['WEEKS_PER_YEAR'])
                            if event == "Failed to spawn":
                                spawn_status[spawn_year] = 1
                            elif event == "Successfully spawned":
                                spawn_status[spawn_year] = 2
                    spawn_statuses = resident_spawn_statuses if fish.is_resident else anadromous_spawn_statuses
                    spawn_statuses.append(spawn_status)
        afig = figure(tools=[], plot_width=500, plot_height=300, title="Anadromous")
        rfig = figure(tools=[], plot_width=500, plot_height=300, title="Resident")
        for statuses, fig, title in ((anadromous_spawn_statuses, afig, "Anadromous"), (resident_spawn_statuses, rfig, "Resident")):
            fish_not_spawning = {year : 0 for year in range(num_years)}
            fish_failing_to_spawn = {year : 0 for year in range(num_years)}
            fish_successfully_spawning = {year : 0 for year in range(num_years)}
            for individual_status in statuses:
                for year, status_code in individual_status.items():
                    if status_code == 0:
                        fish_not_spawning[year] += 1
                    elif status_code == 1:
                        fish_failing_to_spawn[year] += 1
                    elif status_code == 2:
                        fish_successfully_spawning[year] += 1
            source = ColumnDataSource({
                'Year' : range(num_years),
                'FishNotSpawning' : list(fish_not_spawning.values()),
                'FishFailingToSpawn' : list(fish_failing_to_spawn.values()),
                'FishSuccessfullySpawning' : list(fish_successfully_spawning.values())
            })
            fig.yaxis.axis_label = '# of Mature {0} Fish'.format(title)
            fig.toolbar.logo = None
            fig.line('Year', 'FishNotSpawning', source=source, line_width=2, legend='Not Spawning', line_color='Gray')
            fig.line('Year', 'FishFailingToSpawn', source=source, line_width=2, legend='Spawning But Failing', line_color='Red')
            fig.line('Year', 'FishSuccessfullySpawning', source=source, line_width=2, legend='Spawning Successfully', line_color='Green')
        jointfig = row([afig, rfig])
        return jointfig

    def plot_freshwater_growth_rates(self):
        rows = []
        def mass_category_label(mass_category):
            min = np.exp(mass_category - 0.5)
            max = np.exp(mass_category + 0.5)
            return "{0:.1f}-{1:.1f} g".format(min, max)
        for ts in range(self.schedule.time - 1):
            print("Growth rate plot: processing growth rates for timestep ", ts)
            fish_at_timestep = [fish for fish in self.fish_alive_at_timestep(ts) if
                                fish.age_weeks > 0 and fish.activity is Activity.FRESHWATER_GROWTH]
            for fish in fish_at_timestep:
                current_mass = fish.mass_at_timestep(ts)
                previous_weeks_mass = fish.mass_at_timestep(ts - 1)
                if current_mass is not None and previous_weeks_mass is not None:
                    rows.append({
                        "Time": ts / time_settings['WEEKS_PER_YEAR'],
                        "MassCategory": int(round(np.log(current_mass))),
                        "SGR": ((current_mass - previous_weeks_mass) / previous_weeks_mass) / time_settings[
                            'DAYS_PER_WEEK']
                    })
        df = pd.DataFrame(rows)
        gdf = df.groupby(['MassCategory', 'Time'], axis=0, as_index=False).mean()
        mass_categories = gdf['MassCategory'].drop_duplicates().values
        colors = viridis(len(mass_categories))
        fig = figure(tools=[], plot_width=1500, plot_height=800)
        for mass_category, i in enumerate(mass_categories):
            category_result = gdf[gdf['MassCategory'] == mass_category]
            source = ColumnDataSource(category_result)
            fig.line('Time', 'SGR', source=source, line_width=2, line_color=colors[i],
                     legend=mass_category_label(mass_category))
        fig.yaxis.axis_label = 'Specific growth rate (g/g/day)'
        fig.xaxis.axis_label = 'Time (years)'
        fig.legend.location = 'top_left'
        fig.toolbar.logo = None
        return fig