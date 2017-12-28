# Features to add

## Visualization and outputs
* Make an easy way to examine metrics for a particular network reach over time. Then use it to figure out 
  why the tributaries are being so under-utilized.
* Write some code to summarize output from multiple model runs in a way comparable to Matt's summaries
  of the other LCM.
* Do population size summaries by maturity/life history and activity/life history.
* The suite of exported information from a model run should include the input parameters.
* See about serializing the result of a full model run to save to file and retrieve/analyze later.

## Network
* Get Spring95 attribute into the network or figure out how it maps into current attributes.
* Build in "smart" random movement that doesn't get stuck at tips, makes turns sometimes, maybe prioritizes temperature.
* Build in functionality for population groups -- should be in shapefile already, maybe a 6-7 letter code
* Test the latest network version with text fields in it.

## Biology
* Add additional variation in spawner run timing (when they leave the ocean, how fast they move).
* Current mechanisms don't reflect known steelhead extent at all (straying and other movements, as well as
  random life history switching.)
* We currently have very simplistic straying mechanisms. Females that find their spawning reach already
  at capacity become strays. Also, all fish have a very low chance at birth to be assigned a spawning reach
  different from their natal reach, but the new reach is selected at random from the whole network. Eventually, 
  I could have a system that randomly generates a straying distance (exponential distribution)
  and walks the network that distance in random directions, except only backtracking when confronted with
  a dead end. Another, probably better, alternative is to precalculate stray probabilities not for each
  reach a fish is currently in, but for each destination. Walk the network downstream from the destination,
  find all the wrong turns a fish could make when going upstream, and assign a probability to each of
  them based on stream order. When a fish born in one of those reaches is drawn for "destined to stray",
  it is assigned (destined from birth) to make one of these wrong turns. If it then actually survives to
  make the spawning migration, it is (somehow -- figure this out) assigned a natal reach upstream of the
  wrong turn somewhere, and/or guided to the wrong turn and turned into a random upstream migrant.
* Fall warmth-seeking creates net movement downstream; we need to create upstream movement eventually to 
  offset it. However, the temperatures are so low right now that nowhere on the network has the "warm" water
  the fish are seeking during these weeks. Currently, this mechanism is disabled altogether. Summer
  cold-seeking is never triggered by the current network temperatures at all.
            
## Speed/memory optimizations
* Might need to spend some time with a memory profiler and figuring out how to make large/log runs dump
  dead fish to log files periodically instead of keeping them all in memory at once. So far this hasn't
  been an problem even with 50-year, full-network runs, but it has to be at some point.
* Several small but cumulatively worthwhile improvements from the speed profiler, including making 
  is_small, is_medium, is_mature attributes updated only when they change.

## User-friendliness
* Eventually have the settings read from a CSV file rather than hard-coded dictionaries. The code was set up
  to make this a very easy transition.
  
# Problems to fix

## Minor debugging
* We have some fish spawning all the time.
* We have quite a few fish in spawning migration all the time, especially residents.
* Double check that movement ascent & descent paths are working correctly. It seems they may be the same,
  calculated downward from upstream, instead of starting upstream movement with a 50-km jump from the ocean, etc.
* Kelts were spawning in the ocean. A recent update might have fixed this but I should double check.

# Significant conceptual/biological issues to address
* The temperatures in the network are all pretty low, below the optimal temperature for growth of well-fed
  _O. mykiss._ This might be because they're weekly means of daily means and don't really capture the daily
  maxima that might drive fish responses to thermal extremes. As a result, the thermal adaptation parts of 
  the model either aren't triggered at all (seeking cool water in summer) or are triggered all the time
  for the whole network (seeking warmer water in fall). Before these mechanisms can be meaningful, we need
  a more realistic treatment of temperature variation. 
* We need a more realistic/mechanistic treatment of capacity.
* We have an undesirable mixture of a mechanistic mortality mechanism (starvation) and non-mechanistic one
  (stage-specific survival rates) acting simultaneously; it would be ideal to explicitly model other 
  mortality sources in a way that roughly matches the overall survival rates we targeted. Mortality should
  be either fully explicit or fully emergent, not some odd combination of the two.
        