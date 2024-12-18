import json
import argparse
import os
import random
import string
import tqdm

import logging
from pipeline.utils import *
from model.init_model import init_language_model
from model.openai_models import OpenAILanguageModel

room_width = 25
room_height = 15
wall_width = 1

orx = 0     #origin_point
ory = -61
orz = 0

task_number = 1

logger = init_logger("TASK_GOAL", dump=False, level=logging.DEBUG, silent=False)

api_key_list = json.load(open("API_KEY_LIST", "r"))["AGENT_KEY"]
llm_config = {
    # "api_model": "gpt-4o",
    "api_model": "gpt-4-1106-preview",
    # "api_base": "https://api.openai.com/v1/",
    "api_base": "https://api.chatanywhere.tech/v1",
    "api_key_list": api_key_list,
    "api_key": api_key_list[0]
}
# llm_config = {
#     "api_key": "sk-villageragent",
#     "api_base": "http://10.130.130.13:8000/v1",
#     "api_model": "llama_gptq4/"
# }
# llm_config = {
#     "api_key": "sk-qwen05b",
#     "api_base": "http://10.130.130.13:8002/v1",
#     "api_model": "/mount/NAS1/public/Qwen2.5-0.5B-Instruct-GPTQ-Int8"
# }
llm = init_language_model(llm_config)
# task_goal_prompt = "Randomly choose another way to express the following sentence. Try to change the sentence pattern instead of replacing words and try to avoid repetitive sentence patterns as much as possible. Making sure the meaning does not change: "
task_goal_prompt = """
I need you to rewrite the following sentence while keeping its original meaning intact. Your goal is to create sentence variations that are rich in structure and expression. Please follow these guidelines:
1. Preserve the core meaning of the original sentence.
2. Keep the word with '_', do not replace them with other words.
You can diversify the sentence structure by:
1. Changing the word order or introducing inversion.
2. Using synonyms or rephrasing.
3. Switching between active and passive voice.
4. Incorporating participle phrases or dependent clauses.

Remember, You should still keep the original meaning of the sentence, and avoid making changes that alter the original meaning.
Make the task description clear and concise, and avoid unnecessary information.
You should randomly select only one sentence from your rewritten version and return it.

"""

template = {
    "api_model": "/mount/NAS1/public/Qwen2.5-7B-Instruct-GPTQ-Int4",
    "api_base": "http://10.130.130.13:8003/v1",
    "task_type": "meta",
    "task_idx": 0,
    "agent_num": 1,
    "dig_needed": False,
    "max_task_num": 0,
    "task_goal": "You are on a farm where you need to collaborate to make a rabbit_stew. Some ingredients are contained within chests, and if the ingredients are not in the chests, you may need to work together to acquire them. Crafting table is placed to craft items",
    "task_scenario": "craft",
    "evaluation_arg": {
        "target": "rabbit_stew",
        "x": 8,
        "y": -60,
        "z": 8,
        "facing": "",
        "item_position": "inventory",
        "tool": "",
        "action": "",
        "step": 1,
        "other_arg": []
    },
    "document_file": "",
    "host": "10.214.180.148",
    "port": 25565,
    "task_name": ""
}

arg_template = {
    "target": "rabbit_stew",
    "x": 8,
    "y": -60,
    "z": 8,
    "facing": "",
    "item_position": "inventory",
    "tool": "",
    "action": "",
    "step": 1,
    "other_arg": []
}

def select_task_goal(task):
    if task == "construction":
        return "Using the provided blueprint, please collaborate to place blocks in Minecraft. You have access to two chests: one contains a selection of materials, and the other, located in the factory, is equipped with tools which is not needed for this task. The task is completed when the blueprint is fully constructed."
    elif task == "farming_rabbit_stew":
        return "You are on a farm where you need to collaborate to make a rabbit_stew. Some ingredients are contained within chests, and if the ingredients are not in the chests, you may need to work together to acquire them. Crafting table is placed to craft items"
    elif task == "farming_cake":
        return "You are on a farm where you need to collaborate to make a cake. Some ingredients are contained within chests, and if the ingredients are not in the chests, you may need to work together to acquire them. Crafting table is placed to craft items"
    elif task == "puzzle":
        return "Attention all agents, you are tasked with a cooperative multi-stage escape challenge. Each 10x10 room requires teamwork to solve puzzles and overcome obstacles. Be advised that you may be separated into different rooms, where direct collaboration isn't always possible. Despite this, leverage your strengths to progress as a unit. Upon task completion, you'll either be transported to the next room or the path will clear for you to proceed on foot. The rooms are aligned along the z-axis, with the center points spaced 10 units apart. Your final objective is to reach the exit at coordinates 130, -60, -140. Coordinate, adapt, and work together to escape. Good luck!"
    else:
        raise NotImplementedError

