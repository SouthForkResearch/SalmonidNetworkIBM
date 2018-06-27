import math
import os
import pickle
import shutil
from .settings import export_settings

class DominanceBasedActivation:
    """ Custom scheduler completely replaces the Mesa framework's BaseScheduler rather than subclassing
        it, because we need to track two separate collections of agents, Fish and Redds. """

    model = None
    steps = 0
    time = 0
    fish = []
    redds = []

    def __init__(self, model, weeks_per_year):
        self.model = model
        self.steps = 0
        self.time = 0
        self.fish = []
        self.redds = []
        self.weeks_per_year = weeks_per_year
        self.current_year = 0
        self.week_of_year = 0
        self.recent_dead_fish = []
        self.loaded_dead_fish = []
        self.dead_fish_logs_loaded = True   # set to false whenever there are new dead fish logs dumped but not loaded

    def step(self):
        """ Executes the step of all fish, one at a time, with the largest going first. """
        self.current_year = math.floor(self.time / self.weeks_per_year)
        self.week_of_year = self.time % self.weeks_per_year
        self.fish.sort(key=lambda fish: -fish.fork_length)
        for fish in self.fish:
            fish.step()
        for redd in self.redds:
            redd.step()
        self.model.network.step(self.steps)
        self.redds = [redd for redd in self.redds if not redd.is_dead]
        self.fish = [fish for fish in self.fish if not fish.is_dead]
        if self.current_year > 0 and self.week_of_year == 0:
            self.log_dead_fish()
        self.steps += 1
        self.time += 1

    @property
    def dead_fish(self):
        """ This property returns all dead fish, loading them from files if they aren't already loaded. """
        if not self.dead_fish_logs_loaded:
            self.loaded_dead_fish = []
            cache_path = export_settings['DEAD_FISH_CACHE_PATH']
            if not os.path.exists(cache_path):
                return self.recent_dead_fish
            for file_name in os.listdir(cache_path):
                print("Loading cached dead fish from {0}.".format(file_name))
                file_path = os.path.join(cache_path, file_name)
                with open(file_path, 'rb') as file:
                    p = pickle.Unpickler(file)
                    self.loaded_dead_fish += p.load()
            print("Reconnecting cached dead fish to the model for analysis.")
            for fish in self.loaded_dead_fish:
                fish.reconnect_from_pickling(self.model)
            self.dead_fish_logs_loaded = True
        return self.loaded_dead_fish + self.recent_dead_fish

    def log_dead_fish(self):
        """ Called once a year on Jan 1st, this function writes all dead fish to a file to remove them from memory. """
        cache_path = export_settings['DEAD_FISH_CACHE_PATH']
        if self.current_year == 1:  # if writing the first logs, empty and re-create the log directory
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path)
            os.makedirs(cache_path)
        log_file_name = 'dead_fish_year_{0}.pickle'.format(self.current_year - 1)
        log_file_path = os.path.join(cache_path, log_file_name)
        with open(log_file_path, mode='wb') as log_file:
            print("Beginning year {0}, writing previous year's dead fish to log file {1}.".format(self.current_year, log_file_name))
            p = pickle.Pickler(log_file)
            for fish in self.recent_dead_fish:
                fish.disconnect_for_pickling()
            p.dump(self.recent_dead_fish)
            self.recent_dead_fish = []
        self.dead_fish_logs_loaded = False

    @property
    def all_fish(self):
        return self.fish + self.dead_fish

    def add_fish(self, agent):
        self.fish.append(agent)

    def add_redd(self, agent):
        self.redds.append(agent)

    @property  # could gain a bit of speed by tracking these as variables instead of calculating whenever called
    def fish_count(self):
        return len(self.fish)

    @property
    def redd_count(self):
        return len(self.redds)

    def week_of_year_is_within(self, start_week, end_week):
        return start_week <= self.week_of_year <= end_week