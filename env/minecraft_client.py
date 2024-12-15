import time
from langchain.agents import tool, initialize_agent, AgentType
from langchain.callbacks import get_openai_callback
from langchain.load.dump import dumps
from langchain_core.callbacks.base import BaseCallbackManager
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult


import json
import requests
import subprocess
import logging
import datetime
import threading
from functools import wraps
import os
import random

def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # 确保data目录存在
        if not os.path.exists("data"):
            os.makedirs("data")
        
        max_try = 3
        while max_try:
            try:
                # action log
                action_log_path = "data/action_log.json"
                if os.path.exists(action_log_path):
                    with open(action_log_path, "r") as f:
                        action_log = json.load(f)
                else:
                    action_log = {}
                agent_name = kwargs["player_name"] # 第一个参数是 agent_name
                if agent_name not in action_log:
                    action_log[agent_name] = []
                
                # 注意：args, kwargs 和 result 需要是可序列化的
                action_log[agent_name].append({
                    "action": func.__name__,
                    # "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time)),
                    "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time)),
                    "duration": end_time - start_time,
                    "kwargs": kwargs,  # kwargs 可能包含不可序列化的对象
                    "result": result,  # result 可能包含不可序列化的对象
                })
                
                # 写入文件
                with open(action_log_path, "w") as f:
                    json.dump(action_log, f, indent=4)
                break
            except Exception as e:
                print(e)
                max_try -= 1
                time.sleep(1)
        
        return result
    return wrapper

    
class LLMHandler(BaseCallbackHandler):
    def __init__(self):
        self.llm_out = []
        self.seralized_input = []
        self.chain_input = []

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id = None, tags = None, metadata = None, **kwargs):
        self.seralized_input.append(serialized)
        self.chain_input.append(inputs)

    def on_llm_start(
        self,
        serialized,
        prompts,
        **kwargs,
    ):
        self.seralized_input.append(serialized)
        self.chain_input.append(prompts)
        
    def on_llm_end(self, llm_result: LLMResult, **kwargs):
        self.llm_out.append(llm_result.llm_output)
    
