# 这个judger需要根据json文件加载一个地形，将Agent初始化到指定位置
# 根据Agent的状态，环境的更新，结合json文件，给出累计得分
# optional 可能需要根据Agent的状态，judger更新环境
import shutil
import threading
from utils import *
import json
import os
import argparse
from minecraft_define import *
from env_api import *
import random

parser = argparse.ArgumentParser()
parser.add_argument('--idx', type=int, default=0, help='the index of the escape test to be judged')
parser.add_argument('--max_task_num', type=int, default=1, help='how many tasks in the test')
parser.add_argument('--agent_num', type=int, default=1, help='how many agents in the test')
parser.add_argument('--mc_version', type=str, default="1.19.2", help='the version of minecraft')
parser.add_argument('--host', type=str, default="10.21.31.18", help='the host of the server')
parser.add_argument("--port", type=int, default=25565, help="the port of the server")
parser.add_argument("--agent_names", type=str, default="", help="the name of the agents in A,B,C format")
parser.add_argument("--task_name", type=str, default="test", help="the name of the task")

args = parser.parse_args()
select_idx = args.idx
agent_num = args.agent_num
max_task_num = args.max_task_num
agent_names = args.agent_names.split(",")
task_name = args.task_name

mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
collectBlock = require('mineflayer-collectblock')
pvp = require("mineflayer-pvp").plugin
minecraftHawkEye = require("minecrafthawkeye")
Vec3 = require("vec3")
Socks = require("socks5-client")
minecraftData = require('minecraft-data')
mcData = minecraftData(args.mc_version)

y_b = -60  # -60
bot = mineflayer.createBot({
    "host": args.host,
    "port": args.port,
    'username': "meta_judger",
    'checkTimeoutInterval': 600000,
    'auth': 'offline',
    'version': "1.19.2",
})
bot.loadPlugin(pathfinder.pathfinder)
bot.loadPlugin(collectBlock.plugin)
bot.loadPlugin(pvp)
bot.loadPlugin(minecraftHawkEye)

### reset the environments
with open("data/score.json", "w") as f:
    json.dump({}, f, indent=4)

with open(".cache/env.cache", "w") as f:
    json.dump([], f, indent=4)

with open(".cache/load_status.cache", "w") as f:
    json.dump({"status": "loading"}, f, indent=4)

if not os.path.exists("result"):
    os.makedirs("result")

last_time = time.time()
start_time = None

max_action_time = 60
max_time = 300
info_count = 0
config = {}
agent_name = agent_names[0] if len(agent_names) > 0 else "Alice"
# metrics

score = 0

complexity_score = 0
efficiency = 0
balance = 0

def aligned_item_name(item): #去掉可能的物品名前缀
    if item.startswith("minecraft:"):
        aligned_goal_item = item[len("minecraft:"):]
        return aligned_goal_item
    else:
        return item

