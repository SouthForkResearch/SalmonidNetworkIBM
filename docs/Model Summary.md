# Brief summary and goals

This model helps explore relationships between salmonid (currently steelhead, *Oncorhynchus mykiss*) population dynamics and the  environmental and physiological processes that govern the lives of individual fish. It creates a population of simulated fish and tracks the location, characteristics, and actions of each individual throughout its life cycle and its interactions with a changing environment. The environment is a large river network (currently the Upper Salmon basin in Idaho) represented in 1-km pieces with channel characteristics and weekly temperature estimates derived from a variety of geospatial data sources and models.

We can use the model to predict how the population is likely to respond to novel changes to its environment, including potential habitat restoration actions. Detailed diagnostics make it possible to determine which mechanisms underlie any give prediction. Thus, instead of operating as a "black box," the model is a transparent source of ecological hypotheses that may be independently evaluated or prioritized based on their importance in the model and local biologists' knowledge.

This model differs from other large-scale population models in the high level of detail with which it treats the life of each individual simulated fish. And it differs from other detailed models of individual fish behavior in that it works on the scale of a largestream network (thousands of river miles) rather than one short reach.

# Basic structure of the model

The model was programmed in the Python language, starting with the 
[Mesa](https://github.com/projectmesa/mesa) individual-based
modeling framework as a skeleton on which to build the biology of salmonids. Because 
Python is an object-oriented language, the model's functions are organized by their 
correspondence with real-world objects. These include fish, redds, and network reaches.

For example, a "fish" object is defined by attributes (such as mass and age), 
relationships with other objects (such as the network reach it inhabits), and functions 
that describe how these attributes and relationships change over time. For example, 
the growth function uses a fish's current mass and the temperature of its associated 
network reach to calculate the fish's mass in the next time step.

The model updates the population at 8-day intervals. With each update, it loops through 
all the fish in the population in descending order of size, meaning the largest, most 
dominant fish win the contest for limited resources like food or spawning habitat.

# Overview of model details

This overview provides a basic picture of which variables and ecological mechanisms 
are incorporated into the model in some way. A comprehensive, reproducible 
description is planned once some of the mechanisms have been further refined.

## Network reaches

Each network reach is characterized by its length, width, stream order, spring 
scouring flows, temperature (modeled for each week of the year), redd capacity,
shape, and connections to adjacent reaches. 

## Redds

Redds are characterized by their age and accumulated degree-days of temperature, as 
well as relationships to their network reach and mother. They disappear and get 
replaced by juvenile fish after enough degree-days have accrued, unless they are 
killed by scouring flows first.

## Fish

Individual fish are characterized by their sex, life history (anadromous or resident), 
length, mass, age, and average foraging success. They also have relationships to network 
segments, including the reach they currently inhabit, their natal reach, the reach 
where they are to spawn (usually the natal reach, except in cases of straying), and, 
for residents, a home reach for foraging and growth. 

In addition to these basic attributes, the model tracks a large number of status 
variables such as whether or not an individual will stray at spawning time, whether or not 
it has already spawned in the current year, and its age at ocean entry. Two of the 
most important are its "movement mode" (downstream, upstream, random, or seeking 
a specific reach) and "activity" (freshwater growth, random dispersal, competitive 
dispersal, seeking colder or warmer waters, smolt outmigration, saltwater growth, 
spawning migration, spawning, postspawn return home, or kelt outmigration). In each 
timestep, the model uses these status variables to direct changes in the fish's 
state before the next timestep.

Fish grow in freshwater according to the Wisconsin bioenergetics model, based on the 
modeled temperature of their reach at each timestep, their current mass, and a 
lifelong constant value of 'P', or food intake as a proportion of the maximum ration, 
which is drawn from a normal distribution at birth. Future upgrades will incorporate 
the dependence of food intake on habitat. Saltwater growth is governed by a single 
empirical average growth curve regardless of conditions.

Competition for food and space is important to the distribution and abundance of fish 
in the model. Currently, each reach is assigned a fixed capacity for fish in two 
size classes (small and medium) using a simple area-based formula. The largest fish 
get the first spots available in each 
reach. Once the reach is filled to capacity, any remaining (smaller) fish transition
from  the "freshwater growth" activity to the "competitive dispersal" activity, in which 
they move around at random with a suppressed food intake until they find a new place 
to grow within the limits of reach capacity.

Mature fish are triggered by time-of-year to begin their spawning migrations, and females
become available for spawning when they reach their spawning grounds, unless their 
spawning area has already reached its redd capacity, in which case they become 
strays and look for a spot elsewhere. A female will spawn with the first available male 
of the same life history, unless no males of the same life history are available, 
in which case steelhead might mate with residents and vice versa. The act of spawning 
creates a redd object and sends both parents into the post-spawn activity model.

Mortality is modeled via several different mechanisms. At every week and for fish of every
size and activity, there is a small, random, size-dependent chance of mortality. However,
specific biological events can also cause mortality, such as starvation after being 
out-competed for food for several weeks in a row. Likewise, spawning carries a high 
risk or guarantee of post-spawn mortality, depending on sex and life history.

# Diagnostic measures

In addition to the biological and physical attributes described above, each object 
in the model tracks a detailed collection of history variables to help trace interesting 
results back to their biological causes. For example, every important event in each 
fish's life (such as a change in activity or movement mode) is logged, as are its 
length and size at every timestep. These diagnostics enable the kind of plots shown
in the [preliminary results](Early%20Results.md).