class Agent():
    '''
    Agent is the basic class for the agent in the Minecraft environment.
    Agent supports high-level and low-level functions for the agent to interact with the Minecraft environment.
    It works as a bridge between the Minecraft environment and the AI model.
    '''
    headers = {'Content-Type': 'application/json'}

    logging.basicConfig()
    logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)
    model = "gpt-4-1106-preview"
    temperature = 0
    max_tokens = 1024
    api_key_list = []
    base_url = "https://api.chatanywhere.tech/v1"
    verbose = True

    name2port = {}
    agent_process = {}
    url_prefix = {}

    @staticmethod
    def get_url_prefix() -> dict:
        if os.path.exists("data/url_prefix.json"):
            with open("data/url_prefix.json", "r") as f:
                url_prefix = json.load(f)
        else:
            url_prefix = {}
        return url_prefix

    def __init__(self, name, prefix=None, context=None, prompt=None, tools=[], local_port=5000, model=""):
        self.name = name
        self.prefix = prefix
        self.context = context
        self.prompt = prompt
        self.local_port = local_port
        self.model = Agent.model if model == "" else model
        self.action_history = []
        self.basic_tools = [
            Agent.scanNearbyEntities, Agent.navigateTo, Agent.attackTarget,
            Agent.UseItemOnEntity, Agent.fetchContainerContents,
            Agent.MineBlock, Agent.placeBlock, Agent.equipItem,
            Agent.handoverBlock, Agent.SmeltingCooking, Agent.talkTo, Agent.waitForFeedback,
            Agent.withdrawItem, Agent.storeItem, Agent.craftBlock,Agent.ToggleAction, 
        ]
        self.all_tools = [
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
        if tools:
            self.tools = tools
        else:
            self.tools = self.basic_tools

        if name == "nobody":
            return
        url_prefix = Agent.get_url_prefix()
        url_prefix[name] = f"http://localhost:{local_port}"
        with open("data/url_prefix.json", "w") as f:
            json.dump(url_prefix, f)

        Agent.name2port[name] = local_port
        if prefix is None:
            self.prefix = "You are a helpful friendly assistant.\n"

    def render(self, structure_idx, center_pos):
        url = Agent.get_url_prefix()[self.name] + "/post_render"
        data = {
            "id": structure_idx,
            "center_pos": center_pos,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    def env(self, prompt):
        """Get the Environment Information"""
        url = Agent.get_url_prefix()[self.name] + "/post_environment"
        response = requests.post(url, headers=Agent.headers)
        return str(response.json())
    
    def get_environment_info_dict(player_name: str):
        """Get the Environment Information, return string contains time of day, weather"""
        url = Agent.get_url_prefix()[player_name] + "/post_environment_dict"
        response = requests.post(url, headers=Agent.headers)
        return response.json()
    
    def ping(player_name: str):
        """Ping the Server"""
        url = Agent.get_url_prefix()[player_name] + "/post_ping"
        response = requests.get(url)
        return response.json()

    @staticmethod
    def launch(host="10.21.31.18", port=25565, world="world", verbose=False, ignore_name=[], debug=False, fast=False):
        Agent.port = port
        if verbose:
            print("launch ...")
        for key, value in Agent.name2port.items():
            if key in ignore_name:
                continue
            if fast:
                try:
                    Agent.agent_process[key] = subprocess.Popen(
                        ["python", "env/minecraft_server_fast.py", "-H", host, "-P", str(port), "-LP", str(value), "-U", key, "-W",
                    world, "-D", str(debug)], shell=False)
                    print(f"python env/minecraft_server_fast.py -H \"{host}\" -P {port} -LP {value} -U \"{key}\" -W \"{world}\" -D {debug}")
                except Exception as e:
                    print(f"An error occurred: {e}")
                    print(f"python env/minecraft_server_fast.py -H \"{host}\" -P {port} -LP {value} -U \"{key}\" -W \"{world}\" -D {debug}")
                time.sleep(10)
            else:
                Agent.agent_process[key] = subprocess.Popen(
                    ["python", "env/minecraft_server.py", "-H", host, "-P", str(port), "-LP", str(value), "-U", key, "-W",
                 world, "-D", str(debug)], shell=False)
                print(f"python env/minecraft_server.py -H \"{host}\" -P {port} -LP {value} -U \"{key}\" -W \"{world}\" -D {debug}")
                time.sleep(2)
        if verbose:
            print("launch done.")

    @staticmethod
    def kill():
        for value in Agent.agent_process.values():
            value.terminate()

    # @tool
    # @timeit
    # def getMsg(player_name: str):
    #     """Get the Message from the Server"""
    #     url = Agent.get_url_prefix()[player_name] + "/post_msg"
    #     response = requests.post(url, headers=Agent.headers)
    #     return response.json()

    @tool
    @timeit
    def erectDirtLadder(player_name: str, top_x, top_y, top_z):
        """Helpful to place item at higher place Erect a Dirt Ladder Structure at Specific Position x y z, remember to dismantle it after use"""
        url = Agent.get_url_prefix()[player_name] + "/post_erect"
        data = {
            "top_x": top_x,
            "top_y": top_y,
            "top_z": top_z,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()
    
    @tool
    @timeit
    def dismantleDirtLadder(player_name: str, top_x, top_y, top_z):
        """Dismantle a Dirt Ladder Structure from ground to top at Specific Position x y z"""
        url = Agent.get_url_prefix()[player_name] + "/post_dismantle"
        data = {
            "top_x": top_x,
            "top_y": top_y,
            "top_z": top_z,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def layDirtBeam(player_name: str, x_1, y_1, z_1, x_2, y_2, z_2):
        """Lay a Dirt Beam from Position x1 y1 z1 to Position x2 y2 z2"""
        url = Agent.get_url_prefix()[player_name] + "/post_lay"
        data = {
            "x_1": x_1,
            "y_1": y_1,
            "z_1": z_1,
            "x_2": x_2,
            "y_2": y_2,
            "z_2": z_2,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()
    
    @tool
    @timeit
    def removeDirtBeam(player_name: str, x_1, y_1, z_1, x_2, y_2, z_2):
        """Remove a Dirt Beam from Position x1 y1 z1 to Position x2 y2 z2"""
        url = Agent.get_url_prefix()[player_name] + "/post_remove"
        data = {
            "x_1": x_1,
            "y_1": y_1,
            "z_1": z_1,
            "x_2": x_2,
            "y_2": y_2,
            "z_2": z_2,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()


    @tool
    @timeit
    def scanNearbyEntities(player_name: str, item_name: str, radius: int = 10, item_num: int = -1):
        """Find minecraft item blocks chests creatures in a radius, return ('message': msg, 'status': True/False, 'data':[('x':x,'y':y,'z':z),...]) This function can not find items in the chest, container,or player's inventory."""
        url = Agent.get_url_prefix()[player_name] + "/post_find"
        data = {
            "name": item_name.lower().replace(" ", "_"),
            "distance": radius,
            "count": item_num,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def handoverBlock(player_name: str, target_player_name: str, item_name: str, item_count: int):
        """Hand Item to a target player you work with, return ('message': msg, 'status': True/False), item num will be automatically checked and player will automatically move to the target player"""
        url = Agent.get_url_prefix()[player_name] + "/post_hand"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "from_name": player_name, 
            "target_name": target_player_name,
            "item_count": item_count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def navigateToPlayer(player_name: str, target_name: str):
        """Move to a target Player,return ('message': msg, 'status': True/False)"""
        url = Agent.get_url_prefix()[player_name] + "/post_move_to"
        data = {
            "name": target_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def navigateToBuilding(player_name: str, building_name: str):
        """Move to a building by name, return string result"""
        url = Agent.get_url_prefix()[player_name] + "/post_move_to"
        data = {
            "name": building_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def navigateToAnimal(player_name: str, animal_name: str):
        """Move to an animal by name, return string result"""
        url = Agent.get_url_prefix()[player_name] + "/post_move_to"
        data = {
            "name": animal_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def navigateTo(player_name: str, x: int, y: int, z: int):
        """Move to a Specific Position x y z, return string result"""
        url = Agent.get_url_prefix()[player_name] + "/post_move_to_pos"
        data = {
            "x": x,
            "y": y,
            "z": z,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()
    
    def _navigateTo(player_name: str, x: int, y: int, z: int):
        """Move to a Specific Position x y z, return string result"""
        url = Agent.get_url_prefix()[player_name] + "/post_move_to_pos"
        data = {
            "x": x,
            "y": y,
            "z": z,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def UseItemOnEntity(player_name: str, item_name: str, entity_name: str):
        """Use a Specific Item on a Specific Entity, return string result"""
        url = Agent.get_url_prefix()[player_name] + "/post_use_on"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "entity_name": entity_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def sleep(player_name: str):
        """Go to Sleep"""
        url = Agent.get_url_prefix()[player_name] + "/post_sleep"
        response = requests.post(url, headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def wake(player_name: str):
        """Wake Up"""
        url = Agent.get_url_prefix()[player_name] + "/post_wake"
        response = requests.post(url, headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def MineBlock(player_name: str, x: int, y: int, z: int):
        """Dig Block at Specific Position x y z"""
        url = Agent.get_url_prefix()[player_name] + "/post_dig"
        data = {
            "x": x,
            "y": y,
            "z": z,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def placeBlock(player_name: str, item_name: str, x: int, y: int, z: int, facing: str):
        """Place a Specific Item at Specific Position x y z with Specific facing in one of [W, E, S, N, x, y, z, A] default is 'A'., return ('message': msg, 'status': True/False)"""
        url = Agent.get_url_prefix()[player_name] + "/post_place"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "x": x,
            "y": y,
            "z": z,
            "facing": facing,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def attackTarget(player_name: str, target_name: str):
        """Attack the Nearest Entity with a Specific Name"""
        url = Agent.get_url_prefix()[player_name] + "/post_attack"
        data = {
            "name": target_name.lower().replace(" ", "_"),
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def equipItem(player_name: str, slot: str, item_name: str):
        """Equip a Specific Item on a Specific Slot | to equip item on hand,head,torso,legs,feet,off-hand."""
        url = Agent.get_url_prefix()[player_name] + "/post_equip"
        data = {
            "slot": slot,
            "item_name": item_name.lower().replace(" ", "_"),
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def tossItem(player_name: str, item_name: str, count: int = 1):
        """Throw a Specific Item Out with a Specific Count"""
        url = Agent.get_url_prefix()[player_name] + "/post_toss"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "count": count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def get_environment_info(player_name: str):
        """Get the Environment Information, return string contains time of day, weather"""
        url = Agent.get_url_prefix()[player_name] + "/post_environment"
        response = requests.post(url, headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def get_entity_info(player_name: str, target_name: str = ""):
        """Get the Entity Information, return string contains entity name, entity pos x y z, entity held item"""
        url = Agent.get_url_prefix()[player_name] + "/post_entity"
        data = {
            "name": target_name.lower().replace(" ", "_"),
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def withdrawItem(player_name: str, item_name: str, from_name: str, item_count: int):
        """Take out Item from nearest 'chest' | 'container' | 'furnace' return string result"""
        url = Agent.get_url_prefix()[player_name] + "/post_get"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "from_name": from_name.lower().replace(" ", "_"),
            "item_count": item_count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def storeItem(player_name: str, item_name: str, to_name: str, item_count: int):
        """Put in Item to One Chest, Container, etc, return string result"""
        url = Agent.get_url_prefix()[player_name] + "/post_put"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "to_name": to_name.lower().replace(" ", "_"),
            "item_count": item_count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def SmeltingCooking(player_name: str, item_name: str, item_count: int, fuel_item_name: str):
        """Smelt or Cook Item in the Furnace"""
        url = Agent.get_url_prefix()[player_name] + "/post_smelt"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "item_count": item_count,
            "fuel_item_name": fuel_item_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def craftBlock(player_name: str, item_name: str, count: int):
        """Craft Item in the Crafting Table"""
        url = Agent.get_url_prefix()[player_name] + "/post_craft"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "count": count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def enchantItem(player_name: str, item_name: str, count: int):
        """Enchant Item in the Enchanting Table"""
        url = Agent.get_url_prefix()[player_name] + "/post_enchant"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "count": count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def trade(player_name: str, item_name: str, with_name: str, count: int):
        """Trade Item with the villager npc, return the details of trade items and num."""
        url = Agent.get_url_prefix()[player_name] + "/post_trade"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "with_name": with_name,
            "count": count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def repairItem(player_name: str, item_name: str, material: str):
        """Repair Item in the Anvil"""
        url = Agent.get_url_prefix()[player_name] + "/post_repair"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "material": material.lower().replace(" ", "_"),
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def eat(player_name: str, item_name: str):
        """Eat Item"""
        url = Agent.get_url_prefix()[player_name] + "/post_eat"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def drink(player_name: str, item_name: str, count: int):
        """Drink Item"""
        url = Agent.get_url_prefix()[player_name] + "/post_drink"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "count": count,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def wear(player_name: str, slot: str, item_name: str):
        """Wear Item on Specific Slot"""
        url = Agent.get_url_prefix()[player_name] + "/post_wear"
        data = {
            "slot": slot,
            "item_name": item_name.lower().replace(" ", "_"),
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()
    
    @tool
    @timeit
    def openContainer(player_name: str, container_name: str, position=[0, 0, 0]):
        """Open the nearest but might not the correct 'chest' | 'container' | 'furnace' position is optional, return ('message': msg, 'status': True/False, 'data':[('name':name, 'count':count),...])"""
        if position != [0, 0, 0]:
            response = Agent._navigateTo(player_name, position[0], position[1], position[2])
            if response["status"] == False:
                return response
        url = Agent.get_url_prefix()[player_name] + "/post_open"
        data = {
            "item_name": container_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()


    @tool
    @timeit
    def fetchContainerContents(player_name: str, item_name: str, position=[0, 0, 0]):
        """Get the details of item_name 'chest' | 'container' | 'furnace', arg position is [x, y, z], return ('message': msg, 'status': True/False, 'data':[('name':name, 'count':count),...])"""
        if item_name not in ["chest", "inventory", "furnace", "container"]:
            return {'data': [], 'message': 'Failed item name not in ["chest", "inventory", "furnace", "container"]', 'status': False}
        if position != [0, 0, 0]:
            response = Agent._navigateTo(player_name, position[0], position[1], position[2])
            if response["status"] == False:
                return response
        url = Agent.get_url_prefix()[player_name] + "/post_open"
        data = {
            "item_name": item_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def closeContainer(player_name: str, item_name: str, position=[0, 0, 0]):
        """Close 'chest' | 'container' | 'furnace' position is optional."""
        if position != [0, 0, 0]:
            response = Agent._navigateTo(player_name, position[0], position[1], position[2])
            if response["status"] == False:
                return response
        url = Agent.get_url_prefix()[player_name] + "/post_close"
        data = {
            "item_name": item_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def ToggleAction(player_name: str, item_name: str, x: int, y: int, z: int):
        """open/close Gate, Lever, Press Button (pressure_plate need to stand on it, iron door need to be powered, they are not included), at Specific Position x y z"""
        if "plate" in item_name:
            return {'message': "pressure_plate need to stand on it", 'status': False}
        url = Agent.get_url_prefix()[player_name] + "/post_activate"
        data = {
            "item_name": item_name.lower().replace(" ", "_"),
            "x": x,
            "y": y,
            "z": z,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def mountEntity(player_name: str, entity_name: str):
        """Mount the Entity"""
        url = Agent.get_url_prefix()[player_name] + "/post_mount"
        data = {
            "entity_name": entity_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def dismountEntity(player_name: str):
        """Dismount the Entity"""
        url = Agent.get_url_prefix()[player_name] + "/post_dismount"
        response = requests.post(url, headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def rideEntity(player_name: str, entity_name: str):
        """Ride the Entity"""
        url = Agent.get_url_prefix()[player_name] + "/post_ride"
        data = {
            "entity_name": entity_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def disrideEntity(player_name: str):
        """Disride the Entity"""
        url = Agent.get_url_prefix()[player_name] + "/post_disride"
        response = requests.post(url, headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def talkTo(player_name: str, entity_name: str, message: str):
        """Talk to the Entity"""
        Agent._lookAt(player_name, entity_name)
        url = Agent.get_url_prefix()[player_name] + "/post_talk_to"
        data = {
            "entity_name": entity_name,
            "message": message,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()
    
    @tool
    @timeit
    def waitForFeedback(player_name: str, entity_name: str, seconds: int=20):
        """Wait for Feedback from other players, do not use this when you are in a hurry or you are expecting to end the conversation."""
        url = Agent.get_url_prefix()[player_name] + "/post_wait_for_feedback"
        data = {
            "entity_name": entity_name,
            "seconds": seconds,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def performMovement(player_name: str, action_name: str, seconds: int):
        """Perform Action jump forward back left right for Seconds"""
        url = Agent.get_url_prefix()[player_name] + "/post_action"
        data = {
            "action_name": action_name,
            "seconds": seconds,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def lookAt(player_name: str, name: str):
        """Look at Someone or Something"""
        url = Agent.get_url_prefix()[player_name] + "/post_look_at"
        data = {
            "name": name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    def _lookAt(player_name: str, name: str):
        """Look at Someone or Something"""
        url = Agent.get_url_prefix()[player_name] + "/post_look_at"
        data = {
            "name": name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def startFishing(player_name: str, fish_name: str):
        """Start Fishing"""
        url = Agent.get_url_prefix()[player_name] + "/post_start_fishing"
        data = {
            "fish_name": fish_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def stopFishing(player_name: str):
        """Stop Fishing"""
        url = Agent.get_url_prefix()[player_name] + "/post_stop_fishing"
        response = requests.post(url, headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def read(player_name: str, item_name: str):
        """Read Book or Sign neaby, return string details"""
        url = Agent.get_url_prefix()[player_name] + "/post_read"
        data = {
            "name": item_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def readPage(player_name: str, item_name: str, page: int):
        """Read Content from Book Page"""
        url = Agent.get_url_prefix()[player_name] + "/post_read_page"
        data = {
            "name": item_name,
            "page": page,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    @tool
    @timeit
    def write(player_name: str, item_name: str, content: str):
        """Write Content on Writable Book or Sign"""
        url = Agent.get_url_prefix()[player_name] + "/post_write"
        data = {
            "name": item_name,
            "content": content,
        }
        response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
        return response.json()

    def update_history(self, response):
        self.action_history.append(response)
        with open(".cache/meta_setting.json", "r") as f:
            config = json.load(f)
            task_name = config["task_name"]
        if not os.path.exists("result/" + task_name):
            os.mkdir(os.path.join("result/", task_name))
        root = os.path.join("result/", task_name)
        with open(os.path.join(root, f"{self.name}_history.json"), "w") as f:
            json.dump(self.action_history, f, indent=4)

    def step(self, instruction: str, actions=[], observations=[], player_name_list=[], max_try_turn=2, max_iterations=1, tools=[], recommended_actions=[]):
        # return the (action, observation), details.
        assert len(self.api_key_list) > 0, "Please set the api_key_list in Agent class."

        if "instruct" in self.model and "gpt" in self.model:
            from langchain.llms import OpenAI
            self.llm = OpenAI(model=self.model, temperature=0, max_tokens=256, openai_api_key=random.choice(Agent.api_key_list), base_url=Agent.base_url)
        elif "gpt" in self.model:
            from langchain.chat_models import ChatOpenAI
            self.llm = ChatOpenAI(model=self.model, temperature=0,  max_tokens=256, openai_api_key=random.choice(Agent.api_key_list), base_url=Agent.base_url)
        elif "glm" in self.model:
            from zhipu import ChatZhipuAI
            self.llm = ChatZhipuAI(model_name=self.model, temperature=0.01, api_key=random.choice(Agent.api_key_list))
        
        for act, obs in zip(actions, observations):
            instruction += f"\n{act['log']}\n{obs}"
        
        recommended_tools = []
        for action in recommended_actions:
            for tool in self.all_tools:
                if tool.name == action:
                    recommended_tools.append(tool)
        
        mix_tools = []
        for tool in self.tools:
            if tool not in recommended_tools:
                mix_tools.append(tool)
        
        mix_tools += recommended_tools

        while max_try_turn > 0:
            random.shuffle(self.tools)
            llmhandler = LLMHandler()
            agent = initialize_agent(
                tools=mix_tools,
                llm=self.llm,
                verbose=Agent.verbose,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                return_intermediate_steps=True,
                max_execution_time=120,  # seconds
                max_iterations=1,  # 决定了最大的迭代次数
                callback_manager=BaseCallbackManager(handlers=[llmhandler]),
            )
            agent.handle_parsing_errors = True
            response = None
            try:
                if len(player_name_list) == 0:
                    response = agent({"input": f"Your name is {self.name}.\n{instruction}"})
                else:
                    response = agent(
                        {"input": f"You should control {player_name_list} work together. \n{instruction}"})
                break
            except KeyboardInterrupt:
                logging.info("KeyboardInterrupt")
                raise KeyboardInterrupt
            except ConnectionError as e:
                logging.info(e)
                raise ConnectionError
            except ConnectionRefusedError as e:
                logging.info(e)
                raise ConnectionRefusedError
            except Exception as e:
                print(e)
                print("retrying...")
                time.sleep(1)
                max_try_turn -= 1

        if response is None:
            return (None, None), {"input": f"Your name is {self.name}.\n{instruction}", "action_list": [],
                                                "final_answer": "The task execute failed.", "chain_input": llmhandler.chain_input, "seralized_input": llmhandler.seralized_input}
        # print(response)
        # print(dumps(response, pretty=True),type(dumps(response, pretty=True)))
        action_list = []
        response = json.loads(dumps(response, pretty=True))
        for step in response["intermediate_steps"]:
            action_list.append({"action": step[0]["kwargs"], "feedback": step[1]})
        
        if len(action_list) == 0:
            return (None, None), {"input": f"Your name is {self.name}.\n{instruction}", "action_list": [],
                                                "final_answer": "The task execute failed.", "chain_input": llmhandler.chain_input, "seralized_input": llmhandler.seralized_input}
    

        final_answer = response["output"]
        # save the action_list and final_answer

        with open(f"data/history/{hash(response['input'])}.json", "w") as f:
            json.dump({"input": response["input"], "action_list": action_list, "final_answer": final_answer}, f,
                      indent=4)
        action = action_list[0]
        return (action['action'], action["feedback"]), {"input": response["input"], "action_list": action_list, "final_answer": final_answer}

    def run(self, instruction: str, player_name_list=[], max_try_turn=10, max_iterations=10, tools=[]):
        # print(f"Your name is {self.name}. \n{instruction}")
        assert len(self.api_key_list) > 0, "Please set the api_key_list in Agent class."
        # dynamic api key
        if "instruct" in self.model and "gpt" in self.model:
            from langchain.llms import OpenAI
            self.llm = OpenAI(model=self.model, temperature=0, max_tokens=256, openai_api_key=random.choice(Agent.api_key_list), base_url=Agent.base_url)
        elif "gpt" in self.model:
            from langchain.chat_models import ChatOpenAI
            self.llm = ChatOpenAI(model=self.model, temperature=0,  max_tokens=256, openai_api_key=random.choice(Agent.api_key_list), base_url=Agent.base_url)
        elif "gemini" in self.model:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.llm = ChatGoogleGenerativeAI(model=self.model, temperature=0, google_api_key=random.choice(Agent.api_key_list))
        elif "glm" in self.model:
            from zhipu import ChatZhipuAI
            self.llm = ChatZhipuAI(model_name=self.model, temperature=0.01, api_key=random.choice(Agent.api_key_list))
        
        # 这个地方是定义的agent的类型，初始化位置的agent没有被使用
        while max_try_turn > 0:
            random.shuffle(self.tools)
            llmhandler = LLMHandler()
            agent = initialize_agent(
                tools=self.tools if len(tools) == 0 else tools,
                llm=self.llm,
                verbose=Agent.verbose,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                return_intermediate_steps=True,
                max_execution_time=120,  # seconds
                max_iterations=max_iterations,  # 决定了最大的迭代次数
                callback_manager=BaseCallbackManager(handlers=[llmhandler]),
            )
            agent.handle_parsing_errors = True
            response = None
            try:
                with get_openai_callback() as cb:
                    start_time = time.time()
                    if len(player_name_list) == 0:
                        response = agent({"input": f"Your name is {self.name}.\n{instruction}"})
                    else:
                        response = agent(
                            {"input": f"You should control {player_name_list} work together. \n{instruction}"})
                    # print(llmhandler.chain_input)
                    # print(llmhandler.seralized_input)

                    end_time = time.time()
                    # save in pipeLine/tokens
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # if 'gpt' in Agent.model:
                    #     from env.utils import parse_token_text
                    #     token_usage = parse_token_text(cb)
                    #     try:
                    #         with open("data/tokens.json", "r") as f:
                    #             tokens = json.load(f)
                    #         tokens["dates"] = current_time
                    #         tokens["tokens_used"] += token_usage["tokens_used"]
                    #         tokens["prompt_tokens"] += token_usage["prompt_tokens"]
                    #         tokens["completion_tokens"] += token_usage["completion_tokens"]
                    #         tokens["successful_requests"] += token_usage["successful_requests"]
                    #         tokens["total_cost"] += token_usage["total_cost"]
                    #         tokens["action_cost"] += end_time - start_time
                    #         with open("data/tokens.json", "w") as f:
                    #             json.dump(tokens, f, indent=4)
                    #     except KeyboardInterrupt:
                    #         logging.info("KeyboardInterrupt")
                    #         raise KeyboardInterrupt
                    #     except Exception as e:
                    #         logging.info(e)
                break
            except KeyboardInterrupt:
                logging.info("KeyboardInterrupt")
                raise KeyboardInterrupt
            except ConnectionError as e:
                logging.info(e)
                raise ConnectionError
            except ConnectionRefusedError as e:
                logging.info(e)
                raise ConnectionRefusedError
            except Exception as e:
                print(e)
                print("retrying...")
                time.sleep(1)
                max_try_turn -= 1

        if max_turn == 0 or response is None:
            return "The task execute failed.", {"input": f"Your name is {self.name}.\n{instruction}", "action_list": [],
                                                "final_answer": "The task execute failed.", "chain_input": llmhandler.chain_input, "seralized_input": llmhandler.seralized_input}
        # print(response)
        # print(dumps(response, pretty=True),type(dumps(response, pretty=True)))
        action_list = []
        response = json.loads(dumps(response, pretty=True))
        for step in response["intermediate_steps"]:
            action_list.append({"action": step[0]["kwargs"], "feedback": step[1]})
        final_answer = response["output"]
        # save the action_list and final_answer

        with open(f"data/history/{hash(response['input'])}.json", "w") as f:
            json.dump({"input": response["input"], "action_list": action_list, "final_answer": final_answer}, f,
                      indent=4)
        self.update_history({"input": response["input"], "action_list": action_list, "final_answer": final_answer})
        return final_answer, {"input": response["input"], "action_list": action_list, "final_answer": final_answer}

    def chat(self, msg, async_tag=False):
        url = Agent.get_url_prefix()[self.name] + "/post_chat"
        data = {
            "msg": msg,
        }
        if async_tag:
            threading.Thread(target=requests.post, args=(url,),
                             kwargs={"data": json.dumps(data), "headers": Agent.headers}).start()
            return {}
        else:
            time.sleep(.05)
            response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
            return response.json()


if __name__ == "__main__":
    Agent.api_key_list = [
        ""
    ]
    Agent.model = "gpt-4-1106-preview"
    agent1 = Agent(name="Alice", local_port=5001, tools=[Agent.equipItem, Agent.startFishing])
    Agent.base_url = "https://api.chatanywhere.tech/v1"
    Agent.api_key_list = json.load(open("API_KEY_LIST", "r"))["AGENT_KEY"]
    Agent.launch(host="10.214.180.148", port=25565)
    Agent.ping("Alice")
    # url = Agent.get_url_prefix()["Alice"] + "/post_start_fishing"
    # data = {
    #         "fish_name": "cod",
    #     }
    # response = requests.post(url, data=json.dumps(data), headers=Agent.headers)
    # print(response.json())
    Prompt = "You are Alice, you have a fishing rod in your hand, cating some salmon."
    agent1.run(Prompt)
    # actions = []
    # observations = []
    # while True:
    #     (act, obs), detail = agent1.step(Prompt, actions=actions, observations=observations)
    #     if act == None:
    #         continue
    #     actions.append(act)
    #     observations.append(obs)
    #     input()
    