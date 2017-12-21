import math

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
        self.dead_fish = []


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
        self.steps += 1
        self.time += 1

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