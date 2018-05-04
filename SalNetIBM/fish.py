from mesa import Agent
import random
from bokeh.models import HoverTool, Label, ColumnDataSource, Arrow, VeeHead, TableColumn, DataTable, LinearAxis, Range1d
from bokeh.layouts import column, row
from bokeh.plotting import figure
import numpy as np

from .settings import time_settings, resident_fish_settings, anadromous_fish_settings, spawning_settings
from .bioenergetics import daily_growth_from_p, mass_at_length, length_at_mass

from enum import Enum, auto

class Sex(Enum):
    MALE = auto()
    FEMALE = auto()

class LifeHistory(Enum):
    ANADROMOUS = auto()
    RESIDENT = auto()

class Origin(Enum):
    BORN = auto()
    INITIATED = auto()

class Activity(Enum):
    FRESHWATER_GROWTH = auto()
    RANDOM_DISPERSAL = auto()
    COMPETITIVE_DISPERSAL = auto()
    SUMMER_COLD_SEEKING = auto()
    FALL_WARMTH_SEEKING = auto()
    SMOLT_OUTMIGRATION = auto()
    SALTWATER_GROWTH = auto()
    SPAWNING_MIGRATION = auto()
    SPAWNING = auto()
    POSTSPAWN_RETURN_HOME = auto()
    KELT_OUTMIGRATION = auto()

class Movement(Enum):
    STATIONARY = auto()
    UPSTREAM = auto()
    DOWNSTREAM = auto()
    RANDOM = auto()
    SEEKING_SPAWNING_REACH = auto()
    SEEKING_HOME_REACH = auto()

