# Preliminary results

This page exists to demonstrate the kinds of output the model generates, how they can 
help understand the biology it's simulating, and how a comparison of these outputs could 
provide insight into restoration actions.

Right now, some of the mechanisms in the model are placeholders pending the incorporation 
of new data sources from collaborators, so the specifics of the findings (such as 
population sizes) should not be taken literally yet. Instead, view this page as a demonstration
of the potential of this modeling platform to explore the consequences of individual 
behavior and physiology and their environmental drivers.

## Test scenarios

The results below come from two model runs representing different temperature 
regimes in the Upper Salmon basin. Unless specifically labeled, they come from the 
"restoration scenario" in which stream temperatures have been reduced basin-wide by 
improvements to riparian vegetation. For comparison, some results are shown from 
a "baseline scenario" representing modeled temperatures from a typical recent 
year (2013). 

## Overall population

Total population size in both for fish (left) and redds (right) is summarized below 
for the restoration scenario:

![Restoration Scenario Population Size](/docs/Media/Results_Restoration/Population%20Size.png)

We can compare this with the baseline scenario:

![Baseline Scenario Population Size](/docs/Media/Results_Baseline/Population%20Size.png)

These two simulations actually show a smaller population under the cooler, restored 
temperatures; this is not a serious prediction, but an artifact of the preliminary 
state of the model. We are still working on implementing the 
mechanisms by which excessive water temperature harms a real population. 

## Survival and success

For each model run, we can look at overall survival:

![Restoration Scenario Survival Curves](/docs/Media/Results_Restoration/Survival%20Curves.png)

as well as success at various tasks or transitions:

![Restoration Scenario Population Size](/docs/Media/Results_Restoration/Success%20Rate%20Table.png)

For fish that died, we can look at the sources of mortality:

![Mortality Sources](/docs/Media/Results_Restoration/Mortality%20Source%20Table.png)

## Visualizing the population

After a model run, we can stitch together a big-picture overview of the population at every timestep, 
including where the fish are (circles on the map, with areas proportional to the number
of fish), what they're doing, size distribution over time, and where the current 
frame fits onto the overall population size plots.

Two special reaches on the network are shown for convenience without realistic position
or length: the "ocean reach" which represents the entire ocean, and the "migration reach"
represents approximately 1,100 km of river from the lower end of this Upper Salmon network
to the ocean. Both are visualized with placeholders to show how many fish are in each 
area at any given time. 

### Overall population summaries

Click the thumbnail to view the population summary video on Youtube:

[![Video summary of the restoration scenario population](http://img.youtube.com/vi/XJc7mq6fKtA/0.jpg)](https://youtu.be/XJc7mq6fKtA "Full population details")

Here is a closeup of the population map without the supporting graphs:

[![Video map of the restoration scenario population](http://img.youtube.com/vi/fY6srDlwDg8/0.jpg)](https://youtu.be/fY6srDlwDg8 "Full population map")

We can break this down for anadromous fish only:

[![Video map of the restoration scenario anadromous population](http://img.youtube.com/vi/e8QuMiz6cD8/0.jpg)](https://youtu.be/e8QuMiz6cD8 "Anadromous population map")

Or residents only:

[![Video map of the restoration scenario resident population](http://img.youtube.com/vi/M64QvcrVJzI/0.jpg)](https://youtu.be/M64QvcrVJzI "Resident population map")

### Population relative to capacity

In the videos linked below, we view the population not as circles over the network, but 
as color-coding of network segments to indicate how close they are to their maximum 
capacity at various stages. These plots are important to understanding which mechanisms 
are limiting the population.

For small fish (less than 100 mm):

[![Video of small fish relative to capacity](http://img.youtube.com/vi/iS0i2d7KIiM/0.jpg)](https://youtu.be/iS0i2d7KIiM "Small fish capacity")

Medium fish (between 100 and 180 mm):

[![Video of medium fish relative to capacity](http://img.youtube.com/vi/JNXykCSouR0/0.jpg)](https://youtu.be/JNXykCSouR0 "Medium fish capacity")

For redds:

[![Video of redds relative to capacity](http://img.youtube.com/vi/nZLM6WTy39Q/0.jpg)](https://youtu.be/nZLM6WTy39Q "Redd capacity")

### Passage

For comparison with field data, the model can generate predicted timetables of fish passage 
(both smolts and spawners) past the mouths of various tributaries. In this simulation, we 
eventually lost all fish in the Yankee Fork, due to artifacts from some of the 
unrealistic placeholders in the current model. Eventually, matching these to field 
data will be a key step in model validation.

A glitch in the current plotting code left some of these unlabeled, but they 
alternate stages: smolt, spawner, smolt, spawner, smolt, spawner.

![Fish Passage Plots](/docs/Media/Results_Restoration/Passage%20Plots.png)

### Individual fish histories

One of the most important steps in validating the model is making sure the activities 
of each individual fish pass a basic sanity test. We cannot do this for all the hundreds 
of thousands of fish in each simulation, but manually reviewing a large number of 
cases provides a good idea of whether realistic biology dominates the model.

For example, the following fish follows a fairly realistic sequence of major life events 
(listed on the left side) until dying from the random survival probability model en route 
to its spawning grounds. However, its growth is too slow, and it mostly experiences
very low temperatures.

![Anadromous individual](/docs/Media/Results_Restoration/selected%20anadromous%20individuals/fish%20219327.png)

In contrast, this resident individual spends its long life in a small area:

![Resident individual](/docs/Media/Results_Restoration/selected%20resident%20individuals/fish%20425707.png)

Although it is not possible to display here on Github, hovering over the circles indicating 
fish positions in the direct model output displays a detailed list of variables describing
the fish's status while it was there. 

In the current version of the model, most fish follow realistic life histories, but there 
are a few glitches being resolved. The combination of population- and individual-level 
diagnostics makes it possible to rigorously reality-check the model and 
track down the sources of unrealistic artifacts. Even at this preliminary stage, 
this process provides some insights into which mechanisms are or are not necessary to account 
for the patterns we see in nature.
