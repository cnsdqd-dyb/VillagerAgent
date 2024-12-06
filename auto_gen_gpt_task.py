from pipeline.utils import format_string, extract_info
from env.env import VillagerBench, env_type, Agent
from pipeline.controller import GlobalController
from pipeline.data_manager import DataManager
from pipeline.task_manager import TaskManager
import json
from model.init_model import init_language_model
import random
import os
from datetime import datetime

if __name__ == "__main__":

    # Set Environment
    env = VillagerBench(env_type.auto, task_id=0, _virtual_debug=False, dig_needed=False, host="10.214.180.148", task_name="auto_gen")

    # Set Agent
    api_key_list = json.load(open("API_KEY_LIST", "r"))["AGENT_KEY"] # use OPENAI as an example
    base_url = "https://api.chatanywhere.tech/v1"
    llm_config = {
        "api_model": "gpt-4-1106-preview", # for example, "gpt-4-1106-preview"
        "api_base": base_url, # for example, "https://api.openai.com/v1"
        "api_key_list": api_key_list
    }

    Agent.model = llm_config["api_model"]
    Agent.base_url = base_url
    Agent.api_key_list = api_key_list

    # more agent tools can be added here you can refer to the agent_tool in doc/api_library.md
    basic_tools = [
        Agent.scanNearbyEntities, Agent.navigateTo, Agent.attackTarget,
        Agent.UseItemOnEntity,
        Agent.MineBlock, Agent.placeBlock, Agent.equipItem,
        Agent.handoverBlock, Agent.SmeltingCooking, Agent.talkTo, Agent.waitForFeedback,
        Agent.withdrawItem, Agent.storeItem, Agent.craftBlock,Agent.ToggleAction, 
    ]
    all_tools = [
        Agent.scanNearbyEntities, Agent.navigateTo, Agent.attackTarget,
        Agent.navigateToBuilding, Agent.navigateToAnimal, Agent.navigateToPlayer,
        Agent.UseItemOnEntity, Agent.sleep, Agent.wake,
        Agent.MineBlock, Agent.placeBlock, Agent.waitForFeedback, Agent.equipItem,
        Agent.tossItem, Agent.talkTo, Agent.handoverBlock,
        Agent.withdrawItem, Agent.storeItem, Agent.craftBlock,
        Agent.SmeltingCooking, Agent.erectDirtLadder, Agent.dismantleDirtLadder,
        Agent.enchantItem, Agent.trade, Agent.repairItem, Agent.eat,
        Agent.drink, Agent.wear, Agent.layDirtBeam, Agent.removeDirtBeam,
        Agent.openContainer, Agent.closeContainer,
        Agent.fetchContainerContents, Agent.ToggleAction,
        Agent.get_entity_info, Agent.get_environment_info, 
        Agent.performMovement, Agent.lookAt, Agent.startFishing,
        Agent.stopFishing, Agent.read, Agent.readPage, Agent.write,
        Agent.mountEntity, Agent.dismountEntity, Agent.rideEntity, Agent.disrideEntity,
    ]
    other_tools = [tool for tool in all_tools if tool not in basic_tools]
 
    llm = init_language_model(llm_config)

    # Define lists of actions, materials, entities, etc.
    actions = [
        "Agent can talk with other agents in the environment.",
        "Agent can move to a specific location in the environment.",
        "Agent can equip items in the environment.",
        "Agent can craft items in the environment.",
        "Agent can interact with other agents and entities in the environment.",
        "Agent can attack other agents and entities in the environment.",
        "Agent can dig the ground in the environment."
        "Agent can read the signs."
        "Agent can feed animals, mount the horse."
        "Agent can use chest, furnace, crafting table."
        "Agent can sleep and wake up."
    ]

    materials = ["wooden", "stone", "iron", "golden", "diamond", "netherite"]
    agents = ["Alice", "Bob"]
    entities = ["zombie", "skeleton", "sheep", "cow", "rabbit", "pig", "chicken", "creeper", "spider", "enderman"]
    equipments = ["helmet", "chestplate", "leggings", "boots"]
    food = ["mutton", "beef", "rabbit", "porkchop", "chicken", "potato", "cod", "salmon", "wheat_seeds", "melon_seeds", "pumpkin_seeds", "beetroot_seeds"]
    other_food = ["apple", "golden_apple", "carrot", "beetroot", "bread", "cookie", "baked_potato", "pumpkin_pie", "beetroot_soup", "rabbit_stew", "mushroom_stew"]
    tools = ["axe", "pickaxe", "shovel", "hoe", "sword", "flint_and_steel", "compass", "shears", "fishing_rod", "clock"]

    # Randomly select a subset of actions
    selected_actions = random.sample(actions, k=len(actions))

    # Generate prompt with random actions
    prompt_task_description = format_string("""
    Generate a task description for the agent to complete in the Minecraft environment. The task should be designed in various styles.
    {{selected_actions}}
    Agent can not trade or talk with villagers, the task can be finished in 3~5 stepsis better.
    Agent can be given materials, foods, tools, for finish the task.
    The task can focus on crafting, building, fighting, exploring, farming, talking, etc. Make the task simple and in detail.                                     
    The common materials, entities, equipments, food, and tools names:
    materials: {{materials}}
    agents: {{agents}}
    entities: {{entities}}
    equipments: {{equipments}}
    food: {{food}}
    other_food: {{other_food}}
    tools: {{tools}}
    You need to design a task description that includes 3~5 of the above actions for agents to complete.
    return in json format.
    {
        "main_actions": [...], a list of main actions designed for agents to complete in the Minecraft environment (no more than 5).
        "agents": [...], a list of agents in the environment.
        "task_description": str, "The task description designed for each agent to complete in the Minecraft environment."
        "entities": [...], a list of entities in the environment.
        "materials": [...], a list of materials in the environment.
        "equipments": [...], a list of equipments in the environment.
        "tools": [...], a list of tools in the environment.
        "milestones": [...], a list of milestones designed for agents to complete in the Minecraft environment.
    }
    """, {
        "selected_actions": ', '.join(selected_actions),
        "materials": materials,
        "agents": agents,
        "entities": entities,
        "equipments": equipments,
        "food": food,
        "other_food": other_food,
        "tools": tools
    })

    # Use LLM to generate task description
    task_description = llm.few_shot_generate_thoughts("", prompt_task_description, cache_enabled=True, json_check=True, temperature=0.3)
    task_description = extract_info(task_description)[0]
    task_description_str = str(task_description["milestones"])
    print(task_description)
    # input()

    # Use LLM to select the agent tool
    prompt_agent_tool = """
    Select the agent tool for the agent to complete the task in the Minecraft environment. The agent basic tools are:
    scanNearbyEntities, navigateTo, attackTarget, UseItemOnEntity,
    MineBlock, placeBlock, equipItem, handoverBlock, SmeltingCooking, 
    talkTo, waitForFeedback, withdrawItem, storeItem, craftBlock, ToggleAction
    
    The agent advanced tools are:
    navigateToBuilding, navigateToAnimal, navigateToPlayer, sleep, wake, tossItem, erectDirtLadder, dismantleDirtLadder, enchantItem, trade, repairItem, eat, drink, wear, layDirtBeam, removeDirtBeam, openContainer, closeContainer, fetchContainerContents, get_entity_info, get_environment_info, performMovement, lookAt, startFishing, stopFishing, read, readPage, write, mountEntity, dismountEntity, dismountEntity, rideEntity, disrideEntity
    
    Current Task Description is:
    {{TASK_JSON}}
    
    return in json format.
    {
        "agent_tool": [...], a list of agent tools selected for the agent to complete the task in the Minecraft environment.
    }
    """
    prompt_agent_tool = format_string(prompt_agent_tool, {"TASK_JSON": task_description})
    response = llm.few_shot_generate_thoughts("", prompt_agent_tool, cache_enabled=True, json_check=True)
    agent_tool_dict = extract_info(response)[0]
    agent_tool = basic_tools
    if type(agent_tool_dict) == list:
        agent_tool_dict = {"agent_tool": agent_tool_dict}
    for tool_name in agent_tool_dict["agent_tool"]:
        for t in all_tools:
            if t.name == tool_name:
                agent_tool.append(t)

    # Use LLM to generate OP command
    prompt_op_command = """
    Generate a OP command for the agent to complete in the Minecraft environment. The OP command should be designed in various styles.
    1. set the block in the environment:
    /setblock int int int chest{Items:[{Slot:int, id:"minecraft:name", Count:int}, {Slot:int, id:"minecraft:name", Count:int}]}
    2. set the time in the environment:
    /time set day/night
    3. set the weather in the environment:
    /weather clear/rain/thunder
    4. summon entities in the environment:
    /summon name int int int
    5. write text on the sign in the environment:
    /setblock int int int jungle_wall_sign[facing=north]{Text1:str, Text2:str}
    6. set the environment:
    "prefix": ["desert_","plains_","savanna_","snowy_","taiga_"],
    "houses": ["animal_pen", "butcher_shop", "cartographer_house", "butcher_shop", "farm", "fletcher_house", "library", "shepherd_house", "small_house", "weaponsmith", "medium_house"],
    /place template prefix+houses

    Remember: equippent should named in material_toolname format like: iron_sword.

    You need to generate OP according to the task json generated by the LLM.
    The task json:
    {{TASK_JSON}}
    remember the center of the environment is (0, -60, 0). 
    The environment size is 15*10*15.
    houses are placed in the center 5*10*5 area.
    materials, chest and agents should be placed in x,z in -15~-5 or 5~15.
    return in json format.
    {
        "environ_op":["/..."], a list of OP for set the environment.
        "place_op": str, place template house OP.
        "entities_op":["/..."], a list of OP to summon the entites.
        "blocks_op":["/..."], a list of OP to set the useful blocks.
        "inventory_op":["/..."], a list of OP to add useful materials to agents or chests.
    }
    """
    op_prompt = format_string(prompt_op_command, {"TASK_JSON": task_description})
    # /setblock x y z jungle_wall_sign[facing=north]{{Text1:\"{{\\\"text\\\":\\\"{Text you want to write 1.}\\\"}}\",Text2:\"{{\\\"text\\\":\\\"{Text you want to write 2.}\\\"}}\"}}
    response = llm.few_shot_generate_thoughts("", op_prompt, cache_enabled=True, json_check=True)
    op_command = extract_info(response)[0]
    print(op_command)
    # input()

    # OP rewrite
    prompt_op_command_prefix = """
    You should rewrite the OP command to the correct format.
    The OP command is:
    """
    prompt_op_command_postfix = """
    The correct format is:
    /setblock x y z jungle_wall_sign[facing=north]{{Text1:\"{{\\\"text\\\":\\\"{Text you want to write 1.}\\\"}}\",Text2:\"{{\\\"text\\\":\\\"{Text you want to write 2.}\\\"}}\"}}
    return in json format.
    {
        "rewrite_op": str, "The rewrited OP command."
    }
    """
    for i, op in enumerate(op_command["blocks_op"]):
        if "Text1" in op:
            prompt_op_command = prompt_op_command_prefix + op + prompt_op_command_postfix
            response = llm.few_shot_generate_thoughts("", prompt_op_command, cache_enabled=True, json_check=True)
            op_command["blocks_op"][i] = extract_info(response)[0]["rewrite_op"]
    # Save OP to JSON
    op_filename = datetime.now().strftime("%Y%m%d%H%M%S_op.json")
    op_filepath = os.path.join("auto_task/op_commands", op_filename)
    os.makedirs(os.path.dirname(op_filepath), exist_ok=True)
    with open(op_filepath, 'w') as op_file:
        json.dump(op_command, op_file, indent=4)
    
    env.op_path = op_filepath
    print(f"OP commands saved to {op_filepath}")
    # input()

    # Register Agent
    env.agent_register(agent_tool=agent_tool, agent_number=len(task_description["agents"]), name_list=task_description["agents"]) # Attention that the agent number should be consistent with the agent_tool

    # Run Environment
    with env.run():
        
        # Set Data Manager
        dm = DataManager(silent=False)
        dm.update_database_init(env.get_init_state())

        # Set Task Manager
        tm = TaskManager(silent=False)

        # Set Controller
        ctrl = GlobalController(llm_config, tm, dm, env)

        # Set Task
        tm.init_task(task_description_str, {})

        # Run Controller
        ctrl.run()