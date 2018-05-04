import numpy as np
from numba import jit

CA = 0.628
CB = -0.3
RA = 0.013     # (g / g) / day
RB = -0.217
ACT = 1.3
SDA = 0.172
EDO2 = 13562
EDprey = 3636  # J / g wet mass ; Differs from original value of 2500 based on my energy density calculations
EDpred = 5900  # J / g wet mass
Ck1 = 0.2
Ck4 = 0.2
CQ = 3.5
CTL = 24.3
CTO = 25
CTM = 22.5
RQ = 2.2
RTM = 26
RTO = 22

# Five of these egestion/excretion parameters come from Elliott 1976, and they all come from Elliott' s experiments;
# UA was modified by Stewart et al 1983 from the original value of 0.0259 to the new value of 0.0314 to account
# for the fact that egested calories cannot be excreted.
FA = 0.212
FB = -0.222
FG = 0.631
UA = 0.0314
UB = 0.58
UG = -0.299


@jit(nopython=True)
def f1(T):
    c3 = (1 / (CTO - CQ)) * np.log(0.98 * (1 - Ck1) / (0.02 * Ck1))
    c4 = (1 / (CTL - CTM)) * np.log(0.98 * (1 - Ck4) / (0.02 * Ck4))
    return (Ck1 * np.exp(c3 * (T - CQ)) / (1 + Ck1 * (np.exp(c3 * (T - CQ)) - 1))) * (
    Ck4 * np.exp(c4 * (CTL - T)) / (1 + Ck4 * (np.exp(c4 * (CTL - T)) - 1)))  # eqn 15


@jit(nopython=True)
def f2(T):
    c5 = (1 / 400) * ((np.log(RQ) * (RTM - RTO)) ** 2 * (1 + (1 + 40 / (np.log(RQ) * (RTM - RTO + 2))) ** 0.5) ** 2)
    return ((RTM - T) / (RTM - RTO)) ** c5 * np.exp(c5 * (T - RTO) / (RTM - RTO))  # eqn 17


@jit(nopython=True)
def f3(T):
    return T ** FB if T > 1 else 1


@jit(nopython=True)
def f4(T):
    return T ** UB if T > 1 else 1


@jit(nopython=True)
def daily_growth_from_p(T, W, p):
    # Returns daily growth from p, the proportion of the fish's maximum ration it obtains
    return (1 / EDpred) * ((EDprey * CA * W ** CB * p * f1(T)) * (1 - (FA * f3(T) * np.exp(FG * p)))
                           * (1 - SDA - UA * f4(T) * np.exp(UG * p)) - (RA * ACT * EDO2 * W ** RB * f2(T)))

@jit(nopython=True)
def daily_growth_from_grams_consumed(T, W, C_g):
    # Takes temperature T (degrees C), fish mass W (g), and actual grams consumed (g/day) and returns daily specific growth
    p = min(1, C_g / (W * CA * W ** CB * f1(T)))
    return (1 / EDpred) * ((EDprey * CA * W ** CB * p * f1(T)) * (1 - (FA * f3(T) * np.exp(FG * p)))
                           * (1 - SDA - UA * f4(T) * np.exp(UG * p)) - (RA * ACT * EDO2 * W ** RB * f2(T)))

@jit(nopython=True)
def daily_grams_consumed_from_p(T, W, p):
    # Takes temperature T (degrees C), fish mass W (g), and p-value, and returns consumption in (g/day), not the
    # usual g/g/day used for the 'C' term in the bioenergetics model.s
    return W * CA * W ** CB * p * f1(T)


@jit(nopython=True)
def mass_at_length(fork_length):
    return 10 ** (2.9 * np.log10(fork_length) - 4.7)


@jit(nopython=True)
def length_at_mass(mass):
    return 10 ** ((np.log10(mass) + 4.7) / 2.9)
