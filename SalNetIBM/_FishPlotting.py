from bokeh.models import HoverTool, Label, ColumnDataSource, Arrow, VeeHead, TableColumn, DataTable, LinearAxis, Range1d
from bokeh.layouts import column, row
from bokeh.plotting import figure
import numpy as np
from .settings import time_settings


class FishPlotting:

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
        lifemap.add_layout(
            Label(x=30, y=700, x_units='screen', y_units='screen', text="Fish ID {0}".format(self.unique_id)))
        title, lifetext, lifesource = self.activity_descriptors()
        lifemap.title.text = title
        lifemap.title.text_font_size = "10px"
        lifemap.toolbar.logo = None
        for i in range(1, len(pointx)):
            lifemap.add_layout(
                Arrow(end=VeeHead(size=10, line_color='#cb7723', fill_color='#fcb001'), line_color='#fcb001',
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
        fig.extra_y_ranges = {
            'length_range': Range1d(start=min(self.length_history) - 3, end=max(self.length_history) + 3)}
        fig.xaxis.axis_label = 'Age (years)'
        fig.yaxis.axis_label = 'Mass (g)'
        fig.add_layout(LinearAxis(y_range_name='length_range', axis_label='Fork length (mm)'), 'right')
        fig.line('age', 'mass', source=source, line_width=2, legend='Mass', line_color='forestgreen')
        fig.line('age', 'length', source=source, y_range_name='length_range', line_width=2, legend='Length',
                 line_color='slateblue', line_dash='dotted')
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