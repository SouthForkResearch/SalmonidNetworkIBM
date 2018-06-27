# Mixin for FishModel to hold table output functions in a separate file.

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

class FishModelVideos:

    def capacity_videoframe_function(self, frame, color_attr):
        """ which_attr proportion_capacity_redds"""
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
        for step in np.arange(self.schedule.steps):
            frame_paths.append(os.path.join(temp_path, "frame {0:07d}.png".format(step+1)))
            frame_fig = frame_function(step, attr)
            export_png(frame_fig, frame_paths[-1])
            print("Exported frame {0} of {1} for movie {2}.".format(step+1, self.schedule.steps, movie_name))
        print("Making individual-frame movie 'clips' from exported files.")
        clips = [ImageClip(fp).set_duration(1 / 30) for fp in frame_paths]
        print("Concatenating frames into final video.")
        concat_clip = concatenate_videoclips(clips, method="compose")
        print("Writing final video file.")
        concat_clip.write_videofile(os.path.join(export_settings['RESULTS_PATH'], movie_name + '.mp4'), fps=30, bitrate='8000k', codec='mpeg4')
        shutil.rmtree(temp_path, ignore_errors=True)
        print("Finished exporting {0}.mp4.".format(movie_name))

    def create_all_movies(self):
        self.create_movie(self.mainpanel_videoframe_function, 'Total Population Details', 'population')
        self.create_movie(self.population_videoframe_function, 'Total Population', 'population')
        self.create_movie(self.population_videoframe_function, 'Resident Population', 'resident')
        self.create_movie(self.population_videoframe_function, 'Anadromous Population', 'anadromous')
        self.create_movie(self.population_videoframe_function, 'Redd Count', 'n_redds')
        self.create_movie(self.capacity_videoframe_function, 'Redd Capacity', 'proportion_capacity_redds')