def generate_task_goal(task_scenario, arg_dict):
    template_prompt = ""
    if task_scenario == "dig":
        if arg_dict["tool"]:
            template_prompt = f"Use {arg_dict['tool']} to dig the {arg_dict['target']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). The {arg_dict['tool']} is in the {arg_dict['item_position']}."
        else:
            template_prompt = f"Dig the {arg_dict['target']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). You can dig it directly and don't need to use any tool."
    
    elif task_scenario == "craft":
        template_prompt = f"Use crafting_table to make a {arg_dict['target']}. All ingredients are in the {arg_dict['item_position']}."
    
    elif task_scenario == "place":
        if arg_dict["facing"] in ["north", "south", "east", "west"]:
            template_prompt = f"Place a {arg_dict['target']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}), facing {arg_dict['facing']}. The {arg_dict['target']} is in the {arg_dict['item_position']}."
        elif arg_dict["facing"] in ["x", "y", "z"]:
            template_prompt = f"Place a {arg_dict['target']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}), along the {arg_dict['facing']}-axis. The {arg_dict['target']} is in the {arg_dict['item_position']}."
        elif len(arg_dict["other_arg"]) == 1:
            template_prompt = f"Place a {arg_dict['target']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). The {arg_dict['target']} is in the {arg_dict['item_position']}."
        else:
            template_prompt = f"Place {len(arg_dict['other_arg'])} {arg_dict['target']} at "
            for i, block_pos in enumerate(arg_dict["other_arg"]):
                template_prompt += f"({block_pos[0]}, {block_pos[1]}, {block_pos[2]})"
                if i == len(arg_dict["other_arg"]) - 2:
                    template_prompt += " and "
                elif i == len(arg_dict["other_arg"]) - 1:
                    template_prompt += f". The {arg_dict['target']} is in the {arg_dict['item_position']}."
                else:
                    template_prompt += " , "
    elif task_scenario == "useitem":
        if "sign" in arg_dict["target"]:
            template_prompt = f"Place a {arg_dict['target']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}), and write '{arg_dict['other_arg'][0]}' on it. The {arg_dict['target']} is in the {arg_dict['item_position']}."
        else:
            template_prompt = f"Equip the {arg_dict['target']}. The {arg_dict['target']} is in the {arg_dict['item_position']}."
    elif task_scenario == "move":
        template_prompt = f"Move to ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). You may need some block or tool to get to that position, you can find them in the {arg_dict['item_position']}."
    
    elif task_scenario == "interact":
        if arg_dict["action"] in ["attack", "feed", "shear", "milk"]:
            template_prompt = f"Use {arg_dict['tool']} to {arg_dict['action']} the {arg_dict['target']}. The {arg_dict['tool']} is in the {arg_dict['item_position']}"
        elif arg_dict["action"] == "cook":
            template_prompt = f"Cook the {arg_dict['other_arg'][-1]} in furnace by coal. The coal and the {arg_dict['other_arg'][-1]} are in the {arg_dict['item_position']}."
        elif arg_dict["action"] == "handover":
            template_prompt = f"Hand over a {arg_dict['other_arg'][0]} to {arg_dict['target']}. The {arg_dict['other_arg'][0]} is in the {arg_dict['item_position']}."
        elif arg_dict["action"] == "store":
            template_prompt = f"Store a {arg_dict['other_arg'][0]} in the chest. The chest is at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']})."
            # "till", "fishing", "bone_meal", "chat", "sign", "toggle", "saddle", "boat", "minecart", "bed"
        elif arg_dict["action"] == "till":
            size = arg_dict["other_arg"][0]["size"]
            template_prompt = f"Till the land at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}) to farmland. The hoe is in the {arg_dict['item_position']}, plant the {arg_dict['other_arg'][0]['crops']} in the farmland."
        elif arg_dict["action"] == "fishing":
            template_prompt = f"Go fishing at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). The fishing rod is in the {arg_dict['item_position']}."
        elif arg_dict["action"] == "bone_meal":
            template_prompt = f"First place the {arg_dict['other_arg'][0]['crops']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). Then use bone meal to grow it. The bone meal is in the {arg_dict['item_position']}. If the {arg_dict['other_arg'][0]['crops']} is not in the {arg_dict['item_position']}, you can find seeds or crop in the {arg_dict['item_position']}."
        elif arg_dict["action"] == "sign":
            sign = arg_dict["target"]
            template_prompt = f"Read the content on the {sign} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']})."
        elif arg_dict["action"] == "toggle":
            if "iron" in arg_dict["target"]:
                template_prompt = f"Use {arg_dict['tool']} to open the {arg_dict['target']}. The {arg_dict['target']} is at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). The {arg_dict['tool']} is in the {arg_dict['item_position']}."
            else:
                template_prompt = f"Open the {arg_dict['target']} at ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). You can open it directly and do not need any tool."
        elif arg_dict["action"] == "saddle":
            template_prompt = f"Put the {arg_dict['tool']} on the {arg_dict['target']} and ride it, then dismount it. The {arg_dict['tool']} and the food are in the {arg_dict['item_position']}."
        elif arg_dict["action"] == "boat":
            template_prompt = f"Ride the {arg_dict['target']} and dismount it. The boat is in the {arg_dict['item_position']}."
        elif arg_dict["action"] == "minecart":
            template_prompt = f"Ride the {arg_dict['target']} and dismount it. The minecart is in the {arg_dict['item_position']}."
        elif arg_dict["action"] == "bed":
            template_prompt = f"Sleep in the {arg_dict['target']}. The bed is in the {arg_dict['item_position']}, then wake up."
        elif arg_dict["action"] == "chat":
            positive_attribute = arg_dict["other_arg"][0]["positive_attribute"]
            negative_attribute = arg_dict["other_arg"][0]["negative_attribute"]
            topic = arg_dict["other_arg"][0]["topic"]
            template_prompt = f"Alice is acting as a {positive_attribute} person, but Bob is acting as a {negative_attribute} person. Start a conversation about {topic} for at least 5 turns. (This task should be assigned to two agents for each time)"
        elif arg_dict["action"] == "ladder":
            size = arg_dict["other_arg"][0]["size"]
            template_prompt = f"Build a {size} ladder upward start from ({arg_dict['x']}, {arg_dict['y']}, {arg_dict['z']}). The ladder is in the {arg_dict['item_position']}, you may use some dirts at near places internally to place the ladder."
    
    template_prompt = template_prompt.replace("the inventory", "your inventory")
    if random.randint(1, 2) == 1: # 有小概率直接用原始的prompt
        task_goal = template_prompt
    else:
        template_prompt = "Original Sentence: " + template_prompt
        task_goal = llm.few_shot_generate_thoughts(system_prompt=task_goal_prompt, example_prompt=template_prompt, temperature=0.2)
    logger.warning(task_goal)
    logger.debug("-" * 50)
    return task_goal

