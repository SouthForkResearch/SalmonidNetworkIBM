import os

BASE_DIRECTORY = os.path.join(os.path.expanduser("~"), 'Dropbox', 'SFR')

export_settings = dict(
    RESULTS_PATH=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBMResults'),
    DEAD_FISH_CACHE_PATH=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBMResults', 'DeadFishCache')
)

time_settings = dict(
    DAYS_PER_WEEK=8,
    WEEKS_PER_YEAR=46
)

network_settings = dict(
    SMALL_NETWORK_TEST=False,        # set to True to run things on a subset of the network
    MOST_DOWNSTREAM_REACH=2962,
    NETWORK_TO_OCEAN_DISTANCE=1115,  # km from the lowermost node of our network to the ocean
    OCEAN_REACH_LENGTH=250,          # km "length" of the ocean reach, used to spread out run timing a bit
    LEMHI_MOUTH=1627,
    PAHSIMEROI_MOUTH=2242,
    YANKEE_FORK_MOUTH=3671,
    PROPORTION_USABLE_HABITAT=1.0,  # Arbitrary multiplier to reduce habitat area beyond the raw predicitons to match generally reasonable numbers
    #SHAPEFILE=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBM', 'Network', 'SalmonNetwork_R1_20171018.shp'),
    MICROHABITAT_MODEL_CACHE_PATH=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBM', 'Network', 'Microhabitat_Model_Cache'),
    MICROHABITAT_PREFERENCE_CACHE_PATH=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBM', 'resources', 'nrei_batch_results'),
    SHAPEFILE=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBM', 'Network', 'G_SalmonNetwork_R1_TextFields_20171206.shp'),
    NODE_RELATIONSHIP_FILE=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBM', 'Network', 'Salmon_noderelationship_20171003.dbf'),
    #TEMPERATURE_FILE=os.path.join(BASE_DIRECTORY, 'UpperSalmon', 'HexSim', 'RipVeg', '2013', 'Mean', 'USal_2013_8D_pot_Mn.shp'),  # restoration 2013 temps
    TEMPERATURE_FILE=os.path.join(BASE_DIRECTORY, 'UpperSalmon', 'HexSim', 'RipVeg', '2013', 'Mean', 'USal_2013_8D_curr_Mn.shp'),  # regular 2013 temps
    NREI_BATCH_FOLDER=os.path.join(BASE_DIRECTORY, 'Projects', 'SalmonidNetworkIBM', 'resources', 'nrei_batch_results')
)

spawning_settings = dict(
    REQUIRED_DEGREE_DAYS_TO_EMERGE=340,
    LIFE_HISTORY_INHERITANCE_PROBABILITY=0.75,
    MAX_WEEKS_TO_WAIT_WITHOUT_MATE=6,  # how long a fish will remain a spawner before giving up on finding a mate
    STRAY_PROBABILITY=0.02  # arbitrary guess
)

resident_fish_settings = dict(
    SPAWNING_MIGRATION_START=8,  # week
    SPAWNING_MIGRATION_END=19,  # week
    SPAWNING_MIGRATION_SPEED=5,  # km/week
    AGE_AT_MATURITY=92,  # weeks
    MALE_POSTSPAWN_SURVIVAL_PROBABILITY=0.8,  # MADE UP, NEED REAL NUMBERS
    FEMALE_POSTSPAWN_SURVIVAL_PROBABILITY=0.8,  # NEED REAL NUMBERS
    POSTSPAWN_RETURN_RATE=10,  # km/week,
    SUMMER_COLD_SEEKING_START=28,  # week
    SUMMER_COLD_SEEKING_END=36,  # week
    FALL_WARMTH_SEEKING_START=35,  # week
    FALL_WARMTH_SEEKING_END=39,  # week
    FALL_WARMTH_SEEKING_RATE=5,  # km/week
    STARVATION_THRESHOLD=0.8,    # a fish dies when it drops below this proportion of its lifetime maximum mass
    MINIMUM_FLOATER_P=0.25       # lowest possible proportion of maximum ration for outcompeted fish as floaters
)

anadromous_fish_settings = resident_fish_settings.copy()  # define as equal, specify differences below
anadromous_fish_settings['SPAWNING_MIGRATION_START'] = 30  # At 50 km/week and 1115 km from ocean to network,
anadromous_fish_settings['SPAWNING_MIGRATION_END'] = 41    # anad spawners should arrive in network around week 6-17
anadromous_fish_settings['SPAWNING_MIGRATION_SPEED'] = 50

anadromous_fish_settings['SMOLT_OUTMIGRATION_START'] = 16
anadromous_fish_settings['SMOLT_OUTMIGRATION_END'] = 25
anadromous_fish_settings['SMOLT_OUTMIGRATION_SPEED'] = 50
anadromous_fish_settings['SMOLT_MIN_FORK_LENGTH'] = 180

anadromous_fish_settings['MALE_POSTSPAWN_SURVIVAL_PROBABILITY'] = 0.0
anadromous_fish_settings['FEMALE_POSTSPAWN_SURVIVAL_PROBABILITY'] = 0.2  # kelting rate

anadromous_fish_settings['POSTSPAWN_RETURN_RATE'] = 200  # km/week, MADE UP

