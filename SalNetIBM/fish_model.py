import random

from mesa import Model

from bokeh.io import export_png

import os

from .dominance_based_scheduler import DominanceBasedActivation
from .fish import Fish, LifeHistory, Activity
from ._FishModelPlotting import FishModelPlotting
from ._FishModelTables import FishModelTables
from ._FishModelVideos import FishModelVideos
from .redd import Redd
from .stream_network import StreamNetwork
from .settings import time_settings, export_settings, network_settings


class FishModel(Model, FishModelPlotting, FishModelTables, FishModelVideos):
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

    def random_live_fish(self):
        return random.choice(self.schedule.fish)

    def random_dead_fish(self):
        return random.choice(self.schedule.dead_fish)

    def fish_alive_at_timestep(self, timestep):
        return [fish for fish in self.schedule.fish + self.schedule.dead_fish if
                fish.birth_week <= timestep and fish.birth_week + fish.age_weeks > timestep]

    def generate_report(self, movies=True, passage=True, individuals=10):
        print("Exporting basic plots.")
        export_path = export_settings['RESULTS_PATH']
        if not os.path.exists(export_path):
            os.makedirs(export_path)
        export_png(self.survival_plot(), os.path.join(export_path, "Survival Curves.png"))
        export_png(self.plot_population_size(), os.path.join(export_path, "Population Size.png"))
        export_png(self.mortality_source_table(), os.path.join(export_path, "Mortality Source Table.png"))
        export_png(self.success_rate_table(), os.path.join(export_path, "Success Rate Table.png"))
        export_png(self.plot_spawning_success_rates(), os.path.join(export_path, "Spawning Success Rates.png"))
        export_png(self.plot_fish_born_per_year(), os.path.join(export_path, "Fish Born Per Year.png"))
        export_png(self.plot_survivor_count(12), os.path.join(export_path, "Number Surviving to 12 Weeks.png"))
        export_png(self.plot_survivor_proportion(12), os.path.join(export_path, "Proportion Surviving to 12 Weeks.png"))
        export_png(self.plot_freshwater_growth_rates(), os.path.join(export_path, "Freshwater Growth Rates.png"))
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
            passage_plots = self.passage_report();
            for passage_plot, title in passage_plots:
                export_png(passage_plot, os.path.join(export_path, "Passage - {0}.png".format(title)))
        print("Report export complete.")