def generate_config(task, api_model, host, port, agent_num=2):
    # assert api_model in ["gpt-4-1106-preview", "gpt-3.5-turbo-1106", "glm-4", "glm-3-turbo", "gemini-pro"], "api_model not supported"
    # assert task in ["construction", "farming", "puzzle"], "task not supported"

    config_list = []
    if task == "construction":
        for i in range(0,100):
            task_goal = select_task_goal(task)
            config = template.copy()
            config["api_model"] = api_model
            config["host"] = host
            config["port"] = port
            config["task_idx"] = i
            config["task_type"] = task
            config["task_goal"] = task_goal
            config["agent_num"] = agent_num
            config["task_name"] = f"{config['api_model']}_{task}_task{i}_{config['agent_num']}p"
            config["document_file"] = f"data\\map_description.json"
            config_list.append(config)

    elif task == "farming":
        for i in range(0,1):
            if i <= 35:
                task_goal = select_task_goal("farming_cake")
            else:
                task_goal = select_task_goal("farming_rabbit_stew")

            config = template.copy()
            config["api_model"] = api_model
            config["host"] = host
            config["port"] = port
            config["task_idx"] = i
            config["task_type"] = task
            config["agent_num"] = agent_num
            config["task_goal"] = task_goal
            config["task_name"] = f"{config['api_model']}_{task}_task{i}_{config['agent_num']}p"
            config["document_file"] = f"data\\recipe_hint.json"
            config_list.append(config)
    
    elif task == "puzzle":
        for i in range(1,5):
            for j in range(0,8-i):
                task_goal = select_task_goal(task)
                config = template.copy()
                config["api_model"] = api_model
                config["host"] = host
                config["port"] = port
                config["task_idx"] = j
                config["task_type"] = task
                config["agent_num"] = agent_num
                config["max_task_num"] = i
                config["task_goal"] = task_goal
                config["task_name"] = f"{config['api_model']}_{task}_task{i}_{config['agent_num']}p" + f"_idx{j}"
                config["document_file"] = ""
                config_list.append(config)
    elif task == "meta":
        for i in tqdm.tqdm(range(0, 100)):
            random_task = random.choices(["dig", "craft", "place", "useitem", "move", "interact"], [0.1, 0.2, 0.1, 0.05, 0.05, 0.4])[0]
            if random_task == "dig":
                with open("data/blocks.json", "r") as f:
                    blocks = json.load(f)
                block_id_list = random.sample(range(len(blocks)), k=task_number)
                for i, id in enumerate(block_id_list):
                    block = blocks[id]
                    tool = block["material"]
                    config = template.copy()
                    arg_dict = arg_template.copy()
                    arg_dict["target"] = block["name"]
                    arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                    arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                    arg_dict["y"] = random.randint(ory + 1, ory + 3)
                    if tool == "coweb":
                        tool = "sword"
                        arg_dict["tool"] = f"diamond_{tool}"
                        # # #
                        arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                        # # #
                    elif "mineable" in tool:
                        tool = block["material"].split("/", 1)[1]
                        arg_dict["tool"] = f"diamond_{tool}"
                        # # #
                        arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                        # # #
                    else:
                        tool = "default"
                    config["task_type"] = "meta"
                    config["task_idx"] = i
                    config["agent_num"] = 1
                    config["task_scenario"] = "dig"
                    config["evaluation_arg"] = arg_dict
                    config["task_goal"] = generate_task_goal(random_task, arg_dict)
                    config["host"] = host
                    config["port"] = port
                    if tool != "default":
                        config["task_name"] = f"dig_{arg_dict['target']}_{tool}_{arg_dict['item_position']}_id{i}"
                    else:
                        config["task_name"] = f"dig_{arg_dict['target']}_{tool}_id{i}"
                    config_list.append(config)

            elif random_task == "craft":
                with open("data/recipes.json", "r") as f:
                    recipes = json.load(f)
                item_id_list = random.sample(range(len(recipes)), k=task_number)
                for i, id in enumerate(item_id_list):
                    item = recipes[id]["result"]
                    config = template.copy()
                    arg_dict = arg_template.copy()
                    arg_dict["target"] = item["name"]
                    # # #
                    arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"]) 
                    arg_dict["step"] = 1
                    # # #
                    config["task_type"] = "meta"
                    config["task_idx"] = i
                    config["agent_num"] = 1
                    config["task_goal"] = generate_task_goal(random_task, arg_dict)
                    config["task_scenario"] = "craft"
                    config["evaluation_arg"] = arg_dict
                    config["document_file"] = "data\\recipes_hint.json"
                    config["host"] = host
                    config["port"] = port
                    config["task_name"] = f"craft_{arg_dict['target']}_{arg_dict['item_position']}_{arg_dict['step']}_id{i}"
                    config_list.append(config)

            elif random_task == "place":
                with open("data/blocks.json", "r") as f:
                    blocks = json.load(f)
                placeable_blocks = []
                allowed_facing = {"north", "south", "east", "west", "x", "y", "z"}
                for block in blocks:
                    placeable = True
                    for state in block["states"]:
                        if "values" in state and not all(faceable in allowed_facing for faceable in state["values"]):
                            placeable = False
                            break
                    if "potted" in block["name"] or "_cauldron" in block["name"]:
                        placeable = False
                    if placeable:
                        placeable_blocks.append(block)
                block_id_list = random.sample(range(len(placeable_blocks)), k=task_number)
                with open("data/place_template.json", "r") as f:
                    block_template = json.load(f)
                for i, id in enumerate(block_id_list):
                    block = placeable_blocks[id]
                    config = template.copy()
                    arg_dict = arg_template.copy()
                    arg_dict["target"] = block["name"]
                    arg_dict["x"] = random.randint(orx + wall_width + 2, orx + room_width + wall_width - 3)
                    arg_dict["z"] = random.randint(orz + wall_width + 2, orz + room_width + wall_width - 3)
                    arg_dict["y"] = random.randint(ory + 1, ory + 2)
                    facing = []
                    for state in block["states"]:
                        if "values" in state:
                            for face in state["values"]:
                                facing.append(face)
                    if facing:
                        arg_dict["facing"] = random.choice(facing)
                        block_number = "single"
                    else:
                        block_number = random.choices(["single", "template", "multi"], [40, 50, 10])[0]
                    arg_dict["other_arg"] =[([arg_dict['x'], arg_dict['y'], arg_dict['z']])]
                    if block_number == "multi":
                        another_block = random.choice([1, 2])
                        direction = random.choice([-1, 1])
                        invalid_pos = []
                        while another_block > 0:
                            dx = random.randint(0, 2)
                            dy = random.randint(0, 1)
                            dz = random.randint(0, 2)
                            while dx + dy + dz == 0 or [dx, dy, dz] in invalid_pos:
                                dx = random.randint(0, 2)
                                dy = random.randint(0, 1)
                                dz = random.randint(0, 2)
                            arg_dict["other_arg"].append([arg_dict['x'] + dx * direction, arg_dict['y'] + dy, arg_dict['z'] + dz * direction])
                            invalid_pos.append([dx, dy, dz])
                            another_block -= 1
                    if block_number == "template":
                        direction = random.choice([-1, 1])
                        template_pos = random.choice(block_template)
                        for offset in template_pos["pos"]:
                            arg_dict["other_arg"].append([arg_dict['x'] + offset[0] * direction, arg_dict['y'] + offset[1], arg_dict['z'] + offset[2] * direction])
                    # # #
                    arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                    # # #
                    config["task_type"] = "meta"
                    config["task_idx"] = i
                    config["agent_num"] = 1
                    config["task_scenario"] = "place"
                    config["evaluation_arg"] = arg_dict
                    config["task_goal"] = generate_task_goal(random_task, arg_dict)
                    config["host"] = host
                    config["port"] = port
                    if facing:
                        config["task_name"] = f"place_{block_number}_{arg_dict['facing']}_{arg_dict['item_position']}_id{i}"
                    else:
                        config["task_name"] = f"place_{block_number}_{arg_dict['item_position']}_id{i}"
                    config_list.append(config)

            elif random_task == "useitem":
                target = "equipment"
                # target = random.choice(["equipment", "sign"])
                material = ["chainmail", "iron", "diamond", "golden", "netherite"]
                equipment = ["helmet", "chestplate", "leggings", "boots"]
                charset = string.ascii_letters + string.digits
                for i in range(task_number):
                    config = template.copy()
                    arg_dict = arg_template.copy()
                    if target == "sign":
                        arg_dict["target"] = random.choice(["oak", "spruce", "birch", "acacia", "jungle", "dark_oak", "mangrove"]) + "wall_sign"
                        arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                        arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                        arg_dict["y"] = random.randint(ory + 1, ory + 3)
                        text_len = random.randint(5, 8)
                        arg_dict["other_arg"] = [''.join(random.choices(charset, k=text_len))]
                    else:
                        arg_dict["target"] = random.choice(material) + "_" + random.choice(equipment)

                    config["task_type"] = "meta"
                    config["task_idx"] = i
                    config["agent_num"] = 1
                    config["task_scenario"] = "useitem"
                    config["evaluation_arg"] = arg_dict
                    config["task_goal"] = generate_task_goal(random_task, arg_dict)
                    config["host"] = host
                    config["port"] = port
                    config["task_name"] = f"useitem_{arg_dict['target']}_id{i}"
                    config_list.append(config)

            elif random_task == "move":
                for i in range(task_number):
                    config = template.copy()
                    arg_dict = arg_template.copy()
                    arg_dict["target"] = ""
                    arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                    arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                    arg_dict["y"] = random.randint(ory + 1, ory + 3)
                    config["task_type"] = "meta"
                    config["task_idx"] = i
                    config["agent_num"] = 1
                    config["task_scenario"] = "move"
                    config["evaluation_arg"] = arg_dict
                    config["task_goal"] = generate_task_goal(random_task, arg_dict)
                    config["host"] = host
                    config["port"] = port
                    config["task_name"] = f"move_id{i}"
                    config_list.append(config)
                    
            elif random_task == "interact":
                animal_list = [{"name": "sheep", "food": ["wheat"]}, {"name": "cow", "food": ["wheat"]}, {"name": "rabbit", "food": ["carrot"]}, 
                            {"name": "pig", "food": ["potato", "beetroot", "carrot"]}, {"name": "chicken", "food": ["wheat_seeds", "melon_seeds", "pumpkin_seeds", "beetroot_seeds"]}, 
                            {"name": "horse", "food": ["golden_carrot", "golden_apple", "sugar", "apple"]}, {"name": "wolf", "food": ["bone"]}, {"name": "cat", "food": ["cod", "salmon"]},
                            {"name": "parrot", "food": ["melon_seeds", "pumpkin_seeds"]}, {"name": "fox", "food": ["sweet_berries"]}, {"name": "turtle", "food": ["seagrass"]}, 
                            {"name": "panda", "food": ["bamboo"]}]
                cooked_list = ["mutton", "beef", "rabbit", "porkchop", "chicken", "potato", "cod", "salmon"]
                action_list = ["attack", "feed", "cook", "handover", "store", "shear", "milk"]
                # 额外的几个任务 1. 耕地-并加种子 2. 钓鱼 3.作物加骨粉催熟 4. 小花园 5. 建造一个矩形的栅栏 6. 聊天对话 7. 读写牌子上面的内容
                # 8. 由一个红石线，一个（门/灯）和一个开关组成的电路，要求开关能控制门/灯的开关
                # 9. 给马加上马鞍，并且给马喂食，骑马，下马 / 给猪背上胡萝卜杆，骑猪
                # 10. 乘船，下船。乘矿车，下矿车
                # 11. 建造一面墙
                # 12. 放置床睡觉，然后起床 
                # 13. 搭梯子
                additional_task_list = ["till", "fishing", "bone_meal", "chat", "sign", "toggle", "saddle", "boat", "minecart", "bed"]


                for i in range(task_number):
                    # action = "feed"
                    task_level = random.choice(["basic", "advanced"])
                    if task_level == "basic":
                        action = random.choices(action_list, [10, 10, 9, 28, 28, 2, 2, 10])[0]
                        config = template.copy()
                        arg_dict = arg_template.copy()
                        if action == "cook":
                            target = random.choice(cooked_list)
                            arg_dict["target"] = "furnace"
                        elif action == "store":
                            target = "chest"
                            arg_dict["target"] = "chest"
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = random.randint(ory + 1, ory + 3)
                        elif action in ["handover"]:
                            target = "Bob"
                            arg_dict["target"] = "Bob"
                        elif action == "shear":
                            target = "sheep"
                            arg_dict["target"] = "sheep"
                        elif action == "milk":
                            target = "cow"
                            arg_dict["target"] = "cow"
                        else:
                            target = random.choice(animal_list)
                            arg_dict["target"] = target["name"]
                        arg_dict["action"] = action
                        if action == "attack":
                            arg_dict["tool"] = "iron_sword"
                        elif action == "feed":
                            arg_dict["tool"] = random.choice(target["food"])
                        elif action == "cook":
                            arg_dict["other_arg"] = ["coal", target]
                        elif action == "shear":
                            arg_dict["tool"] = "shears"
                        elif action == "milk":
                            arg_dict["tool"] = "bucket"
                        elif action in ["handover", "store"]:
                            with open("data/items.json", "r") as f:
                                items = json.load(f)
                            arg_dict["other_arg"] = [random.choice(items)["name"]]
                        # # #
                        arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                        # # #
                        config["task_type"] = "meta"
                        config["task_idx"] = i
                        config["agent_num"] = 1
                        config["task_scenario"] = "interact"
                        config["evaluation_arg"] = arg_dict
                        config["task_goal"] = generate_task_goal(random_task, arg_dict)
                        config["host"] = host
                        config["port"] = port
                        config["task_name"] = f"interact_{action}_id{i}"
                        config_list.append(config)
                    else:
                        action = random.choice(additional_task_list)
                        config = template.copy()
                        arg_dict = arg_template.copy()
                        arg_dict["action"] = action
                        if action == "till":
                            arg_dict["target"] = "farmland"
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = ory + 1
                            origin_block = random.choice(["dirt", "grass_block", "coarse_dirt", "podzol", "dirt_path"])
                            # 作物列表
                            crops = ["wheat_seeds", "beetroot_seeds", "melon_seeds", "pumpkin_seeds", "carrot", "potato"]

                            # 锄头列表
                            hoes = ["wooden", "stone", "iron", "golden", "diamond"]
                            arg_dict["tool"] = f"{random.choice(hoes)}_hoe"


                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])


                            arg_dict["other_arg"] = [{"origin_block": origin_block, "crops": random.choice(crops)}]

                        elif action == "fishing":
                            fish = ["cod", "salmon", "tropical_fish", "pufferfish"]
                            arg_dict["target"] = random.choice(fish)
                            
                            arg_dict["tool"] = "fishing_rod"

                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = random.randint(ory - 1, ory)
                        
                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])

                        elif action == "bone_meal":
                            crops_seeds_in_dirt = ["bamboo", "wheat_seeds", "beetroot_seeds", "melon_seeds", "pumpkin_seeds", "carrot", "potato", "nether_wart"]
                            crops_on_sand = ["bamboo", "sugar_cane"]
                            tree_saplings = ["oak_sapling", "spruce_sapling", "birch_sapling", "acacia_sapling", "jungle_sapling", "dark_oak_sapling", "mangrove_sapling"]
                            crops_on_grass = ["tall_grass", "rose_bush", "peony", "lilac", "sunflower"]
                            crops_on_farmland = ["wheat", "beetroot", "carrot", "potato"]

                            base_block = random.choice(["dirt", "grass_block", "coarse_dirt", "podzol", "dirt_path", "farmland"])
                            if base_block == "farmland":
                                crops = random.choice(crops_on_farmland)
                            elif base_block == "dirt":
                                crops = random.choice(crops_seeds_in_dirt)
                            elif base_block == "grass_block":
                                crops = random.choice(crops_on_grass)
                            elif base_block == "coarse_dirt":
                                crops = random.choice(crops_on_sand)
                            else:
                                crops = random.choice(tree_saplings)
                            arg_dict["target"] = "bone_meal"
                            arg_dict["other_arg"] = [{"base_block": base_block, "crops": crops}]
                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                            arg_dict["tool"] = "bone_meal"
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = random.randint(ory + 1, ory + 1)

                        elif action == "chat":
                            # 性格设定
                            positivae_attribute = ["kind", "funny", "smart", "cute", "cool", "brave", "strong", "friendly", "honest", "helpful"]
                            negative_attribute = ["stupid", "boring", "ugly", "weak", "mean", "scary", "selfish", "lazy", "rude", "useless"]
                            # 话题设定
                            topic = ["chest", "inventory", "furnace", "recipe", "animals", "crops", "life", "weather", "zombies"]

                            arg_dict["target"] = "Bob"
                            arg_dict["other_arg"] = [{
                                "positive_attribute": random.choice(positivae_attribute),
                                "negative_attribute": random.choice(negative_attribute),
                                "topic": random.choice(topic)
                            }]

                        elif action == "sign":
                            sign_instruction_easy = ["Welcome to the room", "Please close the door", "Don't touch my stuff", "I'm watching you", "Be careful of the trap", "Don't break the block", "Don't feed the animals", "Don't steal my items", "Don't kill the animals", "Don't destroy the crops"]
                            sign_instruction_hard = ["withdraw items from the chest", "place a dirt block", "dig a hole", "craft a wooden sword"]
                            arg_dict["target"] = "oak_sign"
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = random.randint(ory + 1, ory + 3)
                            if random.randint(1, 3) == 1:
                                arg_dict["other_arg"] = [random.choice(sign_instruction_hard)]
                            else:
                                arg_dict["other_arg"] = [random.choice(sign_instruction_easy)]
                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])

                        elif action == "toggle":
                            trigger = ["button", "lever"]
                            material = ["acacia", "birch", "dark_oak", "jungle", "mangrove", "oak", "spruce"]
                            device = ["door", "trapdoor", "fence"]

                            trigger_flag = random.choices(["default", "trigger"], [70, 30])[0]
                            if trigger_flag == "trigger":
                                arg_dict["target"] = "iron_"+ random.choice(["door", "trapdoor"])
                                arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                                trig = random.choice(trigger)
                                if trig == "button":
                                    trig = random.choice(material) + "_button"
                                arg_dict["tool"] = trig
                            else:
                                arg_dict["target"] = random.choice(material) + "_" + random.choice(device)
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = ory + 1

                        elif action == "saddle":
                            arg_dict["target"] = random.choice(["horse", "pig"])
                            if arg_dict["target"] == "horse":
                                arg_dict["tool"] = "saddle"
                            else:
                                arg_dict["tool"] = "carrot_on_a_stick"
                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
    
                        elif action == "boat":
                            boats = ["boat", "chest_boat"]
                            arg_dict["target"] = random.choice(boats)
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = ory + 1
                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                        
                        elif action == "minecart":
                            arg_dict["target"] = "minecart"
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = ory + 1
                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])

                        elif action == "bed":
                            bed_color = ["red", "blue", "green", "yellow", "white", "black", "brown", "cyan", "gray", "light_blue", "lime", "magenta", "orange", "pink", "purple"]
                            arg_dict["target"] = random.choice(bed_color) + "_bed"
                            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                            arg_dict["y"] = ory + 1
                            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])

                        config["task_type"] = "meta"
                        config["task_idx"] = i
                        config["agent_num"] = 1
                        config["task_scenario"] = "interact"
                        config["evaluation_arg"] = arg_dict
                        config["task_goal"] = generate_task_goal(random_task, arg_dict)
                        config["host"] = host
                        config["port"] = port
                        config["task_name"] = f"interact_{action}_id{i}"
                        config_list.append(config)

    elif task == "dig":
        with open("data/blocks.json", "r") as f:
            blocks = json.load(f)
        block_id_list = random.sample(range(len(blocks)), k=task_number)
        for i, id in enumerate(block_id_list):
            block = blocks[id]
            tool = block["material"]
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = block["name"]
            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
            arg_dict["y"] = random.randint(ory + 1, ory + 3)
            if tool == "coweb":
                tool = "sword"
                arg_dict["tool"] = f"diamond_{tool}"
                # # #
                arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                # # #
            elif "mineable" in tool:
                tool = block["material"].split("/", 1)[1]
                arg_dict["tool"] = f"diamond_{tool}"
                # # #
                arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
                # # #
            else:
                tool = "default"
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "dig"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = generate_task_goal(task, arg_dict)
            config["host"] = host
            config["port"] = port
            if tool != "default":
                config["task_name"] = f"dig_{arg_dict['target']}_{tool}_{arg_dict['item_position']}_id{i}"
            else:
                config["task_name"] = f"dig_{arg_dict['target']}_{tool}_id{i}"
            config_list.append(config)

    elif task == "craft":
        with open("data/recipes.json", "r") as f:
            recipes = json.load(f)
        item_id_list = random.sample(range(len(recipes)), k=task_number)
        for i, id in enumerate(item_id_list):
            item = recipes[id]["result"]
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = item["name"]
            # # #
            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"]) 
            arg_dict["step"] = 1
            # # #
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_goal"] = generate_task_goal(task, arg_dict)
            config["task_scenario"] = "craft"
            config["evaluation_arg"] = arg_dict
            config["document_file"] = "data\\recipes_hint.json"
            config["host"] = host
            config["port"] = port
            config["task_name"] = f"craft_{arg_dict['target']}_{arg_dict['item_position']}_{arg_dict['step']}_id{i}"
            config_list.append(config)

    elif task == "place":
        with open("data/blocks.json", "r") as f:
            blocks = json.load(f)
        placeable_blocks = []
        allowed_facing = {"north", "south", "east", "west", "x", "y", "z"}
        for block in blocks:
            placeable = True
            for state in block["states"]:
                if "values" in state and not all(faceable in allowed_facing for faceable in state["values"]):
                    placeable = False
                    break
            if "potted" in block["name"] or "_cauldron" in block["name"]:
                placeable = False
            if placeable:
                placeable_blocks.append(block)
        block_id_list = random.sample(range(len(placeable_blocks)), k=task_number)
        with open("data/place_template.json", "r") as f:
            block_template = json.load(f)
        for i, id in enumerate(block_id_list):
            block = placeable_blocks[id]
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = block["name"]
            arg_dict["x"] = random.randint(orx + wall_width + 2, orx + room_width + wall_width - 3)
            arg_dict["z"] = random.randint(orz + wall_width + 2, orz + room_width + wall_width - 3)
            arg_dict["y"] = random.randint(ory + 1, ory + 2)
            facing = []
            for state in block["states"]:
                if "values" in state:
                    for face in state["values"]:
                        facing.append(face)
            if facing:
                arg_dict["facing"] = random.choice(facing)
                block_number = "single"
            else:
                block_number = random.choices(["single", "template", "multi"], [40, 50, 10])[0]
            
            arg_dict["other_arg"] = [([arg_dict['x'], arg_dict['y'], arg_dict['z']])]
            if block_number == "multi":
                another_block = random.choice([1, 2])
                direction = random.choice([-1, 1])
                invalid_pos = []
                while another_block > 0:
                    dx = random.randint(0, 2)
                    dy = random.randint(0, 1)
                    dz = random.randint(0, 2)
                    while dx + dy + dz == 0 or [dx, dy, dz] in invalid_pos:
                        dx = random.randint(0, 2)
                        dy = random.randint(0, 1)
                        dz = random.randint(0, 2)
                    arg_dict["other_arg"].append([arg_dict['x'] + dx * direction, arg_dict['y'] + dy, arg_dict['z'] + dz * direction])
                    invalid_pos.append([dx, dy, dz])
                    another_block -= 1
            if block_number == "template":
                direction = random.choice([-1, 1])
                template_pos = random.choice(block_template)
                for offset in template_pos["pos"]:
                    arg_dict["other_arg"].append([arg_dict['x'] + offset[0] * direction, arg_dict['y'] + offset[1], arg_dict['z'] + offset[2] * direction])
            # # #
            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
            # # #
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "place"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = generate_task_goal(task, arg_dict)
            config["host"] = host
            config["port"] = port
            if facing:
                config["task_name"] = f"place_{block_number}_{arg_dict['facing']}_{arg_dict['item_position']}_id{i}"
            else:
                config["task_name"] = f"place_{block_number}_{arg_dict['item_position']}_id{i}"
            config_list.append(config)

    elif task == "useitem":
        target = "equipment"
        # target = random.choice(["equipment", "sign"])
        material = ["chainmail", "iron", "diamond", "golden", "netherite"]
        equipment = ["helmet", "chestplate", "leggings", "boots"]
        charset = string.ascii_letters + string.digits
        for i in range(task_number):
            config = template.copy()
            arg_dict = arg_template.copy()
            if target == "sign":
                arg_dict["target"] = random.choice(["oak", "spruce", "birch", "acacia", "jungle", "dark_oak", "mangrove"]) + "_sign"
                arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                arg_dict["y"] = random.randint(ory + 1, ory + 3)
                text_len = random.randint(5, 8)
                arg_dict["other_arg"] = [''.join(random.choices(charset, k=text_len))]
            else:
                arg_dict["target"] = random.choice(material) + "_" + random.choice(equipment)

            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "useitem"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = generate_task_goal(task, arg_dict)
            config["host"] = host
            config["port"] = port
            config["task_name"] = f"useitem_{arg_dict['target']}_id{i}"
            config_list.append(config)

    elif task == "move":
        for i in range(task_number):
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = ""
            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
            arg_dict["y"] = random.randint(ory + 1, ory + 3)
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "move"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = generate_task_goal(task, arg_dict)
            config["host"] = host
            config["port"] = port
            config["task_name"] = f"move_id{i}"
            config_list.append(config)
            
    elif task == "interact":
        animal_list = [{"name": "sheep", "food": ["wheat"]}, {"name": "cow", "food": ["wheat"]}, {"name": "rabbit", "food": ["carrot"]}, 
                       {"name": "pig", "food": ["potato", "beetroot", "carrot"]}, {"name": "chicken", "food": ["wheat_seeds", "melon_seeds", "pumpkin_seeds", "beetroot_seeds"]}, ]
        cooked_list = ["mutton", "beef", "rabbit", "porkchop", "chicken", "potato", "cod", "salmon"]
        action_list = ["attack", "feed", "cook", "handover", "store", "shear", "milk"]
        for i in range(task_number):
            # action = "feed"
            action = random.choices(action_list, [10, 10, 9, 28, 28, 2, 2, 10])[0]
            config = template.copy()
            arg_dict = arg_template.copy()
            if action == "cook":
                target = random.choice(cooked_list)
                arg_dict["target"] = "furnace"
            elif action == "store":
                target = "chest"
                arg_dict["target"] = "chest"
                arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
                arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
                arg_dict["y"] = random.randint(ory + 1, ory + 3)
            elif action in ["handover"]:
                target = "Bob"
                arg_dict["target"] = "Bob"
            elif action == "shear":
                target = "sheep"
                arg_dict["target"] = "sheep"
            elif action == "milk":
                target = "cow"
                arg_dict["target"] = "cow"
            else:
                target = random.choice(animal_list)
                arg_dict["target"] = target["name"]
            arg_dict["action"] = action
            if action == "attack":
                arg_dict["tool"] = "iron_sword"
            elif action == "feed":
                arg_dict["tool"] = random.choice(target["food"])
            elif action == "cook":
                arg_dict["other_arg"] = ["coal", target]
            elif action == "shear":
                arg_dict["tool"] = "shears"
            elif action == "milk":
                arg_dict["tool"] = "bucket"
            elif action in ["handover", "store"]:
                with open("data/items.json", "r") as f:
                    items = json.load(f)
                arg_dict["other_arg"] = [random.choice(items)["name"]]
            elif action == "chat":
                charset = string.ascii_letters + string.digits
                text_len = random.randint(5, 8)
                arg_dict["other_arg"] = [''.join(random.choices(charset, k=text_len))]
            # # #
            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
            # # #
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "interact"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = generate_task_goal(task, arg_dict)
            config["host"] = host
            config["port"] = port
            config["task_name"] = f"interact_{action}_id{i}"
            config_list.append(config)
    elif task == "toggle":
        action = "toggle"
        config = template.copy()
        arg_dict = arg_template.copy()
        arg_dict["action"] = action
        trigger = ["button", "lever"]
        material = ["acacia", "birch", "dark_oak", "jungle", "mangrove", "oak", "spruce"]
        device = ["door", "trapdoor", "fence"]

        trigger_flag = random.choices(["default", "trigger"], [70, 30])[0]
        if trigger_flag == "trigger":
            arg_dict["target"] = "iron_"+ random.choice(["door", "trapdoor"])
            arg_dict["item_position"] = random.choice(["inventory", "inventory", "chest"])
            trig = random.choice(trigger)
            if trig == "button":
                trig = random.choice(material) + "_button"
            arg_dict["tool"] = trig
        else:
            arg_dict["target"] = random.choice(material) + "_" + random.choice(device)
        arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
        arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
        arg_dict["y"] = ory + 1
        config["task_type"] = "meta"
        config["task_idx"] = 0
        config["agent_num"] = 1
        config["task_scenario"] = "interact"
        config["evaluation_arg"] = arg_dict
        config["task_goal"] = generate_task_goal("interact", arg_dict)
        config["host"] = host
        config["port"] = port
        config["task_name"] = f"interact_{action}_id{0}"
        config_list.append(config)
    with open(f"{api_model}_launch_config_{task}.json", "w") as f:
        json.dump(config_list, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, default="construction", help="task type")
    parser.add_argument("--api_model", type=str, default="gpt-4-1106-preview", help="api model")
    parser.add_argument("--host", type=str, default="10.214.180.148", help="host")
    parser.add_argument("--port", type=int, default=25565, help="port")
    parser.add_argument("--agent_num", type=int, default=1, help="agent number")
    args = parser.parse_args()

    api_model = args.api_model.replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")
    generate_config(args.task, api_model, args.host, args.port, args.agent_num)

    # python config.py --task meta --api_model /mount/NAS1/public/Qwen2.5-7B-Instruct-GPTQ-Int4 