@On(bot, 'spawn')
def handleViewer(*args):

    def random_position(x1, y1, z1, x2, y2, z2):
        randx = random.randint(x1, x2)
        randy = random.randint(y1, y2)
        randz = random.randint(z1, z2)
        return randx, randy, randz
    
    def generate_recipe_hint(goal_item):
        recipe_hint = []
        with open("data/recipes.json", "r") as f:
            recipes = json.load(f)
            for recipe in recipes:
                if recipe["result"]["name"] == goal_item:
                    recipe_hint.append(recipe)
        with open("data/recipe_hint.json", "w") as f:
            json.dump(recipe_hint, f, indent=4)

    for name in agent_names:
        bot.chat(f'/op {name}')
        time.sleep(.2) 

    room_width = 15
    room_height = 15
    wall_width = 1

    orx = 0     #origin_point
    ory = -61
    orz = 0

    bot.chat("/gamemode spectator")
    time.sleep(.5)
    bot.chat("/gamerule doDaylightCycle false")
    time.sleep(.5)
    bot.chat("/gamerule doWeatherCycle false")
    time.sleep(.5)
    bot.chat("/time set day")
    time.sleep(.5)
    bot.chat("/weather clear")
    time.sleep(.5)
    bot.chat(f"/tp @s {orx + room_width//2 + 1} {ory + 1} {orz + wall_width} 0 0")
    time.sleep(.5)
    bot.chat("/clear @e[distance=..10,type=player,gamemode=survival]")
    time.sleep(.5)
    bot.chat("/kill @e[type=!minecraft:player]")
    time.sleep(.5)
    bot.chat("/kill @e[type=!minecraft:player]")
    time.sleep(.5)

    bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + wall_width} {ory + room_height + wall_width} {orz + room_width + wall_width} glass hollow")
    time.sleep(.5)
    bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + wall_width} {ory} {orz + room_width + wall_width} grass_block")
    time.sleep(.5)
    # 生成一个内部空间width*width*height，五面玻璃一面草方块的封闭空间
    global config

    with open(".cache/meta_setting.json", "r") as f:
        config = json.load(f)
    
    material_positon = 1 # 东西放在什么地方，0在箱子，1在身上

    if config["task_scenario"] == "dig":
        # randx, randy, randz = random_position(orx + wall_width, ory + 1, orz + wall_width, orx + wall_width + room_width - 1, ory + 3, orz + wall_width + room_width - 1)
        block = aligned_item_name(config["evaluation_item"])
        pos_list = config["evaluation_place"]
        bot.chat(f"/setblock {pos_list[0]} {pos_list[1]} {pos_list[2]} {block}")
    elif config["task_scenario"] == "craft":
        goal_item = aligned_item_name(config["evaluation_item"])
        generate_recipe_hint(goal_item)

        chest_x, chest_y, chest_z = random_position(orx + wall_width, ory + 1, orz + wall_width, orx + wall_width + room_width - 1, ory + 3, orz + wall_width + room_width - 1)
        craft_x, craft_y, craft_z = random_position(orx + wall_width, ory + 1, orz + wall_width, orx + wall_width + room_width - 1, ory + 3, orz + wall_width + room_width - 1)
        while chest_x == craft_x and chest_z == craft_z and (chest_y == craft_y or chest_y == craft_y-1):
            craft_x, craft_y, craft_z = random_position(orx + wall_width, ory + 1, orz + wall_width, orx + wall_width + room_width - 1, ory + 3, orz + wall_width + room_width - 1)
        
        if material_positon == 0: # 材料在随机位置的箱子里
            ingredients_str = "{Items:["

            with open("data/recipes.json", "r") as f:
                recipes = json.load(f)
                for item in recipes:
                    if item["result"]["name"] == goal_item:
                        for i, ingredients in enumerate(item["ingredients"]):
                            if i > 0:
                                ingredients_str += ","
                            ingredients_str += "{Slot:" + str(i) + ",id:" + ingredients["name"] + ",Count:" + str(ingredients["count"]) + "}"
                        break
            ingredients_str += "]}"

            bot.chat(f"/setblock {chest_x} {chest_y} {chest_z} chest{ingredients_str}")
        elif material_positon == 1: # 材料在Agent身上
            with open("data/recipes.json", "r") as f:
                recipes = json.load(f)
                for item in recipes:
                    if item["result"]["name"] == goal_item:
                        for ingredients in item["ingredients"]:
                            bot.chat(f"/give {agent_name} {ingredients['name']} {ingredients['count']}")
                        break
        else:
            bot.chat("/tellraw @a {\"text\":\"INVALID MATERIAL POSITION!\", \"color\":\"red\"}")

        bot.chat(f"/setblock {craft_x} {craft_y} {craft_z} crafting_table")
    elif config["task_scenario"] == "place":
        goal_item = aligned_item_name(config["evaluation_item"])
        bot.chat(f"/give {agent_name} {goal_item} 1")
    else:
        bot.chat("/tellraw @a {\"text\":\"INVALID SCENARIO!\", \"color\":\"red\"}")


    bot.chat(f"/tp @e[gamemode=survival] {orx + room_width // 2 + 1} {ory + 4} {orz + 2} 0 0")

    global max_action_time, max_time
    
    with open(".cache/load_status.cache", "w") as f:
        json.dump({"status": "loaded"}, f, indent=4)
    
    global start_time
    start_time = time.time()
    

