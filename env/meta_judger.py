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
import platform

system_type = platform.system().lower()

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
if system_type == 'linux':
    minecraftHawkEye = require("minecrafthawkeye").default
else:
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

environment_set_time = 10
info_count = 0
interact_type = "block"
interact_arg = 0
arg_host = args.host
arg_port = args.port
# evaluation_arg 
# dig    : target, x, y, z, tool
# craft  : target, item_position, step
# place  : target, x, y, z, item_position, facing
# useitem: target, item_position, action
# move   : x, y, z
# interact(entity): target, tool, action
# interact(block) : target, action, (other args)

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

    for name in agent_names:
        bot.chat(f'/op {name}')
        time.sleep(.2) 

    room_width = 25
    room_height = 15
    wall_width = 1

    orx = 0     #origin_point
    ory = -61
    orz = 0

    def generate_hill(start_x, start_z, height):
        height_vis = [[-1 for _ in range(room_width + 1)] for _ in range(room_width + 1)]
        neighbor_list = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        height_vis[start_x][start_z] = height
        queue = deque([(start_x, start_z, height)])
        while queue:
            x, z, current_height = queue.popleft()

            if current_height > 1:
                bot.chat(f"/fill {x} {ory + 1} {z} {x} {ory + current_height - 1} {z} dirt")
                time.sleep(.1)
            bot.chat(f"/setblock {x} {ory + current_height} {z} grass_block")
            time.sleep(.1)
            random.shuffle(neighbor_list)
            for dx, dz in neighbor_list:
                nx, nz = x + dx, z + dz
                if nx <= orx or nx > orx + room_width or nz <= orz or nz > orz + room_width:
                    continue
                if height_vis[nx][nz] == -1:
                    neighbor_count, neighbor_height = 0, 0
                    for dx2, dz2 in neighbor_list:  # 避免出现坑洼的地形
                        nnx, nnz = nx + dx2, nz + dz2
                        if nnx <= orx or nnx > orx + room_width or nnz <= orz or nnz > orz + room_width:
                          continue
                        if height_vis[nnx][nnz] != -1:
                            neighbor_count += 1
                            neighbor_height += height_vis[nnx][nnz]
                    if neighbor_count >= 3:
                        next_height = round(neighbor_height / neighbor_count)
                    else:
                        if current_height > 1:
                            next_height = current_height + random.choices([-1, 0], weights=[58, 42])[0] #-1的权重越大，越陡峭，但是-1的权重不宜太小
                        else:
                            next_height = current_height + random.choices([-1, 0], weights=[75, 25])[0]
                    if next_height == 0:
                        continue
                    height_vis[nx][nz] = next_height
                    queue.append((nx, nz, next_height))
    
    def get_surface_y(x, z):
        y = ory + 1
        flag = False
        while y <= ory + room_height:
            block = bot.blockAt(Vec3(x, y, z))
            if block:
                if block["name"] == "air":
                    if flag:
                        return y - 1
                    else:
                        flag = True # 至少连续两格为空气才认为是surface
                else:
                    flag = False
            else:
                bot.chat("/tellraw @a {\"text\":\"UNLOADED POSITION!\", \"color\":\"red\"}")
                bot.chat(f"{x} {y} {z}")
                return None
            y = y + 1
            
        return ory + 1
    
    def random_position(x1, z1, x2, z2, y_range, invalid_pos = []):
        randx = random.randint(x1, x2)
        randz = random.randint(z1, z2)
        while True:
            cover = False
            for pos in invalid_pos:
                if abs(pos[0] - randx) <= 2 and abs(pos[2] - randz) <= 2:
                    cover = True
                    break
            if cover:
                randx = random.randint(x1, x2)
                randz = random.randint(z1, z2)
            else:
                break
        sur_y = get_surface_y(randx, randz)
        randy = sur_y + random.randint(1 , y_range) - 1
        return randx, randy, randz
    
    def generate_recipe_hint(goal_item):
        recipe_hint = []
        with open("data/recipes.json", "r") as f:
            recipes = json.load(f)
            for recipe in recipes:
                if recipe["result"]["name"] in goal_item:
                    recipe_hint.append(recipe)
        with open("data/recipe_hint.json", "w") as f:
            json.dump(recipe_hint, f, indent=4)        

    def set_chest(invalid_position, items):
        chest_x, chest_y, chest_z= random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1)
        while ((chest_x, chest_y, chest_z) in invalid_position) or ((chest_x, chest_y+1, chest_z) in invalid_position) or chest_y > ory + 4:
            chest_x, chest_y, chest_z= random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1)
        item_str = "{Items:["
        for i, item in enumerate(items):
            if i > 0:
                item_str += ","
            item_str += "{Slot:" + str(i) + ",id:" + item["name"] + ",Count:" + str(item["count"]) + "}"
        item_str += "]}"
        bot.chat(f"/setblock {chest_x} {chest_y} {chest_z} chest{item_str}")
    
    bot.chat("/gamemode spectator")
    time.sleep(.2)
    bot.chat("/gamerule doDaylightCycle false")
    time.sleep(.2)
    bot.chat("/gamerule doWeatherCycle false")
    time.sleep(.2)
    bot.chat("/time set day")
    time.sleep(.2)
    bot.chat("/weather clear")
    time.sleep(.2)
    
    # bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + wall_width} {ory + room_height + wall_width} {orz + room_width + wall_width} glass hollow")
    # time.sleep(.2)
    # bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + wall_width} {ory} {orz + room_width + wall_width} grass_block")
    # time.sleep(.2)
    # bot.chat(f"/setblock {orx + wall_width} {ory + room_height // 2 - 1} {orz + wall_width} glass")
    # time.sleep(.2)
    # bot.chat(f"/tp @s {orx + wall_width} {ory + room_height // 2} {orz + wall_width} -45 45")
    
    # peakx, peakz = random.randint(orx + wall_width, orx + room_width + wall_width - 1), random.randint(orz + wall_width, orx + room_width + wall_width - 1)
    # hill_height = 3
    # bot.chat(f"/tp @e[gamemode=survival] {orx + room_width + 100} {ory + 4} {orz + room_width + 100} 0 0") #tp走防止在生成的地形里窒息
    # generate_hill(peakx, peakz, hill_height)

    # bot.chat(f"/tp {agent_name} {orx - 10} {ory + 4} {orz - 10} 0 0") #tp走防止在生成的地形里窒息
    time.sleep(.2)

    with open(".cache/meta_setting.json", "r") as f:
        config = json.load(f)
    arg_dict = config["evaluation_arg"]

    clear_w = 31
    clear_h = 6
    feature_list = ["desert", "plains", "savanna", "snowy", "taiga"]
    tree_list = ["acacia", "birch", "spruce", "oak", "jungle_tree", "dark_oak", "mangrove"]
    tree_weight = [5, 30, 5, 50, 4, 3, 3]
    invalid_pos = []
    if config["task_scenario"] in ["dig", "place", "move"] or (config["task_scenario"] == "useitem" and "sign" in arg_dict["target"]) or (config["task_scenario"] == "interact" and arg_dict["action"] == "store"):
        invalid_pos.append((arg_dict['x'], arg_dict['y'], arg_dict['z']))
    
    crx, cry, crz = random_position(orx + wall_width + 3, orz + wall_width + 3, orx + room_width + wall_width - 3, orz + room_width + wall_width - 3, 1, invalid_pos)
    # 建筑位置
    tx, ty, tz = random_position(orx + wall_width + 3, orz + wall_width + 3, orx + room_width + wall_width - 3, orz + room_width + wall_width - 3, 1, invalid_pos)
    # 树位置

    for i in range(4):
        bot.chat(f"/fill {orx + wall_width + room_width // 2 - clear_w} {ory + clear_h * i + 1} {orz + wall_width + room_width // 2 - clear_w} {orx + wall_width + room_width // 2 + clear_w} {ory + clear_h * (i+1) + 1} {orz + wall_width + room_width // 2 + clear_w} air")
        time.sleep(.2)

    # bot.chat(f"/fill {orx + wall_width + room_width // 2 - clear_w} {ory + 1} {orz + wall_width + room_width // 2 - clear_w} {orx + wall_width + room_width // 2 + clear_w} {ory + clear_h + 1} {orz + wall_width + room_width // 2 + clear_w} air")
    # time.sleep(.2)
    # bot.chat(f"/fill {orx + wall_width + room_width // 2 - clear_w} {ory + clear_h + 2} {orz + wall_width + room_width // 2 - clear_w} {orx + wall_width + room_width // 2 + clear_w} {ory + clear_h * 2 + 1} {orz + wall_width + room_width // 2 + clear_w} air")
    # time.sleep(.2)
    # bot.chat(f"/fill {orx + wall_width + room_width // 2 - clear_w} {ory + clear_h * 2 + 2} {orz + wall_width + room_width // 2 - clear_w} {orx + wall_width + room_width // 2 + clear_w} {ory + clear_h * 3 + 1} {orz + wall_width + room_width // 2 + clear_w} air")
    # time.sleep(.2)
    # bot.chat(f"/fill {orx + wall_width + room_width // 2 - clear_w} {ory + clear_h * 3 + 2} {orz + wall_width + room_width // 2 - clear_w} {orx + wall_width + room_width // 2 + clear_w} {ory + clear_h * 4 + 1} {orz + wall_width + room_width // 2 + clear_w} air")
    # time.sleep(.2)
    # bot.chat("/kill @e[type=!minecraft:player]")
    # time.sleep(.2)
    # 清空原来的环境

    # peakx, peakz = random.randint(orx + wall_width, orx + room_width + wall_width - 1), random.randint(orz + wall_width, orx + room_width + wall_width - 1)
    # hill_height = 3
    # generate_hill(peakx, peakz, hill_height)
    # 生成土丘

    feature = random.choice(feature_list)
    with open("data/template_houses.json", "r") as f:
        template_houses = json.load(f)
    house = random.choice(template_houses[feature])
    bot.chat(f"/tp {crx} {ory + 1} {crz}")
    time.sleep(.2) 
    bot.chat(f"/place template village/{feature}/houses/{house}")
    time.sleep(.2)
    bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + wall_width} {ory + room_height + wall_width} {orz + room_width + wall_width} air replace jigsaw")
    time.sleep(.2)
    bot.chat(f"/tp {tx} {get_surface_y(tx, tz)} {tz}")
    time.sleep(.2)
    bot.chat(f"/place feature {random.choices(tree_list, tree_weight)[0]}")
    time.sleep(.2)
    # 生成房屋和树

    bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + wall_width} {ory + room_height + wall_width} {orz} glass")
    time.sleep(.2)
    bot.chat(f"/fill {orx} {ory} {orz} {orx} {ory + room_height + wall_width} {orz + room_width + wall_width} glass")
    time.sleep(.2)
    bot.chat(f"/fill {orx + room_width + wall_width} {ory} {orz} {orx + room_width + wall_width} {ory + room_height + wall_width} {orz + room_width + wall_width} glass")
    time.sleep(.2)
    bot.chat(f"/fill {orx} {ory} {orz + room_width + wall_width} {orx + room_width + wall_width} {ory + room_height + wall_width} {orz + room_width + wall_width} glass")
    time.sleep(.2)
    bot.chat(f"/fill {orx} {ory + room_height + wall_width} {orz} {orx + room_width + wall_width} {ory + room_height + wall_width} {orz + room_width + wall_width} glass")
    time.sleep(.2)
    bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + wall_width} {ory} {orz + room_width + wall_width} grass_block")
    time.sleep(.2)
    # 生成一个内部空间width*width*height，五面玻璃一面草方块的封闭空间
    
    bot.chat("/clear @e[distance=..10,type=player,gamemode=survival]")
    time.sleep(.2)
    bot.chat("/kill @e[type=!minecraft:player]")
    time.sleep(.2)
    bot.chat("/kill @e[type=!minecraft:player]")
    time.sleep(.2)

    bot.chat(f"/setblock {orx + wall_width} {ory + room_height // 2 - 1} {orz + wall_width} glass")
    time.sleep(.2)
    bot.chat(f"/tp @s {orx + wall_width} {ory + room_height // 2} {orz + wall_width} -45 45")
    time.sleep(.2)

    sur_y = get_surface_y(orx + room_width // 2 + 1, orz + 4)
    bot.chat(f"/tp {agent_name} {orx + room_width // 2 + 1} {sur_y} {orz + 4} 0 0")
    time.sleep(.2)
    bot.chat(f"/gamemode survival {agent_name}")
    time.sleep(.2)

    global interact_arg, interact_type
    
    bot.chat(f"/give {agent_name} dirt 15")
    time.sleep(.2)

    if config["task_scenario"] == "dig":
        if arg_dict["tool"]:
            if arg_dict["item_position"] == "chest":
                set_chest([(arg_dict['x'], arg_dict['y'], arg_dict['z'])], [{"name": arg_dict["tool"], "count": 1}])
            elif arg_dict["item_position"] == "inventory":
                bot.chat(f"/give {agent_name} {arg_dict['tool']} 1")
            else:
                bot.chat("/tellraw @a {\"text\":\"INVALID ITEM POSITION!\", \"color\":\"red\"}") 
            time.sleep(.2)
        block = aligned_item_name(arg_dict["target"])
        bot.chat(f"/setblock {arg_dict['x']} {arg_dict['y']} {arg_dict['z']} {block}")

    elif config["task_scenario"] == "craft":
        goal_item = aligned_item_name(arg_dict["target"])
        ingredients_list = []
        with open("data/recipes.json", "r") as f:
            recipes = json.load(f)
            for item in recipes:
                if item["result"]["name"] == goal_item:
                    for ingredients in item["ingredients"]:
                        ingredients_list.append(ingredients)
                    break
            random.shuffle(ingredients_list)
           
            if arg_dict["step"] == 2: # 两步合成长度        
                    rm_flag, rm_ingredient = False, {}
                    for ingredients in ingredients_list:
                        if rm_flag:
                            break
                        for item in recipes:
                            if item["result"]["name"] == ingredients["name"]: #找到第一个可以合成的材料
                                ing_flag = True
                                for ing2 in item["ingredients"]:
                                    if ing2["name"] == goal_item:  #这个材料的配料中不应该有目标物品，防止出现互相合成时直接获得goal_item
                                        ing_flag = False
                                        break
                                if ing_flag:
                                    rm_ingredient = ingredients
                                    rm_flag = True
                                    for ing2 in item["ingredients"]:
                                        ingredients_list.append({"name": ing2["name"], "count": ing2["count"] * ingredients["count"]})
                                    break
                    if rm_flag:
                        ingredients_list.remove(rm_ingredient)
                        generate_recipe_hint([goal_item, rm_ingredient["name"]])
                    else:
                        generate_recipe_hint([goal_item])
            else:
                generate_recipe_hint([goal_item])
        craft_num = 3
        craft_pos = []
        for _ in range(craft_num):
            craft_x, craft_y, craft_z = random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1) 
            while craft_y > ory + 4 or (craft_x, craft_y, craft_z) in craft_pos:    # 避免生成在太高的地方
                craft_x, craft_y, craft_z = random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1) 
            craft_pos.append((craft_x, craft_y, craft_z))
            bot.chat(f"/setblock {craft_x} {craft_y} {craft_z} crafting_table")
            time.sleep(.2)

        if arg_dict["item_position"] == "chest": # 材料在随机位置的箱子里
            set_chest(craft_pos, ingredients_list)
        elif arg_dict["item_position"] == "inventory": # 材料在Agent身上
            for ingredients in ingredients_list:
                bot.chat(f"/give {agent_name} {ingredients['name']} {ingredients['count']}")
        else:
            bot.chat("/tellraw @a {\"text\":\"INVALID ITEM POSITION!\", \"color\":\"red\"}")

    elif config["task_scenario"] == "place":
        goal_item = aligned_item_name(arg_dict["target"])

        if arg_dict["item_position"] == "inventory":
            bot.chat(f"/give {agent_name} {goal_item} 1")
            bot.chat(f"/give {agent_name} dirt 15")
        elif arg_dict["item_position"] == "chest":
            set_chest([(arg_dict['x'], arg_dict['y'], arg_dict['z'])], [{"name": goal_item, "count": 1}, {"name": "dirt", "count": 15}])
        else:
            bot.chat("/tellraw @a {\"text\":\"INVALID ITEM POSITION!\", \"color\":\"red\"}")

    elif config["task_scenario"] == "move":
        if arg_dict["item_position"] == "inventory":
            bot.chat(f"/give {agent_name} dirt 10")
            bot.chat(f"/give {agent_name} ladder 10")
            bot.chat(f"/give {agent_name} diamond_pickaxe 1")
        elif arg_dict["item_position"] == "chest":
            set_chest([(arg_dict['x'], arg_dict['y'], arg_dict['z'])], [{"name": "dirt", "count": 10}, {"name": "ladder", "count": 10}, {"name": "diamond_pickaxe", "count": 1}])
        else:
            bot.chat("/tellraw @a {\"text\":\"INVALID ITEM POSITION!\", \"color\":\"red\"}")

    elif config["task_scenario"] == "useitem":
        goal_item = aligned_item_name(arg_dict["target"])
        if arg_dict["item_position"] == "inventory":
            bot.chat(f"/give {agent_name} {goal_item} 1")
            bot.chat(f"/give {agent_name} dirt 5")
        elif arg_dict["item_position"] == "chest":
            set_chest([], [{"name": goal_item, "count": 1}, {"name": "dirt", "count": 5}])
        else:
            bot.chat("/tellraw @a {\"text\":\"INVALID ITEM POSITION!\", \"color\":\"red\"}")

    elif config["task_scenario"] == "interact":
        target = aligned_item_name(arg_dict["target"])
        if target == "Bob":
            interact_type = "player"
        else:
            with open("data/animals.json", "r") as f:
                animal_list = json.load(f)
                for animal in animal_list:
                    if animal["name"] == target:   
                        interact_type = "animal"
                        break

        if arg_dict["action"] == "bone_meal":
            base_block = aligned_item_name(arg_dict["other_arg"][0]['base_block'])
            crop = aligned_item_name(arg_dict["other_arg"][0]['crops'])
            
            bot.chat(f"/setblock {arg_dict['x']} {arg_dict['y']} {arg_dict['z']} {base_block}")
            if arg_dict["item_position"] == "inventory":
                bot.chat(f"/give {agent_name} {arg_dict['tool']} 1")
                bot.chat(f"/give {agent_name} {crop} {random.randint(1, 2)}")
            elif arg_dict["item_position"] == "chest":
                set_chest([(arg_dict['x'], arg_dict['y'], arg_dict['z'])], [{"name": arg_dict['tool'], "count": 1}])
                set_chest([(arg_dict['x'], arg_dict['y'], arg_dict['z'])], [{"name": crop, "count": random.randint(1, 2)}])
        
        elif arg_dict["action"] == "ladder":
            pass

        
        elif interact_type == "animal":
            bot.chat(f"/summon {target} {orx + room_width // 2 + 1} {ory + 4} {orz + 3}")
            if arg_dict["item_position"] == "inventory":
                bot.chat(f"/give {agent_name} {arg_dict['tool']} 1")
            elif arg_dict["item_position"] == "chest":
                set_chest([], [{"name": arg_dict['tool'], "count": 1}])
            else:
                bot.chat("/tellraw @a {\"text\":\"INVALID ITEM POSITION!\", \"color\":\"red\"}")
        elif interact_type == "block":
            if arg_dict["action"] == "cook":
                furnace_num = 3
                furnace_pos = []
                for _ in range(furnace_num):
                    furnace_x, furnace_y, furnace_z = random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1) 
                    while furnace_y > ory + 4 or (furnace_x, furnace_y, furnace_z) in furnace_pos:    # 避免生成在太高的地方
                        furnace_x, furnace_y, furnace_z = random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1) 
                    furnace_pos.append((furnace_x, furnace_y, furnace_z))
                    bot.chat(f"/setblock {furnace_x} {furnace_y} {furnace_z} furnace")
                    time.sleep(.2)


                # furnace_x, furnace_y, furnace_z = random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1)        
                item_list = [{"name": item, "count": 1} for item in arg_dict['other_arg']]
                if arg_dict["item_position"] == "inventory":
                    for item in item_list:                    
                        bot.chat(f"/give {agent_name} {item['name']} {item['count']}")
                        time.sleep(.1)
                elif arg_dict["item_position"] == "chest":
                    set_chest(furnace_pos, item_list)
                else:
                    bot.chat("/tellraw @a {\"text\":\"INVALID ITEM POSITION!\", \"color\":\"red\"}")
            if arg_dict["action"] == "store":
                bot.chat(f"/setblock {arg_dict['x']} {arg_dict['y']} {arg_dict['z']} chest")
                bot.chat(f"/give {agent_name} {arg_dict['other_arg'][0]} 1")

        elif interact_type == "player":
            global arg_host, arg_port
            npcbot = mineflayer.createBot({
                "host": arg_host,
                "port": arg_port,
                'username': "Bob",
                'checkTimeoutInterval': 600000,
                'auth': 'offline',
                'version': "1.19.2",
            })
            npc_x, npc_y, npc_z= random_position(orx + wall_width, orz + wall_width, orx + wall_width + room_width - 1, orz + wall_width + room_width - 1, 1)
            bot.chat(f"/clear Bob")
            bot.chat(f"/tp Bob {npc_x} {npc_y} {npc_z}")
            if arg_dict["action"] == "handover":
                bot.chat(f"/give {agent_name} {arg_dict['other_arg'][0]}")


    else:
        bot.chat("/tellraw @a {\"text\":\"INVALID SCENARIO!\", \"color\":\"red\"}")



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
                if Block._properties["facing"] and facing in ["west", "east", "south", "north"]:
                    if Block._properties["facing"] == facing:
                        return True
                if Block._properties["axis"] and facing in ["x", "y", "z"]:
                    if Block._properties["axis"] == facing:
                        return True
                return False
            else:
                return True

    global last_time, start_time, score
    if start_time is not None:
        global complexity_score, efficiency, balance, info_count, environment_set_time, interact_type
        now_time = time.time()
        with open(".cache/meta_setting.json", "r") as f:
            config = json.load(f)
        arg_dict = config["evaluation_arg"]

        if now_time - last_time > 1:
            info_count += 1
            if info_count % 20 == 0:
                bot.chat(f'score: {score}')

            if config["task_scenario"] in ["craft", "move"] or (config["task_scenario"] == "useitem" and "sign" not in arg_dict["target"]):
                bot.chat(f'/recipe take {agent_name} *') # 去除合成表中的所有合成
                bot.chat(f'/data get entity {agent_name}')

            elif config["task_scenario"] == "useitem":
                goal_item = arg_dict["target"]
                if "sign" in goal_item:
                    bot.chat(f'/data get block {arg_dict["x"]} {arg_dict["y"]} {arg_dict["z"]}')

            elif config["task_scenario"] == "dig":
                goal_item = aligned_item_name(arg_dict["target"])
                Block = bot.blockAt(Vec3(arg_dict['x'], arg_dict['y'], arg_dict['z']))
                if now_time - start_time  > environment_set_time and aligned_item_name(Block["name"]) != goal_item:
                    score = 100

            elif config["task_scenario"]  == "place":
                goal_item = aligned_item_name(arg_dict["target"])
                pos_list = [arg_dict['x'], arg_dict['y'], arg_dict['z']]
                if arg_dict["facing"]:
                    pos_list.append(arg_dict["facing"])
                if check_block(pos_list, goal_item):
                    score = 100 

            elif config["task_scenario"]  == "interact":
                target = aligned_item_name(arg_dict["target"]) 
                
                if arg_dict["action"] == "bone_meal":
                    bot.chat(f'/recipe take {agent_name} *') # 去除合成表中的所有合成
                    bot.chat(f'/data get entity {agent_name}')
                
                if interact_type == "block":
                    if arg_dict["action"] == "cook":
                        bot.chat(f'/recipe take {agent_name} *') # 去除合成表中的所有合成
                        bot.chat(f'/data get entity {agent_name}')
                    if arg_dict["action"] == "store":
                        bot.chat(f"/data get block {arg_dict['x']} {arg_dict['y']} {arg_dict['z']}")
                if interact_type == "animal":
                    if arg_dict["action"] in ["feed", "shear"]:
                        bot.chat(f'/recipe take {agent_name} *') # 去除合成表中的所有合成
                        bot.chat(f"/data get entity @e[type={target},limit=1,sort=nearest]")
                    if arg_dict["action"] == "milk":
                        bot.chat(f'/recipe take {agent_name} *') # 去除合成表中的所有合成
                        bot.chat(f'/data get entity {agent_name}')
                if interact_type == "player":
                    if arg_dict["action"] == "handover":
                        bot.chat(f'/recipe take {agent_name} *') # 去除合成表中的所有合成
                        bot.chat(f'/data get entity {arg_dict["target"]}')

            if score == 100:
                time.sleep(5)
                if not os.path.exists("result/" + task_name):
                    os.mkdir(os.path.join("result/", task_name))
                with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                    json.dump({
                        "score": score,
                        "use_time": calculate_action_time(),
                        "end_reason": "task completed",
                        "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
                    }, f, indent=4)
                with open(os.path.join(os.path.join("result", task_name), "config.json"), "w") as f:
                    json.dump(config, f, indent=4)
                with open(".cache/load_status.cache", "w") as f:
                    json.dump({"status": "end"}, f, indent=4)
            if calculate_action_time() > max_action_time:
                efficiency = 1
                # 给出结束信号和写入文件
                if not os.path.exists("result/" + task_name):
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
                with open(os.path.join(os.path.join("result", task_name), "config.json"), "w") as f:
                    json.dump(config, f, indent=4)
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
    global score, info_count, interact_type
    with open(".cache/meta_setting.json", "r") as f:
        config = json.load(f)
    arg_dict = config["evaluation_arg"]

    def calculate_score(inventory, pos):
        if config["task_scenario"] == "craft":
            goal_item = aligned_item_name(arg_dict["target"])
            for item in inventory:
                if aligned_item_name(item['id']) == goal_item:
                    return 100        
                
        elif config["task_scenario"] == "move":
            x = float(pos[0][:-1])
            y = float(pos[1][:-1])
            z = float(pos[2][:-1])
            if abs(x - arg_dict['x']) < 1 and abs(y - arg_dict['y']) < 1 and abs(z - arg_dict['z']) < 1:
                return 100 
            
        elif config["task_scenario"] == "useitem":
            goal_item = aligned_item_name(arg_dict["target"])
            for item in inventory:
                if aligned_item_name(item['id']) == goal_item and int(item['Slot'][:-1]) >= 100:
                    return 100
        
        elif config["task_scenario"] == "interact":
            if arg_dict["action"] == "cook":
                if aligned_item_name(arg_dict["other_arg"][-1]) != "potato":
                    goal_item = "cooked_" + aligned_item_name(arg_dict["other_arg"][-1])  # 设置最后一个位置是放置需要烤的东西
                else:
                    goal_item = "baked_" + aligned_item_name(arg_dict["other_arg"][-1])   
            elif arg_dict["action"] == "handover":
                goal_item = arg_dict["other_arg"][0]
            elif arg_dict["action"] == "milk":
                goal_item = "milk_bucket"
            else:
                 goal_item = ""
            for item in inventory:
                if aligned_item_name(item['id']) == goal_item:
                    return 100
                    
        return 0
    
    if start_time is not None:
        data_pattern = "(.*) has the following (.*) data: (.*)"
        data_match = re.search(data_pattern, message)
        if data_match:
            entity_name = data_match.group(1)
            block_entity = data_match.group(2)
            data_str = data_match.group(3)
        else:
            entity_name = None
            block_entity = None
            data_str = None

        chat_pattern = r"\[(.*?)\]\s*--(MSG|CHAT)--\s*\[(.*?)\]\s*(.*)"
        chat_match = re.search(chat_pattern, message)
        if chat_match:
            host_name = chat_match.group(1)  # 第一个方括号内的内容
            target_name = chat_match.group(3)  # 第二个方括号内的内容
            msg = chat_match.group(4)  # 剩余的消息内容
        else:
            host_name = None
            target_name = None
            msg = None

        if entity_name is not None and data_str is not None and block_entity is not None:
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

            try:    
                data = json.loads(data_str)
            except: # Lazy fix
                bot.chat(f"Error: JUDGER -- JSONDecodeError")
                data = {}

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

            if config["task_scenario"] in ["craft", "move"] or (config["task_scenario"] == "interact" and arg_dict["action"] in ["handover","cook", "milk"]) or (config["task_scenario"] == "useitem" and "sign" not in arg_dict["target"]):
                inventory = data.get("Inventory", [])
                pos = data.get("Pos", [])
                score = calculate_score(inventory, pos)
            elif config["task_scenario"] == "interact" and arg_dict["action"] == "feed":
                inlove = data.get("InLove", 0)
                if int(inlove) > 0:
                    score = 100
            elif config["task_scenario"] == "interact" and arg_dict["action"] == "shear":
                sheared = data.get("Sheared", "0b")
                if int(sheared[:-1]):
                    score = 100
            elif config["task_scenario"] == "interact" and arg_dict["action"] == "store":
                if "Items" in data:
                    for item in data["Items"]:
                        if aligned_item_name(item["id"]) == arg_dict["other_arg"][0]:
                            score = 100
            elif config["task_scenario"] == "useitem" and "sign" in arg_dict["target"]:
                for i in range(1, 5):
                    if f"Text{i}" in data:
                        if data[f"Text{i}"]["text"] == arg_dict["other_arg"][0]:
                            score = 100

            elif config["task_scenario"] == "interact" and arg_dict["action"] == "bone_meal":
                if "Items" in data:
                    for item in data["Items"]:
                        score = 100
                        if aligned_item_name(item["id"]) == "milk_bucket":
                            score = 0
            # info_count += 1
            # if info_count % 20 == 0:
            #     bot.chat(f'score: {score}')
        
        if host_name is not None and target_name is not None and msg is not None:
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
            # messages.append(msg)
            
            # # 将消息列表写回文件
            # with open(file_path, 'w', encoding='utf-8') as f:
            #     json.dump(messages, f, ensure_ascii=False, indent=4)
            
            if config["task_scenario"] == "interact" and arg_dict["action"] == "chat":
                if msg== arg_dict["other_arg"][0]:
                    score = 100

@On(bot, "entityHurt")
def handleAttack(_, entity):
    global environment_set_time, score
    with open(".cache/meta_setting.json", "r") as f:
        config = json.load(f)
    arg_dict = config["evaluation_arg"]
    if arg_dict["action"] == "attack":
        if start_time is not None:
            now_time = time.time()
            if now_time - start_time  > environment_set_time:
                if aligned_item_name(arg_dict["target"]) == aligned_item_name(entity.name):
                    score = 100
