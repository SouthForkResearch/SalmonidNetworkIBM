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

![Restoration Scenario Population Size](https://github.com/SouthForkResearch/SalmonidNetworkIBM/blob/master/Media/Results_Restoration/Population%20Size.png)

We can compare this with the baseline scenario:

![Baseline Scenario Population Size](/Media/Results_Baseline/Population Size.png)

These two simulations actually show a smaller population under the cooler, restored 
temperatures; this is not a serious prediction, but an artifact of the preliminary 
state of the model. We are still working on implementing the 
mechanisms by which excessive water temperature harms a real population. 

## Survival and success

For each model run, we can look at overall survival:

![Restoration Scenario Population Size](/Media/Results_Restoration/Success Rate Table.png)

as well as success at various tasks or transitions:

![Restoration Scenario Survival Curves](/Media/Results_Restoration/Survival Curves.png)

## Visualizing the population

After a model run, we can stitch together a picture of the population at every timestep, 
including where the fish are (circles on the map, with areas proportional to the number
of fish), what they're doing, size distribution over time, and where the current 
frame fits onto the overall population size plots.

Two special reaches on the network are shown for convenience without realistic position
or length: the "ocean reach" which represents the entire ocean, and the "migration reach"
represents approximately 1,100 km of river from the lower end of this Upper Salmon network
to the ocean. Both are visualized with placeholders to show how many fish are in each 
area at any given time. 

[![Video summary of the restoration scenario population](http://img.youtube.com/vi/XJc7mq6fKtA/0.jpg)](https://youtu.be/XJc7mq6fKtA "Full population details")