@On(bot, "time")
def handle(this):
    def calculate_balance():
        # 计算每个agent的时间
        if not os.path.exists('data/action_log.json'):
            return 0
        with open('data/action_log.json', 'r') as f:
            data = json.load(f)
        agent_time = []
        for name, actions in data.items():
            total_time = 0
            for action in actions:
                total_time += action['duration']
            agent_time.append(total_time)
        for i in range(agent_num - len(agent_time)):
            agent_time.append(0)
        time_array = np.array(agent_time)
        
        # 对时间进行归一化处理
        time_array = (time_array - np.min(time_array)) / (np.max(time_array) - np.min(time_array) + 1e-8)
        
        # 计算并返回 Balanced Agent Utilization Score (BAUS)
        return 1 - np.sqrt(np.sum((time_array - np.mean(time_array))**2)) / (len(time_array) * np.mean(time_array) + 1e-8)

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

    def check_block(pos_list, goal_item):
        Block = bot.blockAt(Vec3(pos_list[0], pos_list[1], pos_list[2]))
        if aligned_item_name(Block["name"]) == "air" or aligned_item_name(Block["name"]) == "water" or aligned_item_name(Block["name"]) == "lava":
            return False
        if aligned_item_name(Block["name"]) == goal_item:
            if len(pos_list) > 3:
                facing = pos_list[3]
                if Block._properties["facing"] and facing in ["W", "E", "S", "N"]:
                    if Block._properties["facing"] == "east" and facing == "E":
                        return True
                    if Block._properties["facing"] == "west" and facing == "W":
                        return True
                    if Block._properties["facing"] == "south" and facing == "S":
                        return True
                    if Block._properties["facing"] == "north" and facing == "N":
                        return True
                if Block._properties["axis"] and facing in ["x", "y", "z"]:
                    if Block._properties["axis"] == "x" and facing == "x":
                        return True
                    if Block._properties["axis"] == "y" and facing == "y":
                        return True
                    if Block._properties["axis"] == "z" and facing == "z":
                        return True
                return False
            else:
                return True

    global last_time, start_time, score
    if start_time is not None:
        global complexity_score, efficiency, balance, config, info_count
        now_time = time.time()

        # bot.chat(f'now_time = {now_time}    last_time = {last_time}')

        if now_time - last_time > 1:
            if config["task_scenario"] == "craft":
                bot.chat(f'/data get entity {agent_name}')
            elif config["task_scenario"] == "dig":
                goal_item = aligned_item_name(config["evaluation_item"])
                pos_list = config["evaluation_place"]
                Block = bot.blockAt(Vec3(pos_list[0], pos_list[1], pos_list[2]))
                if now_time - start_time  > 10 and aligned_item_name(Block["name"]) != goal_item:
                    score = 100
                info_count += 1
                if info_count % 20 == 0:
                    bot.chat(f'score: {score}')
            elif config["task_scenario"]  == "place":
                goal_item = aligned_item_name(config["evaluation_item"])
                pos_list = config["evaluation_place"]
                if check_block(pos_list, goal_item):
                    score = 100
                info_count += 1
                if info_count % 20 == 0:
                    bot.chat(f'score: {score}')
            if score == 100:
                if not os.path.exists("result" + task_name):
                    os.mkdir(os.path.join("result/", task_name))
                with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                    json.dump({
                        "score": score,
                        "use_time": calculate_action_time(),
                        "end_reason": "task completed",
                        "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
                    }, f, indent=4)
                with open(".cache/load_status.cache", "w") as f:
                    json.dump({"status": "end"}, f, indent=4)
            if calculate_action_time() > max_action_time:
                efficiency = 1
                # 给出结束信号和写入文件
                if not os.path.exists("result" + task_name):
                    os.mkdir(os.path.join("result/", task_name))
                with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                    json.dump({
                        "complexity_score": complexity_score,
                        "efficiency": efficiency,
                        "balance": balance,
                        "use_time": calculate_action_time(),
                        "end_reason": "action_time out",
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
                # 给出结束信号和写入文件
                if not os.path.exists("result/" + task_name):
                    os.mkdir(os.path.join("result", task_name))
                with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                    json.dump({
                        "complexity_score": complexity_score,
                        "efficiency": efficiency,
                        "balance": balance,
                        "use_time": calculate_action_time(),
                        "end_reason": "max time out",
                        "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
                    }, f, indent=4)
                with open(".cache/load_status.cache", "w") as f:
                    json.dump({"status": "end"}, f, indent=4)

            last_time = now_time

@On(bot, 'messagestr')
def handleChat(_, message, messagePosition, jsonMsg, sender, *args):
    global score, info_count, config
    def calculate_score(inventory, message):
        if config["task_scenario"] == "craft":
            goal_item = aligned_item_name(config["evaluation_item"])
            for item in inventory:
                if aligned_item_name(item['id']) == goal_item:
                    return 100
            return 0
        else:   
            return 0
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
            # cache_dir = 'tmp'
            # file_path = os.path.join(cache_dir, 'message.json')
            # if not os.path.exists(cache_dir):
            #     os.makedirs(cache_dir)
        
            # # 初始化消息列表
            # messages = []
            
            # # 如果文件存在，读取已有内容
            # if os.path.exists(file_path):
            #     with open(file_path, 'r', encoding='utf-8') as f:
            #         try:
            #             messages = json.load(f)
            #         except json.JSONDecodeError:
            #             # 文件可能为空或格式不正确，忽略读取错误
            #             pass
            
            # # 添加新消息到消息列表
            # messages.append(data)
            
            # # 将消息列表写回文件
            # with open(file_path, 'w', encoding='utf-8') as f:
            #     json.dump(messages, f, ensure_ascii=False, indent=4)
            inventory = data.get("Inventory", [])
            score = calculate_score(inventory, message)
            info_count += 1
            if info_count % 20 == 0:
                bot.chat(f'score: {score}')

