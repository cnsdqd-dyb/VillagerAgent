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

parser = argparse.ArgumentParser()
parser.add_argument('--idx', type=int, default=0, help='the index of the escape test to be judged')
parser.add_argument('--max_task_num', type=int, default=1, help='how many tasks in the test')
parser.add_argument('--agent_num', type=int, default=1, help='how many agents in the test')
parser.add_argument('--mc_version', type=str, default="1.19.2", help='the version of minecraft')
parser.add_argument('--host', type=str, default="10.21.31.18", help='the host of the server')
parser.add_argument("--port", type=int, default=25565, help="the port of the server")
parser.add_argument("--agent_names", type=str, default="", help="the name of the agents in A,B,C format")
parser.add_argument("--task_name", type=str, default="test", help="the name of the task")
parser.add_argument("--op_path", type=str, default="", help="the op command path")

args = parser.parse_args()
select_idx = args.idx
agent_num = args.agent_num
max_task_num = args.max_task_num
agent_names = args.agent_names.split(",")
task_name = args.task_name
op_path = args.op_path

mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
collectBlock = require('mineflayer-collectblock')
pvp = require("mineflayer-pvp").plugin
minecraftHawkEye = require("minecrafthawkeye").default
Vec3 = require("vec3")
Socks = require("socks5-client")
minecraftData = require('minecraft-data')
mcData = minecraftData(args.mc_version)

y_b = -60  # -60
bot = mineflayer.createBot({
    "host": args.host,
    "port": args.port,
    'username': "auto_gen",
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

import re

def process_quotes_regex(s):
    # 找到所有的 \"
    s = s.replace('"','\\\"')
    matches = list(re.finditer(r'\\\"', s))
    print(s)
    if matches:
        # 替换第一个和最后一个
        s = s[:matches[0].start()] + '"' + s[matches[0].end():]
        s = s[:matches[-1].start()-1] + '"' + s[matches[-1].end()-1:]
    print(s)
    return s

@On(bot, 'spawn')
def handleViewer(*args):

    for name in agent_names:
        bot.chat(f'/op {name}')
        time.sleep(.2)

    time.sleep(.1)
    bot.chat(f'/tp @s -5 {y_b} 0')
    time.sleep(.1)
    bot.chat(f'/tp @e[type=player,gamemode=survival] @s')
    bot.chat(f'/clear @e[type=player,gamemode=survival]')
    bot.chat(f'/tp @e[type=player,gamemode=creative] @s')
    bot.chat(f'/clear @e[type=player,gamemode=creative]')
    bot.chat('/time set day')
    time.sleep(.1)
    bot.chat('/weather clear')
    time.sleep(.1)
    bot.chat('/gamerule doDaylightCycle false')
    time.sleep(.1)
    bot.chat('/gamemode spectator')
    time.sleep(.1)
    bot.chat('/kill @e[type=!minecraft:player]')
    time.sleep(1)
    bot.chat('/kill @e[type=!minecraft:player]')
    time.sleep(1)
    bot.chat('/kill @e[type=!minecraft:player]')

    for y in range(y_b + 20, y_b - 1, -1):
        bot.chat(f"/fill -40 {y} -40 40 {y} 40 minecraft:air")
        time.sleep(.1)

    bot.chat(f'/fill -20 {y_b} -20 -20 {y_b + 15} 20 minecraft:glass')
    time.sleep(.1)
    bot.chat(f'/fill -20 {y_b} -20 20 {y_b + 15} -20 minecraft:glass')
    time.sleep(.1)
    bot.chat(f'/fill -20 {y_b} 20 20 {y_b + 15} 20 minecraft:glass')
    time.sleep(.1)
    bot.chat(f'/fill 20 {y_b} -20 20 {y_b + 15} 20 minecraft:glass')
    time.sleep(.1)
    bot.chat(f'/fill 40 -61 40 -40 -61 -40 minecraft:grass_block')

    

    op_commands = json.load(open(op_path, "r"))
    for op in op_commands["materials_op"]:
        if "minecraft:water" in op:
            bot.chat(op.replace("-60","-61"))
        else:
            bot.chat(op)
        time.sleep(.2)
    place_op = op_commands["place_op"].strip().split(" ")
    names = place_op[2].split("_")
    place_op_full = f"/place template minecraft:village/{names[0]}/houses/{place_op[2]}_1 0 -60 -0"
    bot.chat(place_op_full)
    time.sleep(.2)
    for op in op_commands["blocks_op"]:
        if "Text" in op:
            bot.chat(process_quotes_regex(op))
        bot.chat(op)
        time.sleep(.2)
    bot.chat("/setblock 5 -60 0 crafting_table")
    for op in op_commands["inventory_op"]:
        bot.chat(op)
        time.sleep(.2)
    for op in op_commands["environ_op"]:
        bot.chat(op)
        time.sleep(.2)



    with open(".cache/load_status.cache", "w") as f:
        json.dump({"status": "loaded"}, f, indent=4)

    summon_time = 40
    for i in range(summon_time):
        time.sleep(1)

    for op in op_commands["entities_op"]:
        bot.chat(op)
        time.sleep(.2)
    

    