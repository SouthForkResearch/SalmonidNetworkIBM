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

class FishModelTables:

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
        res_dead_fish = [fish for fish in dead_fish if fish.life_history is LifeHistory.RESIDENT]
        anad_dead_fish = [fish for fish in dead_fish if fish.life_history is LifeHistory.ANADROMOUS]

        rates['Fry-to-adult survival (all)'] = len(adult_fish) / len(dead_fish)
        rates['Fry-to-adult survival (anadromous)'] = len(anad_adult_fish) / len(anad_dead_fish)
        rates['Fry-to-adult survival (resident)'] = len(res_adult_fish) / len(anad_dead_fish)
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