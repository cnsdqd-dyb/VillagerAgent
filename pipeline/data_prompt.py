AGENT_INFO_STORE_FORMAT = """{name} is at {position}. {name} is holding {items}.There are {inventory} in {name}'s bag(aka inventory). {nearby_info}
The location of blocks around are:
{blocks_info}
"""

SOMEONE_NEARBY_INFO_FORMAT = "There are some agents nearby: {name_list}."

NOONE_NEARBY_INFO_FORMAT = "There is no agent nearby."

SUCCESS_DECOMPOSE_PLAN_FORMAT = """Here is a decompose plan:
Nodes: {nodes}
Edges: {edges}
Entry: {entry}
Exit: {exit}

The performance of the plan is success.
"""

NOT_SUCCESS_DECOMPOSE_PLAN_FORMAT = """Here is a decompose plan:
Nodes: {nodes}
Edges: {edges}
Entry: {entry}
Exit: {exit}

The performance of the plan is unknown.
"""
PERSON_INFO_FORMAT = """{name} is at {position} holding {items}"""

ENVIRONMENT_INFO_FORMAT = """At {time}, {person_info}. There are various blocks in the vicinity, including {block_list}. There is a sign saying {sign_info}."""

SUMMARY_ENVIRONMENT_SYSTEM_PROMPT = """You are a helpful assistant in Minecraft.
Based on the environment info and the task, extract the key information and summarize the environment info in a concise and informative way.
You should focus on the entities, blocks, and creatures in the environment, and provide a summary of the environment info.
"""

SUMMARY_ENVIRONMENT_EXAMPLE_PROMPT = [
    """The environment info:
{"person_info": [{"name": "Tom", "position": [-1, -59, 1], "held_items": {"spruce_planks": 1}}], "blocks_info": [{"spruce_planks": [-3, -60, 0]}, {"grass_block": [-2, -61, 0]}, {"chest": [-4, -60, 0], "facing": "W"}, {"oak Log": [-3, -61, 0]}, {"birch_slab": [-3, -60, -1]}, {"birch_slab": [-3, -60, 1]}, {"dirt": [-2, -62, 0]}, {"grass_block": [-2, -61, -1]}, {"grass_block": [-2, -61, 1]}, {"crafting_table": [-4, -60, -1]}, {"facing": "W", "furnace": [-4, -60, 1]}, {"stone_pressure_plate": [-3, -60, 2]}], {"juggle_button": [-3, -60, 3]}], "time": "sunrise"},
nearby_entities': [{'Alice': [42, -59, 125], 'other_entity': 'Alice'}, {'pig': [-3, -59, 0]}, {'pig': [-3, -59, 2]}]
*** The task *** : cook meat in the Minecraft.
""",
    """The summary of the environment info:
Entity: Tom is located at position [-1, -59, 1] and is holding one spruce plank, Alice is located at position [42, -59, 125].
Blocks: a chest at [-4, -60, 0] facing west, a furnace at [-4, -60, 1] and other bloces.
Creatures: two pigs at [-3, -59, 0] and [-3, -59, 2].
Interactive-Items: a stone pressure plate at [-3, -60, 2], a juggle button at [-3, -60, 3].
Environment: [flatten area] A wall maybe at [-3, -60, 0], a house maybe at [-4, -60, 0], a tree maybe at [-3, -61, 0]. (They are estimated based on the blocks around.)
""",
    """The environment info:
{environment_info}
*** The task *** : {task}.
Return with Entity, Blocks, Creatures, Interactive-Items and Environment, and give all these position of these blocks and entities like chest, crafting table, furnace, animals, and plants.
"""
]

HISTORY_SUMMARY_PROMPT = """You are {name}. Your task is to create a concise running summary of actions and information results in the provided text, focusing on key and potentially important information to remember.

You will receive the current summary and the your latest actions. Combine them, adding relevant key information from the latest development in 1st person past tense and keeping the summary concise.
The subject of the sentence should be {name}.

Summary So Far:
{summary_so_far}

Latest Development:
{latest_development}

Your Summary:
"""



