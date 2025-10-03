# components/room_profiles.py

# This file is the single source of truth for all room specifications.
# It merges the layout data from visualizer.py and the dimensional data from app.py.
ROOM_SPECS = {
    'Small Huddle Room (2-3 People)': {
        'area_sqft': (100, 150), 'capacity': (2, 3), 'primary_use': 'Ad-hoc collaboration, quick calls',
        'typical_dims_ft': (12, 10),
        'table_size': [4, 2.5], 'chair_count': 3, 'chair_arrangement': 'casual'
    },
    'Medium Huddle Room (4-6 People)': {
        'area_sqft': (150, 250), 'capacity': (4, 6), 'primary_use': 'Team meetings, brainstorming',
        'typical_dims_ft': (15, 12),
        'table_size': [6, 3], 'chair_count': 6, 'chair_arrangement': 'round_table'
    },
    'Standard Conference Room (6-8 People)': {
        'area_sqft': (250, 400), 'capacity': (6, 8), 'primary_use': 'Formal meetings, presentations',
        'typical_dims_ft': (20, 15),
        'table_size': [10, 4], 'chair_count': 8, 'chair_arrangement': 'rectangular'
    },
    'Large Conference Room (8-12 People)': {
        'area_sqft': (400, 600), 'capacity': (8, 12), 'primary_use': 'Client presentations, project reviews',
        'typical_dims_ft': (28, 20),
        'table_size': [16, 5], 'chair_count': 12, 'chair_arrangement': 'rectangular'
    },
    'Executive Boardroom (10-16 People)': {
        'area_sqft': (600, 800), 'capacity': (10, 16), 'primary_use': 'High-stakes meetings, executive sessions',
        'typical_dims_ft': (35, 20),
        'table_size': [20, 6], 'chair_count': 16, 'chair_arrangement': 'oval'
    },
    'Training Room (15-25 People)': {
        'area_sqft': (750, 1250), 'capacity': (15, 25), 'primary_use': 'Instruction, workshops',
        'typical_dims_ft': (40, 25),
        'table_size': [10, 4], 'chair_count': 25, 'chair_arrangement': 'classroom'
    },
    'Large Training/Presentation Room (25-40 People)': {
        'area_sqft': (1250, 2000), 'capacity': (25, 40), 'primary_use': 'Lectures, seminars',
        'typical_dims_ft': (50, 35),
        'table_size': [12, 4], 'chair_count': 40, 'chair_arrangement': 'theater'
    },
    'Multipurpose Event Room (40+ People)': {
        'area_sqft': (2000, 4000), 'capacity': (40, 100), 'primary_use': 'Town halls, large events',
        'typical_dims_ft': (60, 40),
        'table_size': [16, 6], 'chair_count': 50, 'chair_arrangement': 'flexible'
    },
    'Video Production Studio': {
        'area_sqft': (500, 1500), 'capacity': (3, 10), 'primary_use': 'Content creation, recording',
        'typical_dims_ft': (40, 25),
        'table_size': [12, 5], 'chair_count': 6, 'chair_arrangement': 'production'
    },
    'Telepresence Suite': {
        'area_sqft': (400, 800), 'capacity': (6, 12), 'primary_use': 'Immersive video conferencing',
        'typical_dims_ft': (30, 20),
        'table_size': [14, 4], 'chair_count': 8, 'chair_arrangement': 'telepresence'
    }
}
