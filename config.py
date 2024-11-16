import json
import argparse
import os
import random

room_width = 15
room_height = 15
wall_width = 1

orx = 0     #origin_point
ory = -61
orz = 0

task_number = 5

template = {
    "api_model": "gpt-4-1106-preview",
    "api_base": "https://api.chatanywhere.tech/v1",
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
    "document_file": "data\\recipe_hint.json",
    "host": "10.192.40.144",
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
    
def generate_config(task, api_model, host, port, agent_num=2):
    assert api_model in ["gpt-4-1106-preview", "gpt-3.5-turbo-1106", "glm-4", "glm-3-turbo", "gemini-pro"], "api_model not supported"
    assert task in ["construction", "farming", "puzzle"], "task not supported"

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

    elif task == "dig":
        with open("data/blocks.json", "r") as f:
            blocks = json.load(f)
        if task_number > len(blocks):
            print("TASK NUMBER IS TOO BIG!")
            return
        block_id_list = random.sample(range(len(block_id_list), task_number))
        for i, id in enumerate(block_id_list):
            tool = "default"
            block = blocks[id]
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = block["name"]
            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
            arg_dict["y"] = random.randint(ory + 1, ory + 5)
            if block["material"] != "default":
                tool = block["material"].split("/", 1)[1]
                arg_dict["tool"] = f"diamond_{tool}"
                # # #
                arg_dict["item_position"] = "inventory"
                # # #
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "dig"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = ""
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
        if task_number > len(recipes):
            print("TASK NUMBER IS TOO BIG!")
            return
        item_id_list = random.sample(range(len(recipes), task_number))
        for i, id in enumerate(item_id_list):
            item = recipes[id]["result"]
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = item["name"]
            # # #
            arg_dict["item_position"] = "inventory" 
            arg_dict["step"] = 1
            # # #
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_goal"] = ""
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
            if placeable:
                placeable_blocks.append(block)
        if task_number > len(placeable_blocks):
            print("TASK NUMBER IS TOO BIG!")
            return
        block_id_list = random.sample(range(len(block_id_list), task_number))
        for i, id in enumerate(block_id_list):
            block = placeable_blocks[id]
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = block["name"]
            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
            arg_dict["y"] = random.randint(ory + 1, ory + 5)
            facing = []
            for state in block["states"]:
                for face in state["values"]:
                    facing.append(face)
            if facing:
                arg_dict["facing"] = random.choice(facing)
            # # #
            arg_dict["item_position"] = "inventory"
            # # #
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "place"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = ""
            config["host"] = host
            config["port"] = port
            if facing:
                config["task_name"] = f"place_{arg_dict['target']}_{arg_dict['facing']}_{arg_dict['item_position']}_id{i}"
            else:
                config["task_name"] = f"place_{arg_dict['target']}_{arg_dict['item_position']}_id{i}"
            config_list.append(config)

    elif task == "useitem":
        pass

    elif task == "move":
        for i in range(task_number):
            config = template.copy()
            arg_dict = arg_template.copy()
            arg_dict["target"] = ""
            arg_dict["x"] = random.randint(orx + wall_width, orx + room_width + wall_width - 1)
            arg_dict["z"] = random.randint(orz + wall_width, orz + room_width + wall_width - 1)
            arg_dict["y"] = random.randint(ory + 1, ory + 5)
            config["task_type"] = "meta"
            config["task_idx"] = i
            config["agent_num"] = 1
            config["task_scenario"] = "move"
            config["evaluation_arg"] = arg_dict
            config["task_goal"] = ""
            config["host"] = host
            config["port"] = port
            config["task_name"] = f"move_id{i}"
            config_list.append(config)
            
    elif task == "interact":
        pass

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
    generate_config(args.task, args.api_model, args.host, args.port, args.agent_num)