class Fish(Agent):
    """ A single O. mykiss individual."""
    def __init__(self, unique_id, model, network_reach, life_history, redd):
        super().__init__(unique_id, model)
        self.network_reach = network_reach
        self.network_reach.fish.append(self)
        self.natal_reach = network_reach  # should never change
        self.spawning_reach = network_reach  # usually stays as natal reach, but can change to stray
        self.home_reach = network_reach  # home reach for feeding residents
        self.life_history = life_history
        if life_history is LifeHistory.ANADROMOUS and (random.random() < spawning_settings['STRAY_PROBABILITY']
                                                       or not self.spawning_reach.is_within_steelhead_extent):
            self.spawning_reach = network_reach.network.random_reach(True)
        if redd is None:  # only for the fish created when initializing the model
            self.position_within_reach = random.uniform(0, network_reach.length)
            self.origin = Origin.INITIATED
        else:
            self.position_within_reach = redd.position_within_reach
            self.origin = Origin.BORN
        self.sex = random.choice([Sex.MALE, Sex.FEMALE])
        self.fork_length = 35
        self.mass = 0.5
        self.stray = False
        self.lifetime_maximum_mass = 0.5
        self.birth_week = model.schedule.time
        self.death_week = None
        self.age_weeks = 0
        self.ocean_entry_week = None
        self.ocean_age_weeks = 0
        self.mortality_reason = None
        self.p = 0.4 + 0.05 * random.normalvariate(0, 1)
        self.settings = resident_fish_settings if self.is_resident else anadromous_fish_settings
        self.should_spawn_this_year = False
        self.has_spawned_this_year = False
        self.is_small = True
        self.is_medium = False
        self.is_dead = False  # flag used to mark fish when they die, for more efficient mass deletion once per timestep

        self.activity = Activity.FRESHWATER_GROWTH
        self.activity_duration = 0
        self.movement_mode = Movement.STATIONARY
        self.movement_rate = 0
        self.current_route = None
        self.current_route_position = 0

        self._event_log_index = -1  # internal increment for event logs, accessed via property that increments it
        self.event_history = [(self.event_log_index, 0, "Born into reach {0}".format(self.natal_reach.id))]
        self.reach_history = [(self.event_log_index, 0, self.natal_reach.id)]
        self.activity_history = [(self.event_log_index, 0, self.activity)]
        self.movement_history = [(self.event_log_index, 0, self.movement_mode, self.movement_rate)]
        self.mass_history = []
        self.length_history = []
        self.temperature_history = []

    @property
    def event_log_index(self):
        self._event_log_index += 1
        return self._event_log_index

    @property
    def is_resident(self):
        return self.life_history is LifeHistory.RESIDENT

    @property
    def is_anadromous(self):
        return self.life_history is LifeHistory.ANADROMOUS

    @property
    def temperature(self):
        return self.network_reach.temperature_at_week(self.model.schedule.time)

    @property
    def is_mature(self):
        is_old_enough = self.age_weeks >= self.settings['AGE_AT_MATURITY']
        if self.is_resident:
            return is_old_enough
        else:  # anadromous fish aren't "mature" until they've been to the ocean
            return is_old_enough and self.ocean_entry_week is not None

    def set_activity(self, activity):
        if activity is Activity.SALTWATER_GROWTH and self.ocean_entry_week is None:
            print("Setting an ocean fish that isn't in the ocean")
        if self.activity is not activity:
            self.activity = activity
            self.activity_duration = 0
            self.activity_history.append((self.event_log_index, self.age_weeks, self.activity))

    def set_movement(self, movement_mode, movement_rate=0):
        self.movement_mode = movement_mode
        self.movement_rate = movement_rate
        self.movement_history.append((self.event_log_index, self.age_weeks, movement_mode, movement_rate))

    def log_event(self, description):
        self.event_history.append((self.event_log_index, self.age_weeks, description))

    def set_spawning_reach(self, reach):
        self.log_event("Set spawning reach = {0}".format(reach.id))
        self.spawning_reach = reach

    def set_home_reach(self, reach):
        self.log_event("Set home reach = {0}".format(reach.id))
        self.home_reach = reach

    @property
    def age_years(self):
        return self.age_weeks / time_settings['WEEKS_PER_YEAR']

    def current_habitat_preferences(self):
        temperature_key = int(round(self.temperature))
        if temperature_key < 1:
            temperature_key = 1
        if temperature_key > 20:
            temperature_key = 20
        lengths_for_temperature = np.array(list(self.network_reach.network.habitat_preferences[temperature_key].keys()))
        length_key = lengths_for_temperature[(np.abs(lengths_for_temperature - self.fork_length)).argmin()]
        return self.network_reach.network.habitat_preferences[temperature_key][length_key]

    def step(self):
        if self.model.schedule.week_of_year == 0:
            self.has_spawned_this_year = False
            self.should_spawn_this_year = True
            if self.is_anadromous:
                ocean_age_years = self.ocean_age_weeks / time_settings['WEEKS_PER_YEAR']
                if ocean_age_years >= 1:
                    rand = random.random()
                    if 1 <= ocean_age_years < 2:
                        self.should_spawn_this_year = True if rand < 0.07 else False
                    elif 2 <= ocean_age_years < 3:
                        self.should_spawn_this_year = True if rand < 0.6 else False
                    elif 3 <= ocean_age_years < 4:
                        self.should_spawn_this_year = True if rand < 0.76 else False
                    else:
                        self.should_spawn_this_year = True

        # Record history
        self.length_history.append(self.fork_length)
        self.mass_history.append(self.mass)
        self.temperature_history.append(self.temperature)

        self.dispatch_activities()

        if self.movement_mode is not Movement.STATIONARY:
            self.move()

        self.activity_duration += 1
        self.age_weeks += 1
        self.ocean_age_weeks += 1 if self.network_reach.is_ocean else 0

        if self.activity in (Activity.FRESHWATER_GROWTH, Activity.SALTWATER_GROWTH,
                             Activity.SUMMER_COLD_SEEKING, Activity.FALL_WARMTH_SEEKING,
                             Activity.RANDOM_DISPERSAL):
            self.grow()  # should smolts be growing, too?

        elif self.activity is Activity.COMPETITIVE_DISPERSAL:
            self.grow(self.settings['DISPLACED_FISH_RATION_FACTOR'] * self.p)  # fish being displaced by competitors get less food than usual

        self.possible_mortality()

    def dispatch_activities(self):
        # Anadromous fish ready to smolt start toward the ocean

        if self.activity is Activity.FRESHWATER_GROWTH \
                and self.life_history is LifeHistory.ANADROMOUS \
                and self.fork_length >= self.settings['SMOLT_MIN_FORK_LENGTH'] \
                and self.model.schedule.week_of_year_is_within(self.settings['SMOLT_OUTMIGRATION_START'],
                        self.settings['SMOLT_OUTMIGRATION_END']):
            self.set_activity(Activity.SMOLT_OUTMIGRATION)
            self.set_movement(Movement.DOWNSTREAM, self.settings['SMOLT_OUTMIGRATION_SPEED'])

        # Smolts arriving at the ocean stay there

        elif self.activity is Activity.SMOLT_OUTMIGRATION and self.network_reach.is_ocean:
            self.ocean_entry_week = self.model.schedule.time
            self.set_activity(Activity.SALTWATER_GROWTH)
            self.set_movement(Movement.STATIONARY)

        # Fish in hot water during the summer seek cold water and stop when they get there

        elif self.activity is Activity.FRESHWATER_GROWTH \
                and self.temperature > 24 \
                and self.model.schedule.week_of_year_is_within(self.settings['SUMMER_COLD_SEEKING_START'],
                    self.settings['SUMMER_COLD_SEEKING_END']):
            self.set_activity(Activity.SUMMER_COLD_SEEKING)
            cold_seeking_rate = 0.4 if self.is_small else 1.0  # approximates Yoy/OnePlus division in HexSim
            self.set_movement(Movement.UPSTREAM, cold_seeking_rate)

        elif self.activity is Activity.SUMMER_COLD_SEEKING \
                and self.temperature <= 20:
            self.set_activity(Activity.FRESHWATER_GROWTH)
            self.set_movement(Movement.STATIONARY)

        # A small proportion of large fish in cold water during the fall seek warmer water, but stop 5th -order
        # or after 4 weeks, whichever comes first, if they don't find it
        # COMMENTED OUT because right now, there is no warm water within the desired range to seek!
        # elif self.activity is Activity.FRESHWATER_GROWTH \
        #         and self.model.schedule.week_of_year_is_within(self.settings['FALL_WARMTH_SEEKING_START'],
        #             self.settings['FALL_WARMTH_SEEKING_END']) \
        #         and self.fork_length > 180 \
        #         and random.random() < 0.2 \
        #         and not 10 <= self.temperature <= 20:
        #     self.set_activity(Activity.FALL_WARMTH_SEEKING)
        #     self.set_movement(Movement.DOWNSTREAM, self.settings['FALL_WARMTH_SEEKING_RATE'])
        #
        # elif self.activity is Activity.FALL_WARMTH_SEEKING \
        #         and (10 <= self.temperature <= 20
        #              or self.network_reach.strahler_order >= 5
        #              or self.activity_duration > 3):
        #     self.set_activity(Activity.FRESHWATER_GROWTH)
        #     self.set_movement(Movement.STATIONARY)

        # A small proportion of freshwater fish randomly disperse during week 37

        elif self.activity is Activity.FRESHWATER_GROWTH \
                and self.fork_length > 180 \
                and random.random() < 0.002:  # this 0.002 weekly chance gives a 9 % annual chance of random dispersal
            self.set_activity(Activity.RANDOM_DISPERSAL)
            self.set_movement(Movement.RANDOM, 5)

        elif self.activity is Activity.RANDOM_DISPERSAL \
                and random.random() < 0.25:  # a randomly dispersing fish has a 25 % chance of stopping any given week
            self.set_activity(Activity.FRESHWATER_GROWTH)
            self.set_movement(Movement.STATIONARY)
            self.set_home_reach(self.network_reach)
            if self.life_history is LifeHistory.RESIDENT and self.network_reach.capacity_redds > 0:
                self.set_spawning_reach(self.network_reach)

        # Fish exceeding the capacity of their reach are forced to disperse

        elif self.activity in (Activity.FRESHWATER_GROWTH, Activity.COMPETITIVE_DISPERSAL, Activity.RANDOM_DISPERSAL,
                               Activity.SUMMER_COLD_SEEKING, Activity.FALL_WARMTH_SEEKING) \
                and ((self.is_small and self.network_reach.small_fish_count > self.network_reach.capacity_small_fish)
                 or (self.is_medium and self.network_reach.medium_fish_count > self.network_reach.capacity_medium_fish)):
            # Each network reach has a fixed # of spots available (and unoccupied) at the start of each timestep,
            # as determined by its capacity. Because fish are stepped through in order from largest to smallest, the
            # large ones will fill the appropriate capacity first and the small ones have to move.
            needs_to_move = False
            if self.is_small:
                self.network_reach.small_fish_spots_available -= 1
                needs_to_move = self.network_reach.small_fish_spots_available < 0
            elif self.is_medium:
                self.network_reach.medium_fish_spots_available -= 1
                needs_to_move = self.network_reach.medium_fish_spots_available < 0
            if needs_to_move:
                if self.activity is not Activity.COMPETITIVE_DISPERSAL:
                    self.set_activity(Activity.COMPETITIVE_DISPERSAL)
                if self.movement_mode is Movement.STATIONARY:
                    self.set_movement(Movement.RANDOM, 1)
            else:
                if self.activity is Activity.COMPETITIVE_DISPERSAL:
                    self.set_activity(Activity.FRESHWATER_GROWTH)
                    self.set_movement(Movement.STATIONARY)
                    self.set_home_reach(self.network_reach)

        # Mature fish ready to spawn start seeking their natal reach

        elif self.is_mature \
                and not self.has_spawned_this_year \
                and self.activity not in (Activity.SPAWNING_MIGRATION, Activity.SPAWNING) \
                and self.model.schedule.week_of_year_is_within(self.settings['SPAWNING_MIGRATION_START'],
                        self.settings['SPAWNING_MIGRATION_END']) \
                and self.should_spawn_this_year:
            self.set_activity(Activity.SPAWNING_MIGRATION)
            self.set_movement(Movement.SEEKING_SPAWNING_REACH, self.settings['SPAWNING_MIGRATION_SPEED'])

        # Spawning fish arrive at the spawning grounds, possibly after going astray

        elif self.activity is Activity.SPAWNING_MIGRATION:
            if self.network_reach == self.spawning_reach and not self.stray:
                if len(self.network_reach.redds) >= self.network_reach.capacity_redds:
                    self.stray = True
                    self.log_event("Straying due to redd capacity")
                    self.set_movement(Movement.RANDOM, self.movement_rate)
                else:
                    self.set_activity(Activity.SPAWNING)
            elif self.stray:
                if self.sex is Sex.FEMALE:  # female strays stop at the first open place to build a redd
                    if len(self.network_reach.redds) < self.network_reach.capacity_redds:
                        self.set_activity(Activity.SPAWNING)
                else:  # male strays stop at the first spawning females
                    spawning_females = [fish for fish in self.network_reach.fish if fish.sex is Sex.FEMALE
                                        and fish.activity is Activity.SPAWNING]
                    if len(spawning_females) > 0:
                        self.set_activity(Activity.SPAWNING)
                        self.set_movement(Movement.STATIONARY)

        # Female spawners (as set by above code, on a previous timestep) spawn

        elif self.activity is Activity.SPAWNING and self.sex is Sex.FEMALE:
            self.female_spawn()

        # Male spawners cease to be spawners if there haven't been any females around for a long time

        elif self.activity is Activity.SPAWNING and self.sex is Sex.MALE \
                and self.activity_duration >= spawning_settings['MAX_WEEKS_TO_WAIT_WITHOUT_MATE']:
            self.post_spawn(False)

        # Kelts heading to the ocean (triggered in self.post_spawn()) stop when they get there

        elif self.activity is Activity.KELT_OUTMIGRATION and self.network_reach.is_ocean:
            self.set_activity(Activity.SALTWATER_GROWTH)
            self.set_movement(Movement.STATIONARY)

        # Residents postspawn stop when they get to their home reach

        elif self.activity is Activity.POSTSPAWN_RETURN_HOME and self.network_reach is self.home_reach:
            self.set_activity(Activity.FRESHWATER_GROWTH)
            self.set_movement(Movement.STATIONARY)

        # Fish that reach the end of the spawning period without finding spawning grounds give up
        # NEED TO RETHINK THIS PART A BIT!!!

        # elif self.activity in (Activity.SPAWNING_MIGRATION, Activity.SPAWNING) and not \
        #         self.model.schedule.week_of_year_is_within(self.settings['SPAWNING_MIGRATION_START'],
        #             self.settings['SPAWNING_MIGRATION_END']):
        #     self.post_spawn(False)

    def female_spawn(self):
        possible_mates = [fish for fish in self.network_reach.fish if fish.sex is Sex.MALE
                          and fish.activity is Activity.SPAWNING and not fish.has_spawned_this_year]
        if len(possible_mates) == 0:
            if self.activity_duration >= spawning_settings['MAX_WEEKS_TO_WAIT_WITHOUT_MATE']:
                self.post_spawn(False)
            return  # if no males around, just wait until one shows up
        else:
            preferred_mates = [mate for mate in possible_mates if mate.life_history == self.life_history]
            if len(preferred_mates) > 0:
                mate = random.choice(preferred_mates)
            else:
                mate = random.choice(possible_mates)
            self.model.add_redd(self)
            self.post_spawn(True)
            mate.post_spawn(True)

    def post_spawn(self, succeeded):
        self.has_spawned_this_year = True
        self.log_event("Successfully spawned" if succeeded else "Failed to spawn")
        survival_probability = self.settings['MALE_POSTSPAWN_SURVIVAL_PROBABILITY'] if self.sex is Sex.MALE \
            else self.settings['FEMALE_POSTSPAWN_SURVIVAL_PROBABILITY']
        if random.random() > survival_probability:
            self.die("Post-spawn mortality ({0})".format("successful" if succeeded else "unsuccessful"))
        else:
            if self.life_history is LifeHistory.ANADROMOUS:
                self.set_activity(Activity.KELT_OUTMIGRATION)
                self.set_movement(Movement.DOWNSTREAM, self.settings['POSTSPAWN_RETURN_RATE'])
            else:
                self.set_activity(Activity.POSTSPAWN_RETURN_HOME)
                self.set_movement(Movement.SEEKING_HOME_REACH, self.settings['POSTSPAWN_RETURN_RATE'])

    def move(self):
        initial_network_reach = self.network_reach
        if self.movement_mode is Movement.RANDOM:  # "Random" movement picks randomly once, then sticks with it.
            random_mode = random.choice([Movement.UPSTREAM, Movement.DOWNSTREAM])
            self.set_movement(random_mode, self.movement_rate)
        if self.movement_mode in (Movement.UPSTREAM, Movement.DOWNSTREAM):
            anadromy_allowed = self.activity in (Activity.SMOLT_OUTMIGRATION, Activity.KELT_OUTMIGRATION)
            self.network_reach, self.position_within_reach, stop = \
                self.network_reach.network.position_after_movement(self.network_reach,
                                                                   self.movement_mode,
                                                                   self.position_within_reach,
                                                                   self.movement_rate,
                                                                   self.life_history,
                                                                   anadromy_allowed)
            if stop:
                self.set_movement(Movement.STATIONARY)
        elif self.movement_mode in (Movement.SEEKING_HOME_REACH, Movement.SEEKING_SPAWNING_REACH):
            if self.current_route is None:
                if self.movement_mode == Movement.SEEKING_SPAWNING_REACH:
                    destination = self.spawning_reach
                else:
                    destination = self.home_reach
                if self.network_reach == destination:
                    self.set_movement(Movement.STATIONARY)
                    self.current_route = None
                    return
                self.current_route = self.network_reach.network.route(self.network_reach,
                                                                      destination,
                                                                      self.position_within_reach,
                                                                      self.movement_rate)
                self.current_route_position = 0
            else:
                if self.current_route_position < len(self.current_route) - 1:
                    self.current_route_position += 1
            self.network_reach, self.position_within_reach = self.current_route[self.current_route_position]
            if self.current_route_position == len(self.current_route) - 1:  # ADDED THE -1 HERE TO FIX THE PROBLEM
                self.set_movement(Movement.STATIONARY)
                self.current_route = None
        if self.network_reach != initial_network_reach:
            initial_network_reach.fish.remove(self)
            self.network_reach.fish.append(self)
            self.reach_history.append((self.event_log_index, self.age_weeks, self.network_reach.id))


    def grow(self, override_p=None):
        if not self.network_reach.is_ocean:
            p = self.p if override_p is None else override_p  # allows overriding normal p-value for special situations
            dg = daily_growth_from_p(self.temperature, self.mass, p)
            weekly_growth_multiplier = (1 + dg) ** time_settings['DAYS_PER_WEEK']
            self.mass = self.mass * weekly_growth_multiplier
            if self.mass > self.lifetime_maximum_mass:
                self.lifetime_maximum_mass = self.mass
                self.fork_length = length_at_mass(self.mass)
            if self.mass < self.settings['STARVATION_THRESHOLD'] * self.lifetime_maximum_mass:
                self.die("Starvation")
        else:
            self.fork_length = self.fork_length + 20.337 * self.ocean_age_weeks ** -0.476
            self.mass = mass_at_length(self.fork_length)
            self.lifetime_maximum_mass = self.mass
        if self.is_small and self.fork_length >= 100:
            self.is_small = False
            self.is_medium = True
        elif self.is_medium and self.fork_length > 180:
            self.is_medium = False

    def possible_mortality(self):
        """ Currently this uses the same size-based model for anadromous spawners as other freshwater fish,
            and only uses a different model when they're out in the ocean. """
        if not self.network_reach.is_ocean:
            L = self.fork_length
            if self.model.schedule.week_of_year_is_within(1, 19):  # winter -- WATCH THE INDEXING WITH 0/1 START
                surv_prob = 0.00055*L + 0.921 if L <= 100 else 0.976
            elif self.model.schedule.week_of_year_is_within(20, 32):  # summer
                surv_prob = 0.00026 * L + 0.968 if L <= 100 else 0.994
            else:  # weeks 33-46; fall
                surv_prob = 0.00039 * L + 0.988 if L <= 100 else 0.988
        else:
            surv_prob = 0.9952 # used for "anadromous adults" in HexSim, fish in ocean here
        if random.random() > surv_prob:
            self.die("Survival probability model")

    def age_at_timestep(self, timestep):
        """ Gives the age in weeks of the fish at a given timestep of the overall model's schedule. If the fish
            wasn't born yet, returns -1. If the fish is already dead, returns -2."""
        if timestep < self.birth_week:
            return -1
        elif self.is_dead and timestep > self.death_week:
            return -2
        else:
            return timestep - self.birth_week

    def activity_at_age(self, age_weeks):
        previous_activity = self.activity_history[0][2]
        for activity_timestep, activity in self.activity_history:
            if activity_timestep >= age_weeks:
                return previous_activity
            previous_activity = activity
        return self.activity_history[-1][2]

    def length_at_age(self, age):
        return self.length_history[age]

    def mass_at_age(self, age):
        return self.mass_history[age]

    def activity_descriptors(self):
        activity_descriptors = [(x[0], x[1], "{0}.".format(x[2])) for x in self.activity_history]
        reach_descriptors = [(x[0], x[1], "Reach {0}.".format(x[2])) for x in self.reach_history]
        movement_descriptors = [(x[0], x[1], "{0} at rate {1}.".format(x[2], x[3])) for x in
                                self.movement_history]
        event_descriptors = [(x[0], x[1], "{0}.".format(x[2])) for x in self.event_history]
        descriptors = sorted(activity_descriptors + movement_descriptors + reach_descriptors + event_descriptors,
                             key=lambda x: x[0])
        if self.is_dead:
            title = "{7} {0} {1} id {8} lived to age {2:.2f} ({3} weeks) and died at length {4:.0f} mm ({5:.1f} g) from '{6}'".format(
                self.life_history.name, self.sex.name, self.age_years, self.age_weeks, self.fork_length, self.mass,
                self.mortality_reason, self.origin.name, self.unique_id)
        else:
            title = "{6} {0} {1} id {7} is still alive at age {2:.2f} ({3} weeks) with current length {4:.0f} mm ({5:.1f} g).".format(
                self.life_history.name, self.sex.name, self.age_years, self.age_weeks, self.fork_length, self.mass,
                self.origin.name, self.unique_id)
        lifetext = ""
        for descriptor in descriptors:
            lifetext += descriptor[2] + "\n"
        source = ColumnDataSource({'age_weeks': [d[1] for d in descriptors],
                                   'age_years': [d[1] / time_settings['WEEKS_PER_YEAR'] for d in descriptors],
                                   'life_event': [d[2] for d in descriptors]
                                   })
        return title, lifetext, source

    def plot(self):
        lifemap = figure(plot_width=750, plot_height=570, toolbar_location='below')
        lifemap.xgrid.visible = False
        lifemap.ygrid.visible = False
        lifemap.xaxis.visible = False
        lifemap.yaxis.visible = False
        self.network_reach.network.plot(lifemap)
        reachids = list(np.array(self.reach_history).T[2])
        pointx, pointy = list(np.array([self.network_reach.network.reach_with_id(id).midpoint for id in reachids]).T)
        source = ColumnDataSource({'xs': pointx,
                                   'ys': pointy,
                                   'reach_id': reachids})
        lifemap.scatter('xs', 'ys', source=source, name='scatterplot', marker='circle', size=10,
                        line_color='#cb7723', fill_color='#fcb001', alpha=1.0)
        hover_tooltips = [('reach', '@reach_id')]
        lifemap.add_tools(HoverTool(tooltips=hover_tooltips, names=['scatterplot']))
        lifemap.add_layout(Label(x=30, y=700, x_units='screen', y_units='screen', text="Fish ID {0}".format(self.unique_id)))
        title, lifetext, lifesource = self.activity_descriptors()
        lifemap.title.text = title
        lifemap.title.text_font_size = "10px"
        lifemap.toolbar.logo = None
        for i in range(1, len(pointx)):
            lifemap.add_layout(Arrow(end=VeeHead(size=10, line_color='#cb7723', fill_color='#fcb001'), line_color='#fcb001',
                                     x_start=pointx[i - 1], y_start=pointy[i - 1], x_end=pointx[i], y_end=pointy[i]))
        columns = [
                TableColumn(field="age_weeks", title="Week", width=40),
                TableColumn(field="age_years", title="Age", width=45),
                TableColumn(field="life_event", title="Life Event", width=315)
            ]
        data_table = DataTable(source=lifesource, columns=columns, row_headers=False, width=400, height=600)
        lyt = row(
                [data_table,
                lifemap,
                column([self.plot_growth(), self.plot_temperature()])],
            sizing_mode='fixed')
        return lyt

    def plot_growth(self):
        source = ColumnDataSource({'age': list(np.arange(len(self.mass_history)) / time_settings['WEEKS_PER_YEAR']),
                                   'mass': self.mass_history,
                                   'length': self.length_history})
        fig = figure(tools=[], plot_width=350, plot_height=280)
        fig.extra_y_ranges = {'length_range': Range1d(start=min(self.length_history)-3, end=max(self.length_history)+3)}
        fig.xaxis.axis_label = 'Age (years)'
        fig.yaxis.axis_label = 'Mass (g)'
        fig.add_layout(LinearAxis(y_range_name='length_range', axis_label='Fork length (mm)'), 'right')
        fig.line('age', 'mass', source=source, line_width=2, legend='Mass', line_color='forestgreen')
        fig.line('age', 'length', source=source, y_range_name='length_range', line_width=2, legend='Length', line_color='slateblue', line_dash='dotted')
        fig.legend.location = 'top_left'
        fig.toolbar.logo = None
        return fig

    def plot_temperature(self):
        source = ColumnDataSource({'age': list(np.arange(len(self.mass_history)) / time_settings['WEEKS_PER_YEAR']),
                                   'temperature': self.temperature_history})
        fig = figure(tools=[], plot_width=350, plot_height=280)
        fig.line('age', 'temperature', source=source, line_width=2, line_color='firebrick')
        fig.xaxis.axis_label = 'Age (years)'
        fig.yaxis.axis_label = 'Temperature (C)'
        fig.toolbar.logo = None
        return fig

    def die(self, reason):
        """ We don't delete the object here, because each deletion is an O(n) operation on the very large list of fish
            in the overall model and its network cell. It's a huge computational time-saver (more than half of model
            runtime) to flag fish for deletion and remove them the fish arrays together at the end of each timestep."""
        self.is_dead = True
        self.death_week = self.model.schedule.time
        self.mortality_reason = reason
        self.log_event("Died from {0}".format(reason))
        self.model.schedule.dead_fish.append(self)
