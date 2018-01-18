# Submodel for competition for food and space

## Desired or required model characteristics

The proposed algorithm described below was motivated by the following goals and constraints:

1. To accurately predict the effects of manipulating food and/or temperature on a population of competing individuals, we need to capture how these variables interact in bioenergetics models. Specifically, fish need more food to sustain a given growth rate at a higher temperature. Thus, at higher temperatures, dominant competitors should monopolize more of the resources, and outcompeted individuals should suffer more sharply from their famine than at colder temperatures.
2. Fish should compete for habitat as well as food, because the availability of food to a fish in a reach depends on which parts of that reach are actually accessible to the fish for profitable foraging and how many competitors are already there.
3. The competition model has to be extremely computationally efficient because it is referenced constantly by growing fish to see how much they'll grow and whether they should move. This means:
    a. Ideally, fish would compete for food and habitat via a single combined metric.
    b. We can't have each fish loop over its competitors to figure out how many there are or where it fits in. Instead, we need to manage resources within the 'network reach' objects by keeping a running tab of what's available to the fish. Fish compete by subtracting from this tab (larger/dominant fish first) rather than directly interacting. The trick is to figure out what this tab looks like.
4. Large fish shouldn't be competing with small fish, because they require different microhabitats and prey sizes. However, it's preferable not to just lump fish into size bins and only have them compete for resources or capacity within their bin. Resource needs vary continuously with fish size, and if we have enough bins to represent this continuity, we end up unrealistically isolating fish from competitors in adjacent bins. Ideally, each fish should be in competition with others within the same range of sizes.

## Proposed algorithm

### Characterizing resources in a reach

Resource availability in each reach is tracked using a 2-D array (a Numpy array, for speed), in which one dimension's index corresponds to depth and the other corresponds to velocity. Values in the array are the surface area available within the reach at each approximate depth and velocity. Fish compete for space in this array, and competition for food is implicit in the formulas for how much space each fish requires and how well they grow if they do not have enough space. 

The values in the array are calculated for each network reach using statistical models, calibrated from CHaMP data, which predict the proportion of habitat at or near each depth/velocity combination as a function of variables we know across the Upper Salmon network: bank-full width, gradient, and maybe discharge. (We don't have a discharge variable in the current shapefile.) The proportions from these regressions will be normalized so the whole array sums to 1, then multiplied by the surface area of the reach, so each entry in the array represents the actual surface area within the reach characterized by the given depth/velocity.

### Competition for space by fish

Both currently and under this new competition model, fish are sorted by size at the beginning of every timestep. The model iterates through them in this order in each timestep, meaning the largest, most dominant fish get first access to limited resources.

Each fish has a list of acceptable depth/velocity combinations for foraging, ranked in order of preference as determined by potential NREI. (Precalculated preference tables for size classes or size class / temperature combinations will negate the need to calculate actual NREIs.) When a fish's turn arrives to take up resources (surface area), it takes up the space it needs (its territory) from the most preferable depth/velocity matrix cell that still has that amount of space available. The space it uses it then subtracted from the table of what's available for the remaining, less dominant fish. 

If no acceptable table entry contains the appropriate amount of space, the fish takes up all the remaining space in the most preferable depth/velocity matrix cell with nonzero remaining space. However, its ration level is reduced in proportion to the ratio of space available to space desired, and it is flagged to begin competitive dispersal movements in the next timestep.

### Relationship between space and food

We don't have any way to calculate actual food available based on drift density or depletion of drift by upstream competitors within the reach, so we instead look for a simplified relationship that satisfies requirement #1 using data available to us.

We develop a relationship to infer food production per unit area in each network reach from gross primary productivity (GPP), which we already have modeled across the network. (I'll address how we do this shortly.) We ignore the fact that food drifts in from upstream and assume fish capture all the local production in their territory instead. A rolling average of GPP might be a better proxy for food production than instantaneous GPP.

The desired territory size for a fish is determined by food production per unit area in the reach and the fish's size- and temperature-dependent food needs as determined by the bioenergetics model. We assume some maximum ration level available to the fish under the best circumstances, probably p = 0.3 based on Gorm Rasmussen's (whose experiments were the basis of many BioE equation parameters for *O. mykiss*) observations that fish in the wild eating insects in a fertile stream never obtained much more than about 0.3 times the maximum caloric ration on hatchery pellet food. We calculate desired territory size based on how large the territory would have to be to provide enough food for p=0.3 given the fish's mass and temperature. Defining territory size in these terms allows for straightforward assignment of resources to outcompeted fish, too: if a fish has a territory of half its desired size, it gets half its desired ration, p=0.15.

To make sure these territory sizes approximate the territory sizes of real fish, and to fill in the unknown linkage between GPP and food above, we calibrate that GPP-to-food relationship such that, under average circumstances, it produces territory sizes which match the allometric scaling of *O. mykiss* territory sizes from the literature (perhaps Ernst Keeley's papers).

## Diagnostic metrics

We'll be able to track a fish's depth, water velocity, and ration level over time.