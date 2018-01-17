import math
import sys
import numpy as np
import functools
from .fish import LifeHistory


class NetworkReach:
    """ The network is represented as a collection of reaches. """

    def __init__(self, network, attribs, points, from_node, to_node):
        self.network = network
        self.id = attribs['LineOID']
        self.from_node = from_node
        self.to_node = to_node
        self.points = points
        self.downstream_reach = None
        self.upstream_reaches = []
        self.length_m = attribs['Shape_Leng']  # convert from meters in shapefile to km in model
        self.length = self.length_m / 1000  # use length in km for most of the model
        self.bank_full_width = attribs['BFW_M']
        self.strahler_order = attribs['strm_ord']
        self.spring95 = attribs['Winter95']  # SPRING95 ISN'T IN THE NETWORK
        self.area = self.length_m * self.bank_full_width  # area is in m2
        self.capacity_redds = attribs['rdd_M2'] * self.area
        self.area_solar = attribs['area_solar']
        self.conductivity = attribs['prdCond']
        self.gnis_name = attribs['GNIS_Name']
        self.huc10_name = attribs['HUC10NmNRC']
        self.huc12_name = attribs['HUC12NmNRC']
        self.gradient = attribs['GRADIENT']
        self.is_within_steelhead_extent = (attribs['steel_anad'] == 1)
        self.is_ocean = False
        self.is_migration_reach = False
        self.fish = []
        self.redds = []
        self.temperatures = []
        self.small_fish_count = 0
        self.medium_fish_count = 0
        self.capacity_small_fish = math.ceil(0.02 * self.area / self.strahler_order**2 + 0.5)
        self.capacity_medium_fish = math.ceil(0.01 * self.area / self.strahler_order**2 + 0.5)
        self.small_fish_spots_available = self.capacity_small_fish
        self.medium_fish_spots_available = self.capacity_medium_fish
        self.history = []
        self.calculate_midpoint()

    def set_temperatures(self, temperatures):
        self.temperatures = temperatures

    def temperature_at_week(self, week_of_simulation):
        """ Input the week of the simulation, not week of year. Temperatures from the input file are
            assumed to cyclically repeat. One year of temperatures is fine, but we could put in a 20+ year
            cycle or something with temperatures rising or falling from year to year, and it should still
            work fine. Another alternative would be to build into this a 'year' check and hard-code or build
            some system to modify temperatures in certain years."""
        if self.is_ocean or self.is_migration_reach:
            return self.network.most_downstream_reach.temperature_at_week(week_of_simulation)
        else:
            return self.temperatures[week_of_simulation % len(self.temperatures)]

    @functools.lru_cache(maxsize=None)
    def gpp_at_week(self, week_of_simulation):
        temperature = self.temperature_at_week(week_of_simulation)
        log_gpp = -11.538 + 0.00827 * self.conductivity + 4.11e-6 * self.area_solar + 0.538 * temperature
        return math.exp(log_gpp)

    def create_habitat_boxes(self):
        """ Ideally, we just have some numbers we can subtract/add when fish enter/leave.

            Every fish gets food dependent on recent GPP in the area and the size of the area it inhabits.

            The first/largest/dominant fish gets all the space it wants, but should have little to no effect on
            smaller fish in slower/shallower microhabitats.

            The "boxes" available depend on the fish trying to inhabit them. Smaller fish take up less space. So
            we want some indicator of territory size.

            How do we have fish of different sizes competing for different "pools" of space?

            Space consists of hundreds of tiny boxes of (depth, velocity). Each fish has some range of tolerable
            depth and tolerable velocity, and it chooses the boxes within that range that would most closely maximize
            its NREI under the prevailing conditions, taking enough boxes to fill its territory size. If there aren't
            enough boxes in the acceptable range to fill its territory size, it goes into competitive dispersal

        """
        pass

    def calculate_midpoint(self):
        npoints = len(self.points)
        if npoints == 0:
            return
        elif npoints % 2 == 0:
            self.midpoint = list(np.mean(self.points[int(npoints / 2 - 1):int(npoints / 2 + 1)], axis=0))
        else:
            self.midpoint = self.points[int(np.floor(npoints / 2))]

    def step(self, timestep):
        # could also speed things up by flagging whether any fish died and not doing the 2 lines below if nothing died
        self.small_fish_spots_available = self.capacity_small_fish
        self.medium_fish_spots_available = self.capacity_medium_fish
        self.small_fish_count = len([fish for fish in self.fish if fish.is_small])
        self.medium_fish_count = len([fish for fish in self.fish if fish.is_medium])
        self.redds = [redd for redd in self.redds if not redd.is_dead]
        self.fish = [fish for fish in self.fish if not fish.is_dead]
        self.history.append({'step': timestep,
                             'anadromous': len([fish for fish in self.fish
                                                if fish.life_history == LifeHistory.ANADROMOUS]),
                             'resident': len([fish for fish in self.fish
                                              if fish.life_history == LifeHistory.RESIDENT]),
                             'n_redds': len(self.redds),
                             'small': self.small_fish_count,
                             'medium': self.medium_fish_count
                             })

    def reach_statistic(self, value, timestep=None):
        """This saves some space in the history-logging dictionary for values that can be calculated from those using
           other, static attributes of the reach. It also allows a single function call from plotting functions to
           retrieve either a static attribute of the reach (if timestep is None) or a dynamic element of the reach's
           history (if timestep is not None)."""

        if hasattr(self, value):
            return getattr(self, value)
        elif timestep is not None:
            step_history = self.history[timestep]
            if value in step_history.keys():
                return step_history[value]
            elif value == 'temperature':
                return self.temperature_at_week(timestep)
            elif value == 'population':
                return step_history['anadromous'] + step_history['resident']
            elif value == 'proportion_capacity_redds':
                return step_history['n_redds'] / self.capacity_redds
            elif value == 'proportion_capacity_small':
                return step_history['small'] / self.capacity_small_fish
            elif value == 'proportion_capacity_medium':
                return step_history['small'] / self.capacity_medium_fish
            else:
                sys.exit("Invalid reach history value requested.")
        else:
            sys.exit("Requested reach history value that isn't a reach attribute, but without a timestep.")

    def passage_stats(self, activity, direction, life_history='both'):  # self = a network reach
        """ How this is supposed to work:
                - To check that a fish passed downstream of this reach (self), we check that it is currently in the
                  path downstream from this reach, and that this reach either is its previous position, or is in the
                  the path downstream from its previous position. That second part avoids recording a downstream passage
                  when a fish enters the lower mainstem and appears downstream of this one, but it came from a different
                  branch rather than passing through this one.
                - To check that a fish passed upstream of this reach, we check that this reach is in the path downstream
                  from its current position, and that its previous position either is this reach was in the path downstream
                  from this reach.
        """
        all_fish = self.network.model.schedule.fish + self.network.model.schedule.dead_fish
        downstream_reach_ids = [reach.id for reach in self.network.path_downstream_from_reach(self)]
        downstream_passage_records = []
        upstream_passage_records = []
        progress = 0
        if life_history == 'resident':
            possible_fish = [fish for fish in all_fish if fish.life_history is LifeHistory.RESIDENT]
        elif life_history == 'anadromous':
            possible_fish = [fish for fish in all_fish if fish.life_history is LifeHistory.ANADROMOUS]
        else:
            possible_fish = all_fish
        fish_with_activity = [fish for fish in possible_fish if activity in [item[2] for item in fish.activity_history]]
        for fish in fish_with_activity:
            progress += 1
            if progress % int(len(fish_with_activity)/20) == 1:
                print("Doing passage record for {0} fish. Progress: {1:.0f} %.".format(len(fish_with_activity), 100 * progress / len(fish_with_activity)))
            previous_reach_id = -1
            for age, reach_id in fish.reach_history:
                timestep = fish.birth_week + age
                if previous_reach_id > -1:
                    previous_reach = self.network.reach_with_id(previous_reach_id)
                    downstream_of_previous_reach_ids = [reach.id for reach in self.network.path_downstream_from_reach(previous_reach)]
                else:
                    downstream_of_previous_reach_ids = []
                candidate_reach = self.network.reach_with_id(reach_id)
                downstream_of_candidate_ids = [reach.id for reach in self.network.path_downstream_from_reach(candidate_reach)]
                if reach_id in downstream_reach_ids and (self.id == previous_reach_id or self.id in downstream_of_previous_reach_ids):
                    if fish.activity_at_age(age) is activity:
                        downstream_passage_records.append((timestep, fish.unique_id, age, fish.length_at_age(age), fish.mass_at_age(age)))  # fish passed reach heading downstream
                elif previous_reach_id in downstream_reach_ids and (self.id == reach_id or self.id in downstream_of_candidate_ids):
                    if fish.activity_at_age(age) is activity:
                        upstream_passage_records.append((timestep, fish.unique_id, age, fish.length_at_age(age), fish.mass_at_age(age)))  # fish passed reach heading upstream
                previous_reach_id = reach_id
        if direction == 'upstream':
            return upstream_passage_records
        elif direction == 'downstream':
            return downstream_passage_records
        elif direction == 'both':
            return upstream_passage_records, downstream_passage_records