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

# metrics
complexity_score = 0
efficiency = 0
balance = 0

@On(bot, 'spawn')
def handleViewer(*args):

    for name in agent_names:
        bot.chat(f'/op {name}')
        time.sleep(.2)

    room_width = 15
    room_height = 15
    wall_width = 1

    orx = 0     #origin_point
    ory = -61
    orz = 0

    print("start setting environment", flush = True)

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
    bot.chat(f"/tp @s {orx + room_width//2 + 1} {ory + room_height // 2} {orz + wall_width} 0 -45")
    time.sleep(.5)
    bot.chat(f"/tp @e[gamemode=survival] {orx + room_width // 2 + 1} {ory + 1} {orz + 2} 0 0")
    time.sleep(.5)
    bot.chat("/clear @e[distance=..10,type=player,gamemode=survival]")
    time.sleep(.5)
    bot.chat("/kill @e[type=!minecraft:player]")
    time.sleep(.5)
    bot.chat("/kill @e[type=!minecraft:player]")
    time.sleep(.5)

    bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + 2 * wall_width} {ory + room_height + 2 * wall_width} {orz + room_width + 2 * wall_width} glass hollow")
    time.sleep(.5)
    bot.chat(f"/fill {orx} {ory} {orz} {orx + room_width + 2 * wall_width} {ory} {orz + room_width + 2 * wall_width} grass_block")
    time.sleep(.5)
    # 生成一个内部空间width*width*height，五面玻璃一面草方块的封闭空间
    bot.chat(f"/setblock {orx + room_width // 2 + 1} {ory + 1} {orz + room_width // 2 + 1} oak_planks")

    print("environment set", flush = True)

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
        global last_time, start_time
        if start_time is not None:
            global complexity_score, efficiency, balance
            now_time = time.time()
            if now_time - last_time > 1:
                agent = bot.player[agent_names[0]]
                
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
