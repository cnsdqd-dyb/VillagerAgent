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
    'username': "escape_judge",
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

max_action_time = 0
max_time = 0

# metrics
complexity_score = 0
efficiency = 0
balance = 0


def calculate_score(state_tree):
    done_task = 0
    for task in state_tree.task_list:
        if task.done:
            done_task += 1
        else:
            satisfied = 0
            total = 0
            for event in task.events:
                satisfied += event.current_max_satisfy_num
                total += len(event.state_dict)
            done_task += satisfied / total
    return done_task / len(state_tree.task_list)


@On(bot, 'spawn')
def handleViewer(*args):

    for name in agent_names:
        bot.chat(f'/op {name}')
        time.sleep(.2)

    bot.chat("/gamemode spectator")
    bot.chat("/gamerule doDaylightCycle false")
    bot.chat("/gamerule doWeatherCycle false")
    bot.chat("/time set day")
    bot.chat("/weather clear")
    bot.chat("/tp 130 -60 140")
    bot.chat("/tp @e[gamemode=survival] @s")
    bot.chat("/clear @e[distance=..10,type=player,gamemode=survival]")

    state_tree = StateTree(bot, Vec3, agent_num=agent_num, bias=[130, -60, 140], max_task_num=max_task_num,
                           file_path="data/escape_atom.json",seed=select_idx)
    # 110 -60 140
    state_tree.load(bot)

    global max_action_time, max_time
    max_action_time = state_tree.complexity * 30 + 60
    max_time = len(state_tree.task_list) * 60 + 360

    with open(".cache/load_status.cache", "w") as f:
        json.dump({"status": "loaded"}, f, indent=4)
    for i in range(-3, 4):
        for j in range(-3, 4):
            if (i + j) % 2 == 0:
                bot.chat(f"/setblock {130 + i} {y_b} {140 + j} minecraft:white_wool")
            else:
                bot.chat(f"/setblock {130 + i} {y_b} {140 + j} minecraft:black_wool")
            time.sleep(.01)
    bot.chat(f"/setblock 130 {y_b + 1} 140 minecraft:chest[facing=north]")
    bot.chat(f"/setblock 130 {y_b + 1} 141 minecraft:red_banner[rotation=8]")
    
    bot.chat("/clear @e[type=player,gamemode=survival] minecraft:red_banner")
    
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
                tag = state_tree.update()
                
                score = calculate_score(state_tree)
                bot.chat(f"{score}")
                complexity_score = state_tree.complexity * score
                balance = calculate_balance()
                bot.chat(f"{state_tree.complexity} {score}")

                if tag:
                    if calculate_action_time() == 0:
                        efficiency = 1
                    else:
                        efficiency = max_action_time / calculate_action_time()
                    # 给出结束信号和写入文件
                    if not os.path.exists("result/" + task_name):
                        os.mkdir(os.path.join("result", task_name))
                    with open(os.path.join(os.path.join("result", task_name), "score.json"), "w") as f:
                        json.dump({
                            "complete_score": score,
                            "complexity_score": complexity_score,
                            "efficiency": efficiency,
                            "balance": balance,
                            "use_time": calculate_action_time(),
                            "end_reason": "complete task",
                            "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))
                        }, f, indent=4)
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
