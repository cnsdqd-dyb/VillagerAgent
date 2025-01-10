# farm craft judger
# 这个judger需要加载一个设定的农场地形，将Agent初始化到指定位置
# json文件中包含了农场的地形，以及Agent的初始位置，以及最后的目标合成物品
# 根据Agent的状态，环境的更新，结合json文件，给出累计得分
import shutil
import threading
import time

import numpy as np

from utils import *
import json
import os
import argparse

cooked_rabbit = ["rabbit in chest", "rabbit in pasture"]
baked_potato = ["potato in chest", "potato in farm"]
carrot = ["carrot in chest", "carrot in farm"]
brown_mushroom = ["brown_mushroom in chest", "brown_mushroom in farm"]
bowl = ["bowl in chest", "acacia_log in pasture"]
coal = ["coal in chest", "coal in mine"]

milk = ["milk_bucket in chest", "bucket in chest", "iron_ingot in chest"]
wheat = ["wheat in chest", "hay_block in chest", "wheat in farm", "hay_block in farm"]
sugar = ["sugar in chest", "sugar_cane in chest", "sugar_cane in farm"]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--idx', type=int, default=0, help='the index of the task, range from 0 to 99')
    parser.add_argument('--host', type=str, default="47.113.149.58", help='the host of the server')
    parser.add_argument('--port', type=int, default=25565, help='the port of the server')
    parser.add_argument('--agent_num', type=int, default=1, help='how many agents in the test')
    parser.add_argument("--agent_names", type=str, default="", help="the name of the agents in A,B,C format")
    parser.add_argument("--task_name", type=str, default="test", help="the name of the task")
    args = parser.parse_args()

    agent_names = args.agent_names.split(",")
    with open(".cache/load_status.cache", "w") as f:
        json.dump({"status": "loading"}, f, indent=4)

    if not os.path.exists("result"):
        os.makedirs("result")

    mineflayer = require('mineflayer')
    agent_num = args.agent_num
    task_name = args.task_name

    x_b, y_b, z_b = 41, -60, 122
    min_x, min_y, min_z = -11, 0, 0
    max_x, max_y, max_z = 11, 15, 25
    bot = mineflayer.createBot({
        "host": args.host,
        "port": args.port,
        'username': "farm_judge",
        'checkTimeoutInterval': 600000,
        'auth': 'offline',
        'version': "1.19.2"
    })

    with open("data/farm_setting.json", "r") as f:
        settings = json.load(f)
    assert args.idx < len(settings), "idx out of range, please make sure idx is in [0, 99]"
    task_data = settings[args.idx]

    # 计算复杂度
    complexity = 0
    if "cake" in task_data["name"]:
        for i in range(len(milk)):
            if task_data["milk"] == milk[i]:
                complexity += i
                break

        for i in range(len(wheat)):
            if task_data["wheat"] == wheat[i]:
                complexity += i
                break

        for i in range(len(sugar)):
            if task_data["sugar"] == sugar[i]:
                complexity += i
                break

        complexity += 3
    elif "rabbit_stew" in task_data["name"]:
        for i in range(len(cooked_rabbit)):
            if task_data["cooked_rabbit"] == cooked_rabbit[i]:
                complexity += i
                break

        for i in range(len(baked_potato)):
            if task_data["baked_potato"] == baked_potato[i]:
                complexity += i
                break

        for i in range(len(carrot)):
            if task_data["carrot"] == carrot[i]:
                complexity += i
                break

        for i in range(len(brown_mushroom)):
            if task_data["brown_mushroom"] == brown_mushroom[i]:
                complexity += i
                break

        for i in range(len(bowl)):
            if task_data["bowl"] == bowl[i]:
                complexity += i
                break

        for i in range(len(coal)):
            if task_data["coal"] == coal[i]:
                complexity += i
                break

        complexity += 6

    score_list = task_data["check_point"].copy()
    score_dict = {}
    for item in score_list:
        score_dict[item["name"]] = {
            "count": item["count"],
            "score": item["score"],
            "success": False,
            "own": False,
            "sub_check_point": item["sub_check_point"]
        }
    del score_list

    own_dict = {}
    """
    基本格式为
    {
        "agent1_name": ["item1", "item2", ...],
        "agent2_name": ["item1", "item2", ...],
    }
    """
    start_time = None
    last_time = None

    max_action_time = complexity * 40
    max_time = complexity * 200
    max_time = complexity * 200

    # metric
    score = 0
    cooperation = 0
    efficiency = 0

    @On(bot, 'spawn')
    def handleViewer(*args):

        for name in agent_names:
            bot.chat(f'/op {name}')
            time.sleep(.2)

        def render_structure(data: dict, x_bias, y_bias, z_bias):
            blocks = data.get("blocks", [])
            for b in blocks:
                # time.sleep(.1)
                x, y, z = b["position"][0] + x_bias, b["position"][1] + y_bias, b["position"][2] + z_bias

                parameter = {}
                for key in b.keys():
                    if key != "position" and key != "name" and key != "items":
                        parameter[key] = b[key]
                if len(parameter) == 0:
                    bot.chat(f'/setblock {x} {y} {z} {b["name"]}')
                else:
                    parameter_str = ""
                    for i, key in enumerate(parameter.keys()):
                        if i != 0:
                            parameter_str += ","
                        parameter_str += f"{key}={parameter[key]}"
                    bot.chat(f'/setblock {x} {y} {z} {b["name"]}[{parameter_str}]')

                if b["name"] == "chest":
                    items = b.get("items", [])
                    next_slot = 0
                    for i, item in enumerate(items):
                        item_name = item["name"]
                        item_count = item["count"]
                        if item_name == "milk_bucket" or item_name == "bucket":
                            for j in range(item_count):
                                bot.chat(
                                    f'/item replace block {x} {y} {z} container.{next_slot} with {item_name}')
                                next_slot += 1
                        else:
                            bot.chat(
                                f'/item replace block {x} {y} {z} container.{next_slot} with {item_name} {item_count}')
                            next_slot += 1

            entities = data.get("entities", [])
            for e in entities:
                time.sleep(.1)
                x, y, z = e["position"][0] + x_bias, e["position"][1] + y_bias, e["position"][2] + z_bias
                bot.chat(f'/summon {e["name"]} {x} {y} {z}')

        def render(data: dict, x_bias, y_bias, z_bias):
            component = data.get("component", [])
            for c in component:
                if c["type"] == "structure":
                    with open("data/farm_blue_print.json", "r") as f:
                        blue_prints = json.load(f)
                    render_structure(blue_prints[c["name"]], x_bias + c["position"][0], y_bias + c["position"][1],
                                     z_bias + c["position"][2])
                elif c["type"] == "block":
                    parameter = {}
                    for key in c.keys():
                        if key != "position" and key != "name" and key != "type" and key != "items":
                            parameter[key] = c[key]
                    if len(parameter) == 0:
                        bot.chat(
                            f'/setblock {x_bias + c["position"][0]} {y_bias + c["position"][1]} {z_bias + c["position"][2]} {c["name"]}')
                    else:
                        parameter_str = ""
                        for i, key in enumerate(parameter.keys()):
                            if i != 0:
                                parameter_str += ","
                            parameter_str += f"{key}={parameter[key]}"
                        bot.chat(
                            f'/setblock {x_bias + c["position"][0]} {y_bias + c["position"][1]} {z_bias + c["position"][2]} {c["name"]}[{parameter_str}]')

                    if c["name"] == "chest":
                        bot.chat(
                            f'/setblock {x_bias + c["position"][0]} {y_bias + c["position"][1]} {z_bias + c["position"][2]} chest')
                        next_slot = 0
                        for i, item in enumerate(c["items"]):
                            item_name = item["name"]
                            item_count = item["count"]
                            if item_name == "milk_bucket" or item_name == "bucket":
                                for j in range(item_count):
                                    bot.chat(
                                        f'/item replace block {x_bias + c["position"][0]} {y_bias + c["position"][1]} {z_bias + c["position"][2]} container.{next_slot} with {item_name}')
                                    next_slot += 1
                            else:
                                bot.chat(
                                    f'/item replace block {x_bias + c["position"][0]} {y_bias + c["position"][1]} {z_bias + c["position"][2]} container.{next_slot} with {item_name} {item_count}')
                                next_slot += 1

        def clear(x_min, y_min, z_min, x_max, y_max, z_max):
            bot.chat(f"/fill {x_min} {y_min} {z_min} {x_max} {y_max} {z_max} air")
            bot.chat(f"/kill @e[type=!player]")
            bot.chat(f"/kill @e[type=item]")

        def generate_recipe_hint(recipes: dict, targets: list, items_in_chest: list):
            def check_recipe(recipe, items_in_chest):
                for item in items_in_chest:
                    if item["name"] == recipe["result"]["name"]:
                        return False
                return True

            recipe_hint = []
            for target in targets:
                for recipe in recipes:
                    if recipe["result"]["name"] == target:
                        recipe_hint.append(recipe)
            recipe_hint = [recipe for recipe in recipe_hint if check_recipe(recipe, items_in_chest)]

            return recipe_hint

        def init():
            global task_data, score_dict, start_time, last_time

            clear(x_b + min_x, y_b + min_y, z_b + min_z, x_b + max_x, y_b + max_y, z_b + max_z)
            bot.chat(f"/fill {x_b + min_x} {y_b + min_y} {z_b + min_z} {x_b + max_x} {y_b + max_y} {z_b + min_z} glass")
            bot.chat(f"/fill {x_b + min_x} {y_b + min_y} {z_b + max_z} {x_b + max_x} {y_b + max_y} {z_b + max_z} glass")
            bot.chat(f"/fill {x_b + min_x} {y_b + min_y} {z_b + min_z} {x_b + min_x} {y_b + max_y} {z_b + max_z} glass")
            bot.chat(f"/fill {x_b + max_x} {y_b + min_y} {z_b + min_z} {x_b + max_x} {y_b + max_y} {z_b + max_z} glass")
            bot.chat(f"/fill {x_b + min_x} -61 {z_b + min_z} {x_b + max_x} -61 {z_b + max_z} grass_block")
            render(task_data, x_b, y_b, z_b)

            bot.chat("/gamemode spectator")
            bot.chat("/gamerule doDaylightCycle false")
            bot.chat("/gamerule doWeatherCycle false")
            bot.chat("/time set day")
            bot.chat("/weather clear")
            bot.chat(f"/tp {bot.username} {x_b} {y_b} {z_b}")
            bot.chat(f"/tp @e[type=minecraft:player, gamemode=survival] {x_b} {y_b} {z_b + 2}")
            bot.chat(f"/clear @e[type=minecraft:player, gamemode=survival]")

            target = []
            for key in score_dict.keys():
                target.append(key)
            with open("data/recipes.json", "r") as f:
                recipes = json.load(f)

            items_in_chest = []
            component = task_data.get("component", [])
            for c in component:
                if c["name"] == "chest":
                    items_in_chest += c.get("items", [])
            recipe_hint = generate_recipe_hint(recipes, target, items_in_chest)
            with open("data/recipe_hint.json", "w") as f:
                json.dump(recipe_hint, f, indent=4)

            bot.chat("task_setting:")
            if "cake" in task_data["name"]:
                bot.chat(f"name: {task_data['name']}")
                bot.chat(f"milk: {task_data['milk']}")
                bot.chat(f"wheat: {task_data['wheat']}")
                bot.chat(f"sugar: {task_data['sugar']}")
            elif "rabbit_stew" in task_data["name"]:
                bot.chat(f"name: {task_data['name']}")
                bot.chat(f"cooked_rabbit: {task_data['cooked_rabbit']}")
                bot.chat(f"baked_potato: {task_data['baked_potato']}")
                bot.chat(f"carrot: {task_data['carrot']}")
                bot.chat(f"brown_mushroom: {task_data['brown_mushroom']}")
                bot.chat(f"bowl: {task_data['bowl']}")
                bot.chat(f"coal: {task_data['coal']}")

            time.sleep(1)

            start_time = time.time()
            last_time = start_time

            with open(".cache/load_status.cache", "w") as f:
                json.dump({"status": "loaded"}, f, indent=4)

        t = threading.Thread(target=init, args=())
        t.start()


    @On(bot, 'time')
    def handleTime(*args):
        def calculate_balance():
            # 计算每个agent的时间
            if not os.path.exists('data/action_log.json'):
                return
            with open('data/action_log.json', 'r') as f:
                data = json.load(f)
            agent_time = []
            for action_name, actions in data.items():
                total_time = 0
                for action in actions:
                    total_time += action.get('duration', 0)
                agent_time.append(total_time)
            for i in range(agent_num - len(agent_time)):
                agent_time.append(0)
            time_array = np.array(agent_time)
            
            # 对时间进行归一化处理
            time_array = (time_array) / (np.max(time_array) + 1e-8)
            
            # 计算并返回 Balanced Agent Utilization Score (BAUS)
            return 1 - np.std(time_array)

        def calculate_action_time():
            if not os.path.exists('data/action_log.json'):
                return 0
            with open('data/action_log.json', 'r') as f:
                data = json.load(f)
            time_list = []
            for name, actions in data.items():
                for action in actions:
                    start = time.mktime(time.strptime(action['start_time'], "%Y-%m-%d %H:%M:%S"))
                    end = time.mktime(time.strptime(action['end_time'], "%Y-%m-%d %H:%M:%S"))
                    time_list.append((start, end))
            if len(time_list) == 0:
                return 0

            # 计算覆盖的总时间
            total_time = 0  # 单位：秒
            time_list.sort(key=lambda x: x[0])  # 按照开始时间排序
            start, end = time_list[0]
            for i in range(1, len(time_list)):
                if time_list[i][0] < end:
                    end = max(end, time_list[i][1])
                else:
                    total_time += end - start
                    start, end = time_list[i]
            total_time += end - start

            return total_time

        def get_player_name():
            global task_data

            name_list = []
            entities = bot.entities
            for key in entities:
                type = entities[key].type
                if type == "player" and entities[key].username != bot.username:
                    x = entities[key].position.x
                    y = entities[key].position.y
                    z = entities[key].position.z
                    if x_b + min_x <= x <= x_b + max_x and y_b + min_y <= y <= y_b + max_y and z_b + min_z <= z <= z_b + max_z:
                        name_list.append(entities[key].username)
            return name_list

        global start_time, last_time, own_dict
        if start_time is not None:
            global score, cooperation, efficiency
            now_time = time.time()

            if now_time - last_time > 1:
                with open(".cache/heart_beat.cache", "w") as f:
                    json.dump({"time": now_time}, f, indent=4)
                if score == 100:
                    efficiency = max_action_time / calculate_action_time()
                    # 给出结束信号和写入文件
                    if not os.path.exists(os.path.join("result", task_name)):
                        os.mkdir(os.path.join("result", task_name))
                    else:
                        shutil.rmtree(os.path.join("result", task_name))
                        os.mkdir(os.path.join("result", task_name))
                    with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                        json.dump({
                            "score": score,
                            "cooperation": cooperation,
                            "efficiency": efficiency,
                            "balance": calculate_balance(),
                            "use_time": calculate_action_time(),
                            "end_reason": "complete task",
                            "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
                        }, f, indent=4)
                    with open(".cache/load_status.cache", "w") as f:
                        json.dump({"status": "end"}, f, indent=4)

                if calculate_action_time() > max_action_time:
                    efficiency = 1
                    if not os.path.exists(os.path.join("result", task_name)):
                        os.mkdir(os.path.join("result", task_name))
                    else:
                        shutil.rmtree(os.path.join("result", task_name))
                        os.mkdir(os.path.join("result", task_name))
                    with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                        json.dump({
                            "score": score,
                            "cooperation": cooperation,
                            "efficiency": efficiency,
                            "balance": calculate_balance(),
                            "use_time": calculate_action_time(),
                            "end_reason": "action time out",
                            "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
                        }, f, indent=4)
                    with open(".cache/load_status.cache", "w") as f:
                        json.dump({"status": "end"}, f, indent=4)

                if now_time - start_time > max_time:
                    action_time = calculate_action_time()
                    if action_time == 0:
                        efficiency = 1
                    else:
                        efficiency = max_action_time / action_time
                    if not os.path.exists(os.path.join("result", task_name)):
                        os.mkdir(os.path.join("result", task_name))
                    else:
                        shutil.rmtree(os.path.join("result", task_name))
                        os.mkdir(os.path.join("result", task_name))
                    with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                        json.dump({
                            "score": score,
                            "cooperation": cooperation,
                            "efficiency": efficiency,
                            "balance": calculate_balance(),
                            "use_time": calculate_action_time(),
                            "end_reason": "max time out",
                            "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
                        }, f, indent=4)
                    with open(".cache/load_status.cache", "w") as f:
                        json.dump({"status": "end"}, f, indent=4)

                

            if now_time - last_time > 5:
                name_list = get_player_name()
                for name in name_list:
                    bot.chat(f"/data get entity {name}")
                    if name not in own_dict.keys():
                        own_dict[name] = []
                last_time = now_time


    @On(bot, 'messagestr')
    def handleChat(_, message, messagePosition, jsonMsg, sender, *args):
        def calculate_score(agent_name: str, inventory: list):
            global score_dict, own_dict
            # 合并同类物品
            for i, item in enumerate(inventory):
                for j in range(i + 1, len(inventory)):
                    if item["name"] == inventory[j]["name"]:
                        item["count"] += inventory[j]["count"]
                        inventory[j]["count"] = 0
            inventory = [item for item in inventory if item["count"] > 0]

            for item in inventory:
                name = item["name"]
                count = item["count"]

                # 达成条件时，标记success
                if name in score_dict.keys() and count >= score_dict[name]["count"]:
                    score_dict[name]["success"] = True

                # 第一次拥有时，加入own_dict
                if name in score_dict.keys() and not score_dict[name]["own"]:
                    score_dict[name]["own"] = True
                    own_dict[agent_name].append(name)

            # 计算score
            add_list = []
            for name in score_dict.keys():
                if score_dict[name]["success"]:
                    add_list.append((name, True))
            for name, valid in add_list:
                sub_check_point = score_dict[name]["sub_check_point"]
                while len(sub_check_point) > 0:
                    new_sub_check_point = []
                    for sub_name in sub_check_point:
                        for i in range(len(add_list)):
                            check_name, _ = add_list[i]
                            if check_name == sub_name:
                                add_list[i] = (check_name, False)
                                break
                        new_sub_check_point += score_dict[sub_name]["sub_check_point"]
                    sub_check_point = new_sub_check_point

            score = 0
            for name, valid in add_list:
                if valid:
                    score += score_dict[name]["score"]

            # 计算合作度
            own = np.array([len(own_dict[name]) for name in own_dict.keys()])
            count = np.sum(own)
            if count == 0:
                cooperation = 0
            else:
                std = np.std(own)
                # 计算最大的标准差，即当一个人拥有所有物品时，标准差最大
                only_one_own = np.zeros_like(own)
                only_one_own[0] = count
                max_std = np.std(only_one_own)
                # 计算最小的标准差，即当所有人拥有相同数量的物品时或相差不超过1时，标准差最小
                average_own = np.zeros_like(own) + count // len(own)
                average_own[:count % len(own)] += 1
                min_std = np.std(average_own)

                if max_std == min_std:  # 防止除0
                    cooperation = 100
                else:
                    cooperation = 100 * (1 - (std - min_std) / (max_std - min_std))

            return score, cooperation

        global start_time, score, cooperation
        if start_time is not None:
            pattern = "(.*) has the following entity data: (.*)"
            match = re.search(pattern, message)
            if match:
                agent_name = match.group(1)
                data_str = match.group(2)
            else:
                agent_name = None
                data_str = None

            if agent_name is not None and data_str is not None:
                # 修复json字符串中的缺失的双引号，有小bug，但是不影响需要的字段
                splits = re.split(r'[\[\]{}]|,\s|:\s', data_str)
                replace_dicts = []
                for split in splits:
                    if split != "":
                        if split.startswith("'") and split.endswith("'"):
                            replace_dicts.append((split, f'{split[1:-1]}'))
                        elif not ((split.startswith('"')) and split.endswith('"')):
                            replace_dicts.append((split, f'"{split}"'))
                start = 0
                for replace_dict in replace_dicts:
                    while True:
                        pos = data_str.find(replace_dict[0], start)
                        if pos == -1:
                            break  # 其实不会发生
                        else:
                            if pos > 0 and data_str[pos - 1] == '"':
                                start = pos + 1
                                continue
                            if pos < len(data_str) - 1 and data_str[pos + 1] == '"':
                                start = pos + 1
                                continue
                            data_str = data_str[:pos] + replace_dict[1] + data_str[pos + len(replace_dict[0]):]
                            start = pos + len(replace_dict[1])
                            break

                data = json.loads(data_str)

                inventory = data.get("Inventory", [])
                for i, item in enumerate(inventory):
                    count = item.get("Count", 0)
                    # 最后一个不是字母
                    if count[-1].isalpha():
                        count = int(count[:-1])
                    else:
                        count = int(count)

                    name = item.get("id", "")
                    pattern = "minecraft:(.*)"
                    match = re.search(pattern, name)
                    if match:
                        name = match.group(1)
                    else:
                        name = None

                    if name is not None:
                        inventory[i] = {"name": name, "count": count}

                score, cooperation = calculate_score(agent_name, inventory)
                bot.chat(f"score: {score}")
                bot.chat(f"cooperation: {cooperation}")
