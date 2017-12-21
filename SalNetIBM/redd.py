import random
from mesa import Agent
from .fish import LifeHistory
from .settings import time_settings, spawning_settings

class Redd(Agent):
    """ A redd that will disappear and be replaced by fish at the appropriate time."""
    def __init__(self, unique_id, model, mother):
        super().__init__(unique_id, model)
        self.accrued_degree_days = 0
        self.deposited_time = model.schedule.time
        self.mother = mother
        self.network_reach = mother.network_reach
        self.position_within_reach = self.mother.position_within_reach
        self.mortality_reason = None
        self.is_dead = False  # flag used to mark fish when they die, for more efficient mass deletion once per timestep
        self.network_reach.redds.append(self)

    def step(self):
        self.accrue_degree_days()
        if self.accrued_degree_days > spawning_settings['REQUIRED_DEGREE_DAYS_TO_EMERGE']:
            self.replace_with_fry()
        elif 0.07 * random.normalvariate(0, 1) * self.network_reach.spring95 > 1:
            self.die("Scoured.")

    def accrue_degree_days(self):
        """ Need to figure out why Chris used the fancier formula  """
        T = self.network_reach.temperature_at_week(self.model.schedule.time)
        self.accrued_degree_days += time_settings['DAYS_PER_WEEK'] * T
        # if T < 2:
        #     self.accrued_degree_days += time_settings['DAYS_PER_WEEK'] * T + 0.96
        # elif T > 14:
        #     self.accrued_degree_days += time_settings['DAYS_PER_WEEK'] * T + 1.45
        # else:
        #     self.accrued_degree_days += -0.26*T + 0.16 * T**2 + 0.0055 * T**3 + 2.91

    def replace_with_fry(self):
        fecundity_mean = 0.15 * 0.0002 * self.mother.fork_length ** 2.5989
        fecundity_variance = 10
        num_fry = round(random.normalvariate(fecundity_mean, fecundity_variance))
        for i in range(num_fry):
            if random.random() < spawning_settings['LIFE_HISTORY_INHERITANCE_PROBABILITY']:
                life_history = self.mother.life_history
            else:
                if self.mother.life_history == LifeHistory.RESIDENT:
                    life_history = LifeHistory.ANADROMOUS
                else:
                    life_history = LifeHistory.RESIDENT
            self.model.add_fish(self.network_reach, life_history, self)
        self.die("Fry emerged")

    def die(self, reason):
        self.mortality_reason = reason
        self.is_dead = True