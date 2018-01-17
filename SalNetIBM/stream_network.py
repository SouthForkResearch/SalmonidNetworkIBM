import math
import random
import shapefile  # from 'pyshp' library
import numpy as np
import csv
import sys
import datetime
from bokeh.models import LinearColorMapper, LogColorMapper, ColorBar, HoverTool, Label, Span, Axis, NumeralTickFormatter
from bokeh.layouts import column, row
from bokeh.models.sources import ColumnDataSource
from bokeh.plotting import figure
from .fish import Movement, LifeHistory
from .settings import network_settings, time_settings
from .network_reach import NetworkReach

class StreamNetwork:
    """ The network is represented as a collection of reaches. """

    def __init__(self, model):
        self.model = model
        self.reaches = []
        self.history = []
        print("Loading network shapefile.")
        # Create the shapefile reader and load the names of its fields
        sf = shapefile.Reader(network_settings['SHAPEFILE'])
        attrib_keys = [field[0] for field in sf.fields][1:]
        # Build a dictionary of from_node and to_node data, keyed by reach id
        dummy_shp = open(network_settings['SHAPEFILE'], "rb")  # not used here, just has to be a shapefile
        relationship_dbf = open(network_settings['NODE_RELATIONSHIP_FILE'], "rb")
        relationship_reader = shapefile.Reader(shp=dummy_shp, dbf=relationship_dbf)
        relationships = {}
        for r in relationship_reader.iterRecords():  # records are [reach_id, from_node, to_node]
            relationships[r[0]] = r[1], r[2]         # relationships keyed by LineOID containing from_node, to_node
        # Load the records from the shapefile and build the NetworkReach objects
        print("Building network reaches.")
        for sr in sf.iterShapeRecords():
            attrib_values = sr.record
            attribs = dict(zip(attrib_keys, attrib_values))
            if network_settings['SMALL_NETWORK_TEST'] is False or attribs['small_test'] > 0:
                points = sr.shape.points
                from_node, to_node = relationships[attribs['LineOID']]
                new_reach = NetworkReach(self, attribs, points, from_node, to_node)
                self.reaches.append(new_reach)
                if attribs['LineOID'] == network_settings['MOST_DOWNSTREAM_REACH']:
                    self.most_downstream_reach = new_reach
                    most_downstream_reach_attribs = attribs
        if not hasattr(self, 'most_downstream_reach'):
            sys.exit("Reach ID specified as the most downstream reach was not found in network.")
        # Connect the NetworkReach objects based on from_node and to_node attributes
        print("Connecting network reaches.")
        for reach in self.reaches:
            downstream_reaches = [r for r in self.reaches if r.from_node == reach.to_node]
            if len(downstream_reaches) == 1:
                reach.downstream_reach = downstream_reaches[0]
                reach.downstream_reach.upstream_reaches.append(reach)
            elif len(downstream_reaches) == 0 and reach is not self.most_downstream_reach:
                exit("Network loading error: Reach {0} has no downstream reach.".format(reach.id))
            elif len(downstream_reaches) > 1:
                exit("Network loading error: Reach {0} has {1} downstream reaches.".format(reach.id, len(downstream_reaches)))
        # Load temperature data for the network reaches
        print("Loading temperature data for the network.")

        # reach_temperatures = {}
        # with open(network_settings['TEMPERATURE_FILE'], newline='') as temperature_file:
        #     reader = csv.DictReader(temperature_file)
        #     for row in reader:
        #         temperature_strings = list(row.values())[1:]
        #         reach_temperatures[int(row['LineOID'])] = [float(temperature) for temperature in temperature_strings]
        # for reach in self.reaches:
        #     reach.set_temperatures(reach_temperatures[reach.id])

        tf = shapefile.Reader(network_settings['TEMPERATURE_FILE'])
        tfields = [field[0] for field in tf.fields if 'TMn' in field[0]]
        attrib_keys = [field[0] for field in tf.fields][1:]
        for attrib_values in tf.iterRecords():
            attribs = dict(zip(attrib_keys, attrib_values))
            reach = self.reach_with_id(int(attribs['LineOID']), True)
            if reach is not None:
                reach.set_temperatures([attribs[field] for field in tfields])

        # Create two "special" network reaches, which copy their properties (except length) from the lower reach
        # The "migration reach" represents the ~1100 km from the lower part of our network to the ocean
        self.migration_reach = NetworkReach(self, most_downstream_reach_attribs, points, None, None)
        self.most_downstream_reach.downstream_reach = self.migration_reach
        self.migration_reach.upstream_reaches.append(self.most_downstream_reach)
        self.migration_reach.length = network_settings['NETWORK_TO_OCEAN_DISTANCE']
        self.migration_reach.length_m = self.migration_reach.length * 1000
        self.migration_reach.is_migration_reach = True
        self.migration_reach.id = -2
        self.migration_reach.points = [(-1390000, 759943), (-1375000, 759943)]
        self.migration_reach.calculate_midpoint()
        self.reaches.append(self.migration_reach)
        # The "ocean reach" represents the ocean itself
        self.ocean_reach = NetworkReach(self, most_downstream_reach_attribs, points, None, None)
        self.migration_reach.downstream_reach = self.ocean_reach
        self.ocean_reach.upstream_reaches.append(self.migration_reach)
        self.ocean_reach.length = network_settings['OCEAN_REACH_LENGTH']
        self.ocean_reach.length_m = self.ocean_reach.length * 1000
        self.ocean_reach.is_ocean = True
        self.ocean_reach.id = -1
        self.ocean_reach.points = [(-1415000, 759943), (-1400000, 759943)]
        self.ocean_reach.calculate_midpoint()
        self.reaches.append(self.ocean_reach)
        print("Network loading complete.")

    def step(self, timestep):
        self.history.append({'step': timestep,
                             'anad pop': len([fish for fish in self.model.schedule.fish
                                              if fish.life_history is LifeHistory.ANADROMOUS]),
                             'res pop': len([fish for fish in self.model.schedule.fish
                                             if fish.life_history is LifeHistory.RESIDENT]),
                             'anad redds': len([redd for redd in self.model.schedule.redds
                                                if redd.mother.life_history is LifeHistory.ANADROMOUS]),
                             'res redds': len([redd for redd in self.model.schedule.redds
                                               if redd.mother.life_history is LifeHistory.RESIDENT])
                             })
        for reach in self.reaches:
            reach.step(timestep)

    def random_reach(self):
        """ Returns a random reach from the main network, excluding the ocean and migration reaches. """
        reach = random.choice(self.reaches)
        if not reach.is_ocean and not reach.is_migration_reach:
            return reach
        else:
            return self.random_reach()

    def reach_with_id(self, id, suppress_not_found_warning=False):
        reaches = [reach for reach in self.reaches if reach.id == id]
        if len(reaches) == 0:
            if not suppress_not_found_warning:
                print("No reach with ID ", id)
        else:
            return reaches[0]

    def season_label(self, history_step):
        week_of_year = history_step % time_settings['WEEKS_PER_YEAR']
        if 10 <= week_of_year <= 21:
            return 'Spring', 'Green'
        elif 22 <= week_of_year <= 32:
            return 'Summer', '#922B21'  # dark red
        elif 33 <= week_of_year <= 44:
            return 'Fall', 'Orange'
        else:
            return 'Winter', 'Blue'

    def plot(self, figure, color_attr=None, history_step=None, solid_color='#0485d1', circle_attr=None,
             circle_attr_transform=lambda x: x, circle_line_color='#cb7723', circle_fill_color='#fcb001',
             circle_hover_attrs=[], color_attr_bounds=None):
        """ To simply plot the network in a solid color, use color_attr=None and history_step=None.
            To plot a fixed attribute of each network reach such as redd capacity, set color_attr to the
            name of that attribute and history_step=None.
            To plot an attribute of the network's history that varies over time, use history_step along
            with the name of that attribute.
            color_attr_bounds is None to use the min and max values of that variable in the current plot, or
            specifiable to use a standard color range across multiple plots"""
        lines = [reach.points for reach in self.reaches]
        source = ColumnDataSource({'xs': [list(np.array(line).T[0]) for line in lines],
                                   'ys': [list(np.array(line).T[1]) for line in lines],
                                   'line_widths': [0.5 * reach.strahler_order for reach in self.reaches]})

        figure.add_layout(Label(x=self.migration_reach.midpoint[0], y=self.migration_reach.midpoint[1]+750,
                                text='Migration', text_align='center'))
        figure.add_layout(Label(x=self.ocean_reach.midpoint[0], y=self.ocean_reach.midpoint[1]+750,
                                text='Ocean', text_align='center'))
        if history_step is not None:
            year = 1 + math.floor(history_step / time_settings['WEEKS_PER_YEAR'])
            step_within_year = history_step % time_settings['WEEKS_PER_YEAR']
            days_into_year = 1 + step_within_year * time_settings['DAYS_PER_WEEK']
            date1 = datetime.date.fromordinal(days_into_year).strftime("%b %e")
            date2 = datetime.date.fromordinal(days_into_year + 7).strftime("%b %e")
            timestring = "Timestep {0} (step {1} of year {2}, {3} - {4})".format(history_step,
                                                                                 1 + step_within_year,
                                                                                 year,
                                                                                 date1,
                                                                                 date2)
            figure.add_layout(Label(x=30, y=700, x_units='screen', y_units='screen', text=timestring))
            season, season_color = self.season_label(history_step)
            figure.add_layout(Label(x=650, y=700, x_units='screen', y_units='screen', text=season, text_color=season_color))
        if color_attr is None:
            figure.multi_line('xs', 'ys', source=source, line_color=solid_color, line_width='line_widths')
        else:
            source.add([reach.reach_statistic(color_attr, history_step) for reach in self.reaches], name='color_values')
            color_low_value = min(source.data['color_values']) if color_attr_bounds is None else color_attr_bounds[0]
            color_high_value = max(source.data['color_values']) if color_attr_bounds is None else color_attr_bounds[1]
            mapper = LinearColorMapper(palette='Viridis256', low=color_low_value, high=color_high_value)
            figure.multi_line('xs', 'ys', source=source, line_color={'field': 'color_values', 'transform': mapper}, line_width='line_widths')
            fmt = NumeralTickFormatter(format='00')
            color_bar = ColorBar(color_mapper=mapper, location=(0, 0), title=color_attr, formatter=fmt, label_standoff=7)
            figure.add_layout(color_bar, 'right')
        if circle_attr is not None:
            circle_source = ColumnDataSource({'xs': [reach.midpoint[0] for reach in self.reaches],
                                              'ys': [reach.midpoint[1] for reach in self.reaches]})
            circle_source.add([circle_attr_transform(reach.reach_statistic(circle_attr, history_step))
                               for reach in self.reaches], name='circle_sizes')
            for attr in circle_hover_attrs:
                circle_source.add([reach.reach_statistic(attr, history_step) for reach in self.reaches], name=attr)
            figure.scatter('xs', 'ys', source=circle_source, name='scatterplot', marker='circle', size='circle_sizes',
                           line_color=circle_line_color, fill_color=circle_fill_color, alpha=0.5)
            hover_tooltips = []
            for attr in circle_hover_attrs:
                hover_tooltips.append((attr, "@"+attr))
            figure.add_tools(HoverTool(tooltips=hover_tooltips, names=['scatterplot']))
            figure.toolbar.logo = None

            # tutorial for adding year slider: https://rebeccabilbro.github.io/interactive-viz-bokeh/

    @staticmethod
    def position_after_movement(origin, direction, position_within_origin, rate, anadromy_allowed, upstream_mode='Random'):
        """ direction can be 'Upstream' or 'Downstream'
            upstream_mode can be 'Random' to choose at random; eventually, I want to add modes to preferentially
            Setting anadromy_allowed to True allows the fish to move into the migration and ocean reaches; otherwise
            it has to stay in the Upper Salmon part of the network.
            choose by temperature (seeking cool tribs) or by stream size (spawners avoiding tiny tribs)
            it would eventually be useful to add an exploratory behavior for fish that get stuck at tributary
            tips, in which they move downstream until hitting a randomly selected higher stream order, then move
            up that one at random
            Returns a tuple (reach, position, stopped)
            """
        current_reach = origin
        position_within_reach = position_within_origin
        if direction == Movement.DOWNSTREAM:
            position_within_reach -= rate
            while position_within_reach < 0:
                if (current_reach.is_ocean and anadromy_allowed) \
                        or (current_reach.downstream_reach.is_migration_reach and not anadromy_allowed) \
                        or (current_reach.downstream_reach.is_ocean and not anadromy_allowed):
                            return current_reach, position_within_reach, True  # don't move downstream beyond ocean
                current_reach = current_reach.downstream_reach
                position_within_reach += current_reach.length
        elif direction == Movement.UPSTREAM:
            if upstream_mode == 'Random':
                position_within_reach += rate
                while position_within_reach > current_reach.length:
                    if len(current_reach.upstream_reaches) == 0:
                        return current_reach, position_within_reach, True  # don't move upstream beyond tips
                    upstream_reach = random.choice(current_reach.upstream_reaches)
                    position_within_reach -= current_reach.length
                    current_reach = upstream_reach
        return current_reach, position_within_reach, False

    def route(self, origin, destination, position_within_origin, rate):
        # PART 1: Build the list of all network reaches along the route from origin to destination
        descent_from_origin = self.path_downstream_from_reach(origin)
        descent_from_destination = self.path_downstream_from_reach(destination)
        descent_path = []
        ascent_path = []
        if destination in descent_from_origin:
            descent_path = self.truncate_path_after_reach(descent_from_origin, destination)
        elif origin in descent_from_destination:
            ascent_path = self.truncate_path_after_reach(descent_from_destination, origin)
            ascent_path.reverse()
        else:
            for reach in descent_from_origin:
                if reach in descent_from_destination:
                    descent_path = self.truncate_path_after_reach(descent_from_origin, reach)
                    ascent_path = self.truncate_path_after_reach(descent_from_destination, reach)
                    ascent_path.reverse()
                    break
        # PART 2: Build a route description consisting of tuples of (reach, position_within_reach) for a
        # traverse of the reaches determined above at the given speed (distance per timestep), including
        # potentially spending more than 1 timestep in a long reach or skipping 1 or more short reaches.
        final_route = []
        position_within_reach = position_within_origin
        ascent_index = descent_index = 0
        while descent_index < len(descent_path):
            final_route.append((descent_path[descent_index], position_within_reach))
            position_within_reach -= rate
            while position_within_reach < 0:
                descent_index += 1
                if descent_index < len(descent_path):
                    position_within_reach += descent_path[descent_index].length
                else:
                    if position_within_reach < 0: # if we overshot the destination reach, choose a random location within the last reach
                        position_within_reach = random.uniform(0.0, descent_path[-1].length)
                    final_route.append((descent_path[-1], position_within_reach))
                    break
        # print([reach.id for reach in ascent_path])
        while ascent_index < len(ascent_path):
            if not (ascent_index == 0 and len(descent_path) > 0):  # don't double-record position when cornering
                # print("Adding reach {0} position {1} to final path.".format(ascent_path[ascent_index].id, position_within_reach))
                final_route.append((ascent_path[ascent_index], position_within_reach))
            position_within_reach += rate
            current_reach_length = ascent_path[ascent_index].length
            # print("Changing position_within_reach to {0}, noting current_reach_length = {1}".format(position_within_reach, current_reach_length))
            while position_within_reach > current_reach_length:
                ascent_index += 1
                position_within_reach -= current_reach_length
                # print("Changing ascent_index to {0} out of {1}".format(ascent_index, len(ascent_path)))
                if ascent_index < len(ascent_path):
                    # print("New ascent index points to reach {0} and position_within_reach to {1}".format(ascent_path[ascent_index].id, position_within_reach))
                    current_reach_length = ascent_path[ascent_index].length
                else:
                    current_reach_length = ascent_path[-1].length
                    if position_within_reach > current_reach_length:
                        position_within_reach = random.uniform(0.0, current_reach_length)
                    # print("Adding reach {0} position {1} to final path.".format(ascent_path[-1].id, position_within_reach))
                    final_route.append((ascent_path[-1], position_within_reach))
                    break
        assert final_route[0][0] is origin, "Route from reach {0} position {3} to reach {1} at rate {4} begins at reach {2}".format(origin.id, destination.id, final_route[0][0].id, final_route[0][1], rate)
        assert final_route[-1][0] is destination, "Route from reach {0} position {3} to reach {1} at rate {4} ends at reach {2}".format(origin.id, destination.id, final_route[-1][0].id, final_route[0][1], rate)
        return final_route

    @staticmethod
    def path_downstream_from_reach(reach):
        path = [reach]
        downstream_reach = reach.downstream_reach
        while downstream_reach is not None:
            path.append(downstream_reach)
            downstream_reach = downstream_reach.downstream_reach
        return path

    @staticmethod
    def truncate_path_after_reach(path, reach):
        index = path.index(reach)
        return path[:index+1]

