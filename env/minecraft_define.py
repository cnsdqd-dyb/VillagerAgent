import random
import time
import json
import os

class MinecraftLoader():
    def __init__(self, data:[dict], interval:float=0.1):
        self.data = data
        self.interval = interval

    def load(self, bot):
        for block in self.data:
            MinecraftBlockAttribute(block_dict=block).set_block(bot)
            time.sleep(self.interval)

class MinecraftBlockAttribute():
    def __init__(self, block=None, block_dict=None):
        self.name = None
        self.position = None
        self.type = None
        self.open = None
        self.facing = None
        self.face = None
        self.axis = None
        self.part = None
        self.hinge = None
        self.powered = None
        self.lock_key = None
        self.command = None
        self.merge_pos = None
        self.split_pos = []
        if block is not None:
            self.load(block)
        if block_dict is not None:
            self.load_dict(block_dict)

    def load(self, block):
        self.name = block.name
        self.position = [block.position.x, block.position.y, block.position.z]
        self.type = block.type
        self.open = block._properties["open"]
        self.facing = block._properties["facing"]
        self.face = block._properties["face"]
        self.axis = block._properties["axis"]
        self.part = block._properties["part"]
        self.hinge = block._properties["hinge"]
        self.powered = block._properties["powered"]

    def load_dict(self, block_dict):
        self.name = block_dict.get("name", None)
        self.position = block_dict.get("position", None)
        self.type = block_dict.get("type", None)
        self.open = block_dict.get("open", None)
        self.facing = block_dict.get("facing", None)
        self.face = block_dict.get("face", None)
        self.axis = block_dict.get("axis", None)
        self.part = block_dict.get("part", None)
        self.hinge = block_dict.get("hinge", None)
        self.powered = block_dict.get("powered", None)
        self.lock_key = block_dict.get("lock_key", None)
        self.command = block_dict.get("command", None)
        self.merge_pos = block_dict.get("merge_pos", None)
        self.split_pos = block_dict.get("split_pos", [])
    
    def satisfy(self, condition:dict):
        # print(condition)
        # print(self._to_dict())
        # 以位置为基准
        if "name" in condition.keys() and condition["name"] is not None:
            if condition["name"] != self.name:
                return False
        if "position" in condition.keys() and condition["position"] is not None:
            if condition["position"] != self.position:
                return False
        if "type" in condition.keys() and condition["type"] is not None:
            if condition["type"] != self.type:
                return False
        if "open" in condition.keys() and condition["open"] is not None:
            if condition["open"] != self.open:
                return False
        if "facing" in condition.keys() and condition["facing"] is not None:
            if condition["facing"] != self.facing:
                return False
        if "axis" in condition.keys() and condition["axis"] is not None:
            if condition["axis"] != self.axis:
                return False
        if "part" in condition.keys() and condition["part"] is not None:
            if condition["part"] != self.part:
                return False
        if "hinge" in condition.keys() and condition["hinge"] is not None:
            if condition["hinge"] != self.hinge:
                return False
        if "powered" in condition.keys() and condition["powered"] is not None:
            if condition["powered"] != self.powered:
                return False
        return True
    
    def _to_dict(self):
        return {
            "name": self.name,
            "position": self.position,
            "type": self.type,
            "open": self.open,
            "facing": self.facing,
            "face": self.face, 
            "axis": self.axis,
            "part": self.part,
            "hinge": self.hinge,
            "powered": self.powered,
            "lock_key": self.lock_key,
            "command": self.command,
            "merge_pos": self.merge_pos,
            "split_pos": self.split_pos,
        }
    
    def set_block(self, bot):
        attr = self._to_dict()
        if self.name == 'air':
            bot.chat(f"/setblock {self.position[0]} {self.position[1]} {self.position[2]} minecraft:air")
            # print(f"/setblock {self.position[0]} {self.position[1]} {self.position[2]} minecraft:air")
            return

        if "summon_" in self.name: 
            name = self.name.replace("summon_","")
            bot.chat(f'/summon {name} {self.position[0]} {self.position[1]} {self.position[2]}')
            # print(f'/summon {name} {self.position[0]} {self.position[1]} {self.position[2]}')
        else:
            meta_data = MinecraftBlockAttribute.get_metadata(attr)
            bot.chat(f"/setblock {self.position[0]} {self.position[1]} {self.position[2]} minecraft:{self.name}[{meta_data}]")
            # print(f"/setblock {self.position[0]} {self.position[1]} {self.position[2]} minecraft:{self.name}[{meta_data}]")
            if 'door' in self.name:
                bot.chat(f"/setblock {self.position[0]} {self.position[1]+1} {self.position[2]} minecraft:{self.name}[{meta_data},half=upper]")
                # print(f"/setblock {self.position[0]} {self.position[1]+1} {self.position[2]} minecraft:{self.name}[{meta_data},half=upper]")
            if "lock_key" in attr.keys() and attr["lock_key"] is not None:
                bot.chat(f"/data merge block {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} {{Lock:{attr['lock_key']}}}")
                # print(f"/data merge block {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} {{Lock:{attr['lock_key']}}}")

        if "command" in attr.keys() and attr["command"] is not None:
            if '_split_pos_' in attr["command"] and attr["split_pos"] is not None:
                attr["command"] = attr["command"].replace(f'_split_pos_', f'{attr["split_pos"][0]} {attr["split_pos"][1]} {attr["split_pos"][2]}')
                for i, split_pos in enumerate(attr["split_pos"]):
                    attr["command"] = attr["command"].replace(f'_split_pos_', f'{split_pos[0]} {split_pos[1]} {split_pos[2]}')
                    
                    if '_position_' in attr["command"]:
                        attr["command"] = attr["command"].replace('_position_', f'x={attr["position"][0]},y={attr["position"][1]},z={attr["position"][2]}')
                    if '_merge_pos_' in attr["command"] and attr["merge_pos"] is not None:
                        attr["command"] = attr["command"].replace('_merge_pos_', f'{attr["merge_pos"][0]} {attr["merge_pos"][1]} {attr["merge_pos"][2]}')
                    if '_pos_' in attr["command"]:
                        attr["command"] = attr["command"].replace('_pos_', f' {attr["position"][0]} {attr["position"][1]} {attr["position"][2]} ')
                    
                    bot.chat(attr["command"])
                    # print(attr["command"])
            else:
                
                if '_position_' in attr["command"]:
                    attr["command"] = attr["command"].replace('_position_', f'x={attr["position"][0]},y={attr["position"][1]},z={attr["position"][2]}')
                if '_merge_pos_' in attr["command"] and attr["merge_pos"] is not None:
                    attr["command"] = attr["command"].replace('_merge_pos_', f'{attr["merge_pos"][0]} {attr["merge_pos"][1]} {attr["merge_pos"][2]}')
                if '_pos_' in attr["command"]:
                    attr["command"] = attr["command"].replace('_pos_', f'{attr["position"][0]} {attr["position"][1]} {attr["position"][2]}')
                bot.chat(attr["command"])
                # print(attr["command"])

    def get_metadata(attr) -> str:
        meta_data = ""
        if "open" in attr.keys() and attr["open"] is not None:
            if attr["open"]:
                meta_data += f",open=true"
            else:
                meta_data += f",open=false"
        if "facing" in attr.keys() and attr["facing"] is not None:
            meta_data += f",facing={attr['facing']}"
        if "face" in attr.keys() and attr["face"] is not None:
            meta_data += f",face={attr['face']}"
        if "axis" in attr.keys() and attr["axis"] is not None:
            meta_data += f",axis={attr['axis']}"
        if "part" in attr.keys() and attr["part"] is not None:
            meta_data += f",part={attr['part']}"
        if "hinge" in attr.keys() and attr["hinge"] is not None:
            meta_data += f",hinge={attr['hinge']}"
        if "powered" in attr.keys() and attr["powered"] is not None:
            if attr["powered"]:
                meta_data += f",powered=true"
            else:
                meta_data += f",powered=false"

        meta_data = meta_data[1:]
        return meta_data
        
    def modify_block(bot, Vec3, attr:dict):
        b = bot.blockAt(Vec3(attr["position"][0], attr["position"][1], attr["position"][2]))
        
        if "command" in attr.keys() and attr["command"] is not None:
            if '_split_pos_' in attr["command"] and attr["split_pos"] is not None:
                for i, split_pos in enumerate(attr["split_pos"]):
                    _attr = attr.copy()
                    _attr["command"] = _attr["command"].replace(f'_split_pos_', f'{split_pos[0]} {split_pos[1]} {split_pos[2]}')
                    
                    if '_position_' in _attr["command"]:
                        _attr["command"] = _attr["command"].replace('_position_', f'x={_attr["position"][0]},y={_attr["position"][1]},z={_attr["position"][2]}')
                    if '_merge_pos_' in _attr["command"] and _attr["merge_pos"] is not None:
                        _attr["command"] = _attr["command"].replace('_merge_pos_', f'{_attr["merge_pos"][0]} {_attr["merge_pos"][1]} {_attr["merge_pos"][2]}')
                    if '_pos_' in _attr["command"]:
                        _attr["command"] = _attr["command"].replace('_pos_', f' {_attr["position"][0]} {_attr["position"][1]} {_attr["position"][2]} ')
                    
                    bot.chat(_attr["command"])
                    # print(_attr["command"])
            else:
                if '_position_' in attr["command"]:
                    attr["command"] = attr["command"].replace('_position_', f'x={attr["position"][0]},y={attr["position"][1]},z={attr["position"][2]}')
                if '_merge_pos_' in attr["command"] and attr["merge_pos"] is not None:
                    attr["command"] = attr["command"].replace('_merge_pos_', f'{attr["merge_pos"][0]} {attr["merge_pos"][1]} {attr["merge_pos"][2]}')
                if '_pos_' in attr["command"]:
                    attr["command"] = attr["command"].replace('_pos_', f'{attr["position"][0]} {attr["position"][1]} {attr["position"][2]}')
                    
                bot.chat(attr["command"])
                # print(attr["command"])
        if MinecraftBlockAttribute(block=b).satisfy(attr):
            return
        meta_data = MinecraftBlockAttribute.get_metadata(attr)
        if "air" in attr["name"]:
            bot.chat(f"/setblock {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} minecraft:air")
            # print(f"/setblock {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} minecraft:air")
        if "door" in attr["name"]:
            bot.chat(f"/setblock {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} minecraft:air")
            # print(f"/setblock {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} minecraft:air")
        bot.chat(f"/setblock {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} minecraft:{attr['name']}[{meta_data}]")
        # print(f"/setblock {attr['position'][0]} {attr['position'][1]} {attr['position'][2]} minecraft:{attr['name']}[{meta_data}]")
        if 'door' in attr["name"]:
            bot.chat(f"/setblock {attr['position'][0]} {attr['position'][1]+1} {attr['position'][2]} minecraft:{attr['name']}[{meta_data},half=upper]")
            # print(f"/setblock {attr['position'][0]} {attr['position'][1]+1} {attr['position'][2]} minecraft:{attr['name']}[{meta_data},half=upper]")
            # /give @a[x=72,y=-60,z=135,distance=..1] minecraft:iron_sword{display:{Name:'{"text":"key"}'}}

class MinecraftEvent():
    def __init__(self, bot, Vec3, condition:[dict], effect:[dict], wait_interval:float=-1, activate_duration:float=-1, type:str="and"):
        # wait_interval: 与运算的每个激活等待时间
        # activate_duration: 激活持续时间，-1为无限
        # type: and, or
        
        self.condition = condition
        self.effect = effect
        self.origin_state = []
        self.bot = bot
        self.Vec3 = Vec3
        self.activate_duration = activate_duration
        self.wait_interval = wait_interval
        self.state_dict = {}
        self.time_dict = {}
        self.activate_time = time.time() - 600
        for condition in self.condition:
            self.state_dict[str(condition["position"])] = False
        # print("self.state_dict" ,self.state_dict)
        # print(self.condition)
        self.current_max_satisfy_num = 0

        for condition in self.condition:
            self.time_dict[str(condition["position"])] = time.time() - 600
        self.type = type
        
        # add activate mode # 电平触发，边沿触发，脉冲触发
        for condition in self.condition:
            if "activate_mode" not in condition.keys():
                condition["activate_mode"] = "level"
            assert condition["activate_mode"] in ["level", "pulse"], "activate_mode must be one of level, pulse"

            if condition["activate_mode"] == "pulse":
                # 设定持续判定时间
                if "duration" not in condition.keys():
                    condition["duration"] = 3 
                    # 这意味着对于边沿触发，切换后的3s内被认为是有效的
                    # 对于脉冲触发，切换状态时间应该小于3s，切换后的1s内被认为是有效的

                condition["mid_time"] = time.time() - 600# 脉冲触发的中间状态

            condition["last_time"] = time.time() - 600 # 上一次判定的时间
        
        # 对影响对象存储原始状态
        for effect in self.effect:
            b = bot.blockAt(Vec3(effect["position"][0], effect["position"][1], effect["position"][2]))
            self.origin_state.append(MinecraftBlockAttribute(block=b)._to_dict())


    def event_update(self):
        bot = self.bot
        Vec3 = self.Vec3

        satisty_num = 0
        if self.activate_duration > 0 and self.activate_time + self.activate_duration > time.time():
            return True
        else:
            for condition in self.condition:
                self.time_dict[str(condition["position"])] = time.time() - 600
                self.state_dict[str(condition["position"])] = False
            self.activate_time = time.time() - 600

        for condition in self.condition:
            block = bot.blockAt(Vec3(condition["position"][0], condition["position"][1], condition["position"][2]))
            if condition["activate_mode"] == "level":
                result = MinecraftBlockAttribute(block=block).satisfy(condition)
                self.state_dict[str(condition["position"])] = result
                if result:
                    self.time_dict[str(condition["position"])] = time.time()
                    satisty_num += 1

            elif condition["activate_mode"] == "pulse":
                if MinecraftBlockAttribute(block=block).satisfy(condition):
                    if time.time() - condition["last_time"] < condition["duration"]:
                        condition["mid_time"] = time.time()
                else:
                    condition["last_time"] = time.time()

                if not MinecraftBlockAttribute(block=block).satisfy(condition):
                    if time.time() - condition["mid_time"] < condition["duration"]:
                        condition["mid_time"] = time.time() - 600
                        condition["last_time"] = time.time() - 600
                        self.state_dict[str(condition["position"])] = not self.state_dict[str(condition["position"])]
                        if self.state_dict[str(condition["position"])]:
                            self.time_dict[str(condition["position"])] = time.time()
                            satisty_num += 1
            else:
                assert False, "activate_mode must be one of level, pulse"
        
        if satisty_num > self.current_max_satisfy_num:
            self.current_max_satisfy_num = satisty_num
            

        if self.type == "and":
            toggle = True
            for condition in self.condition:
                if not self.state_dict[str(condition["position"])]:
                    toggle = False
                    break
        else:
            toggle = False
            for condition in self.condition:
                if self.state_dict[str(condition["position"])]:
                    toggle = True
                    break

        # if any(self.state_dict.values()):
        #     print(self.state_dict)
        # print(self.state_dict)
        
        if toggle:
            self.activate_time = time.time()
            for effect in self.effect:
                MinecraftBlockAttribute.modify_block(bot, Vec3, effect)

            return True
        
        else:
            for i, effect in enumerate(self.effect):
                # 如果effect在条件中存在不允许直接修改
                if effect["position"] in [condition["position"] for condition in self.condition]:
                    continue
                MinecraftBlockAttribute.modify_block(bot, Vec3, self.origin_state[i])

            if self.wait_interval > 0:
                for condition in self.condition:
                    if self.time_dict[str(condition["position"])] + self.wait_interval < time.time():
                        self.state_dict[str(condition["position"])] = False
            return False
        
class AtomTask:
    def __init__(self, bot, Vec3, init:[dict], condition:[dict], effect:[dict], bias=[0,0,0], in_item:{}={}, out_item:{}={},
                 split=False,merge=False,same_room=True, activate_duration:float=10, score=1,
                 type_:str="and", room_height:int=3, room_width:int=3, wall_width:int=1, wait_interval:float=4, min_player:int=1,
                 task_description:str=""):
        self.init = init
        self.condition = condition
        self.effect = effect
        self.room_height = room_height
        self.room_width = room_width
        self.wall_width = wall_width
        self.wait_interval = wait_interval
        self.min_player = min_player
        self.activate_duration = activate_duration
        self.type = type_
        self.bias = bias
        self.task_description = task_description
        self.center = None

        self.init_data_list = []
        self.condition_data_list = []
        self.effect_data_list = []

        self.bot = bot
        self.Vec3 = Vec3

        self.events = None
        self.final_event = None
        self.in_item = in_item
        self.out_item = out_item
        self.split=split
        self.merge=merge
        self.same_room=same_room
        self.condition_repeat_num = None
        self.merge_pos = None
        self.split_pos = []
        self.score = score
        self.current_score = 0

        self.done = False
        self.feedback = []

        self._current_max_condition_num = 0 # 当前房间完成的最大条件数
    
    def export_cache(self):
        return {
            "effect": self.effect,
            "task_description": self.task_description,
            "feedback": self.feedback,
            "center": self.center,
            "done": self.done,
            "state": self.json_to_string(),
        }

    def json_to_string(self):
        feedback_str = "Around you, the key activated blocks are: "
        for feedback in self.feedback:
            feedback_str += f"a {feedback['name']} block set at position {feedback['position']}"
            if "powered" in feedback.keys() and feedback['powered']:
                feedback_str += " powered. "
            if "open" in feedback.keys() and feedback['open']:
                feedback_str += " open. "
        # for condition in self.condition:
        #     if condition["position"] not in [feedback["position"] for feedback in self.feedback]:
        #         feedback_str += f"a {condition['name']} block set at position {condition['position']}"
        #         if "powered" in condition.keys() and condition['powered']:
        #             feedback_str += " powered. "
        #         if "open" in condition.keys() and condition['open']:
        #             feedback_str += " open. "
        if feedback_str == "Around you, the activated blocks are: ":
            feedback_str = "Around you, there is no activated blocks. "

        if self.done:
            if self.merge or self.split:
                feedback_str += " You have done the task in this room. "
            else:
                feedback_str += f" You have done the task in this room. Move to x={self.center[0]}, y={self.center[1]}, z={self.center[2]+6} to continue. "
        center_str = f"You are at task room {self.center}. "

        return feedback_str + center_str
    
    def export_json(self):
        return {
            "init": self.init,
            "condition": self.condition,
            "effect": self.effect,
            "room_height": self.room_height,
            "room_width": self.room_width,
            "wall_width": self.wall_width,
            "wait_interval": self.wait_interval,
            "min_player": self.min_player,
            "activate_duration": self.activate_duration,
            "type": self.type,
            "bias": self.bias,
            "task_description": self.task_description,
            "in_item": self.in_item,
            "out_item": self.out_item,
            "split": self.split,
            "merge": self.merge,
            "same_room": self.same_room,
            "condition_repeat_num": self.condition_repeat_num,
            "merge_pos": self.merge_pos,
            "split_pos": self.split_pos,
            "score": self.score,
        }
    
    def update_local_cache(self):
        if os.path.exists(".cache/env.cache"):
            with open(".cache/env.cache", "r") as f:
                cache = json.load(f)
        else:
            cache = []
        
        # 以center为key
        for i, item in enumerate(cache):
            if item["center"] == self.center:
                cache[i] = self.export_cache()
                break
        else:
            cache.append(self.export_cache())

        with open(".cache/env.cache", "w") as f:
            json.dump(cache, f, indent=4)

    def load_json(self, json_data):
        self.init = json_data["init"]
        self.condition = json_data["condition"]
        self.effect = json_data["effect"]
        self.room_height = json_data["room_height"]
        self.room_width = json_data["room_width"]
        self.wall_width = json_data["wall_width"]
        self.wait_interval = json_data["wait_interval"]
        self.activate_duration = json_data["activate_duration"]
        self.type = json_data["type"]
        self.bias = json_data["bias"]
        self.task_description = json_data["task_description"]
        self.in_item = json_data["in_item"]
        self.out_item = json_data["out_item"]
        self.split = json_data["split"]
        self.merge = json_data["merge"]
        self.same_room = json_data["same_room"]
        self.condition_repeat_num = json_data["condition_repeat_num"]
        self.merge_pos = json_data["merge_pos"]
        self.split_pos = json_data["split_pos"]
        self.score = json_data["score"]

    def copy(self):
        task = AtomTask(self.bot, self.Vec3, self.init, self.condition, self.effect, self.bias, self.in_item, self.out_item, self.split, self.merge, self.same_room,
                        self.activate_duration, self.score, self.type, self.room_height, self.room_width, self.wall_width, self.wait_interval, self.min_player, self.task_description)
        task.room_height = self.room_height
        task.room_width = self.room_width
        task.wall_width = self.wall_width   
        task.wait_interval = self.wait_interval
        task.min_player = self.min_player
        task.activate_duration = self.activate_duration
        task.type = self.type
        task.center = self.center
        task.init_data_list = self.init_data_list
        task.condition_data_list = self.condition_data_list
        task.effect_data_list = self.effect_data_list
        task.events = self.events
        task.final_event = self.final_event
        task.condition_repeat_num = self.condition_repeat_num
        task.split = self.split
        task.merge = self.merge
        task.same_room = self.same_room

        task.merge_pos = self.merge_pos
        task.split_pos = self.split_pos

        return task
    
    def generate(self):

        for effect in self.effect:
            effect["merge_pos"] = self.merge_pos
            effect["split_pos"] = self.split_pos

        init_data_list = []
        condition_data_list = []
        effect_data_list = []
        for init in self.init:
            if "random" in init.keys() and init["random"] != False:
                # 分了两种情况，一个是 有值，一个是init["random"]不是bool 是 int
                condition_repeat_num = init["random"] if type(init["random"]) == int else self.condition_repeat_num
                # 如果 init["random"] 是 int 并且是负数，那么就是condition_repeat_num + init["random"]
                if condition_repeat_num < 0:
                    condition_repeat_num = self.condition_repeat_num + init["random"]
                for i in range(condition_repeat_num):
                    init_data = init.copy()
                    if "random" in init.keys():
                        init_data.pop("random")
                    for condition in self.condition:
                        if condition["position"] == init["position"]:
                            condition_data = condition.copy()
                    while True:
                        position = [random.randint(self.center[0] - self.room_width // 2, self.center[0] + self.room_width // 2), self.center[1], random.randint(self.center[2] - self.room_width // 2, self.center[2] + self.room_width // 2)]
                        if position not in [item["position"] for item in init_data_list]:
                            init_data["position"] = position
                            init_data_list.append(init_data)

                            for condition in self.condition:
                                if condition["position"] == init["position"]:
                                    condition_data = condition.copy()
                                    condition_data["position"] = position
                                    condition_data_list.append(condition_data)

                            for effect in self.effect:
                                if effect["position"] == init["position"]:
                                    effect_data = effect.copy()
                                    effect_data["position"] = position
                                    for key in init_data.keys():
                                        if key not in effect_data.keys():
                                            effect_data[key] = init_data[key]
                                    effect_data_list.append(effect_data)
                            break
            else:
                init_data = init.copy()
                if "random" in init.keys():
                    init_data.pop("random")
                init_data["position"] = [self.center[0] + init_data["position"][0], self.center[1] + init_data["position"][1], self.center[2] + init_data["position"][2]]
                init_data_list.append(init_data)

                for condition in self.condition:
                    if condition["position"] == init["position"]:
                        condition_data = condition.copy()
                        condition_data["position"] = init_data["position"]
                        condition_data_list.append(condition_data)
                
                for effect in self.effect:
                    if effect["position"] == init["position"]:
                        effect_data = effect.copy()
                        # 将init_data中有而effect_data中没有的属性添加到effect_data中
                        effect_data["position"] = init_data["position"]
                        for key in init_data.keys():
                            if key not in effect_data.keys():
                                effect_data[key] = init_data[key]
                        effect_data_list.append(effect_data)
            
            for condition in self.condition:
                if condition["position"] in [init["position"] for init in self.init]:
                    continue
                condition_data = condition.copy()
                condition_data["position"] = [self.center[0] + condition_data["position"][0], self.center[1] + condition_data["position"][1], self.center[2] + condition_data["position"][2]]
                if condition_data["position"] not in [c["position"] for c in condition_data_list]:
                    condition_data_list.append(condition_data)
                    
            for effect in self.effect:
                if effect["position"] in [init["position"] for init in self.init]:
                    continue
                effect_data = effect.copy()
                effect_data["position"] = [self.center[0] + effect_data["position"][0], self.center[1] + effect_data["position"][1], self.center[2] + effect_data["position"][2]]
                if effect_data["position"] not in [e["position"] for e in effect_data_list]:
                    effect_data_list.append(effect_data)


        self.init_data_list = init_data_list
        self.condition_data_list = condition_data_list
        self.effect_data_list = effect_data_list
        # print("=" * 20)
        # print(self.init_data_list)
        # print(self.condition_data_list)
        # print(self.effect_data_list)
        # print("=" * 20)
        self.update_local_cache()

        return init_data_list, condition_data_list, effect_data_list
    
    def load(self):
        x_min = self.center[0] - self.room_width - self.wall_width
        x_max = self.center[0] + self.room_width + self.wall_width
        z_min = self.center[2] - self.room_width - self.wall_width
        z_max = self.center[2] + self.room_width + self.wall_width

        # add door and wall
        self.bot.chat(f"/fill {x_min} {self.center[1]} {z_min} {x_max} {self.center[1] + self.room_height} {z_min-1} stone_brick_wall")
        
        self.bot.chat(f"/fill {x_min} {self.center[1]} {z_min} {x_max} {self.center[1] + self.room_height} {z_min} stone_brick_wall")
        self.bot.chat(f"/fill {self.center[0]} {self.center[1]} {z_min} {self.center[0]} {self.center[1] + 2} {z_min} air")

        self.bot.chat(f"/fill {x_min} {self.center[1]} {z_max} {x_max} {self.center[1] + self.room_height} {z_max} stone_brick_wall")
        self.bot.chat(f"/fill {x_min} {self.center[1]} {z_min} {x_min} {self.center[1] + self.room_height + 1} {z_max} stone_brick_wall")
        self.bot.chat(f"/fill {x_min-1} {self.center[1]} {z_min} {x_min} {self.center[1] + self.room_height + 1} {z_max} stone_brick_wall")
        self.bot.chat(f"/fill {x_max} {self.center[1]} {z_min} {x_max} {self.center[1] + self.room_height + 1} {z_max} stone_brick_wall")
        self.bot.chat(f"/fill {x_max+1} {self.center[1]} {z_min} {x_max} {self.center[1] + self.room_height + 1} {z_max} stone_brick_wall")
        time.sleep(.1)
        self.bot.chat(f"/setblock {x_min} {self.center[1] + self.room_height + 2} {z_min} red_banner[rotation=8]")
        self.bot.chat(f"/setblock {x_max} {self.center[1] + self.room_height + 2} {z_min} red_banner[rotation=8]")
        time.sleep(.1)
        self.bot.chat(f"/setblock {x_max} {self.center[1] + self.room_height + 2} {z_min} red_banner[rotation=8]")
        self.bot.chat(f"/fill {x_min} {self.center[1]} {z_min+2} {x_min} {self.center[1] + 1} {z_max-2} iron_bars")
        self.bot.chat(f"/fill {x_max} {self.center[1]} {z_min+2} {x_max} {self.center[1] + 1} {z_max-2} iron_bars")
        self.bot.chat(f"/fill {self.center[0]} {self.center[1]} {z_max} {self.center[0]} {self.center[1] + 2} {z_max} iron_bars")

        # add a sign to show the task
        hint = self.hint()
        # try:
        #     self.bot.chat(f"/setblock {self.center[0]} {self.center[1] + self.room_height -1} {self.center[2]} jungle_wall_sign[facing=north]{{Text1:\"{{\\\"text\\\":\\\"{self.task_description}\\\"}}\",Text2:\"{{\\\"text\\\":\\\"{hint}\\\"}}\"}}")
        # except Exception as e:
        #     print(e)

        # 由于字数限制，改写到本地


        # print(f"/setblock {self.center[0]} {self.center[1] + self.room_height -1} {self.center[2]} jungle_wall_sign[facing=north]{{Text1:\"{{\\\"text\\\":\\\"{self.task_description}\\\"}}\",Text2:\"{{\\\"text\\\":\\\"{hint}\\\"}}\"}}")
        self.generate()
        
        MinecraftLoader(self.init_data_list).load(self.bot)
    
    def hint(self) -> str:
        hint = ""
        if self.merge:
            hint += "after you finish this task, you need to merge the team"
        elif self.split:
            hint += "you need to split the team to finish the task"
        elif self.same_room:
            hint += "you need to finish the task in this room"
        else:
            hint += "you need to try to help each other to finish this task"

        return hint
    def clear(self):
        # clear
        x_min = self.center[0] - self.room_width * 2 - self.wall_width
        x_max = self.center[0] + self.room_width * 2 + self.wall_width
        z_min = self.center[2] - self.room_width - self.wall_width
        z_max = self.center[2] + self.room_width + self.wall_width



        self.bot.chat(f"/fill {x_min} {self.center[1]} {z_min} {x_max} {self.center[1] + self.room_height} {z_max} air")
        self.bot.chat(f"/fill {x_min + 2} {self.center[1]-1} {z_min} {x_max - 2} {self.center[1]-1} {z_max} cobblestone")
        self.bot.chat(f"/fill {x_min + 3} {self.center[1] + self.room_height + 1} {z_min} {x_max - 3} {self.center[1] + self.room_height + 1} {z_max} white_stained_glass")
        # print(f"/fill {x_min} {self.center[1]} {z_min} {x_max} {self.center[1] + self.room_height} {z_max} air")
        # print(f"/fill {x_min} {self.center[1]-1} {z_min} {x_max} {self.center[1]-1} {z_max} cobblestone")

    def event_update(self):
        if self.events is None:
            #如果condition中存在sub_event字段，那么需要将condition中的subevent字段对应effect中的subevent字段转换为event
            sub_event_keys = []
            for condition in self.condition_data_list:
                if "sub_event" in condition.keys():
                    sub_event_keys.append(condition["sub_event"])
            if len(sub_event_keys) > 0:
                sub_event_keys = list(set(sub_event_keys))
                self.events = []
                for sub_event_key in sub_event_keys:
                    sub_condition = []
                    sub_effect = []
                    for condition in self.condition_data_list:
                        # print(f"condition: {condition}, sub_event: {sub_event_key}")
                        if "sub_event" in condition.keys() and condition["sub_event"] == sub_event_key:
                            sub_condition.append(condition)
                    for effect in self.effect_data_list:
                        if "sub_event" in effect.keys() and effect["sub_event"] == sub_event_key:
                            sub_effect.append(effect)
                    if sub_event_key == "final": #
                        self.final_event = MinecraftEvent(self.bot, self.Vec3, sub_condition, sub_effect, wait_interval=self.wait_interval, activate_duration=self.activate_duration, type=self.type)
                    else:
                        self.events.append(MinecraftEvent(self.bot, self.Vec3, sub_condition, sub_effect, wait_interval=self.wait_interval, activate_duration=self.activate_duration, type=self.type))
            else:
                self.events = [MinecraftEvent(self.bot, self.Vec3, self.condition_data_list, self.effect_data_list, 
                                        wait_interval=self.wait_interval, activate_duration=self.activate_duration, type=self.type)]
        
        flag = True
        self.feedback = []
        condition_done = 0
        for event in self.events:
            res = event.event_update()

            for condition in event.condition:
                if event.state_dict[str(condition["position"])]:
                    self.feedback.append(condition)
                    condition_done += 1

            if not res:
                flag = False
        
        if condition_done > self._current_max_condition_num:
            self._current_max_condition_num = condition_done

        if self.final_event is not None:
            flag = self.final_event.event_update()
       
        if flag:
            # 写入 data/score.json
            with open("data/score.json", "r") as f:
                score_dict = json.load(f)
                if str(self) not in score_dict.keys():
                    score_dict[str(self)] = {"score": 1, "type":self.type, "task_description":self.task_description, 
                    "repeat_num":self.condition_repeat_num, "condition_num":len(self.condition), "activate_duration":self.activate_duration,
                    "current_time":time.time()}
            with open("data/score.json", "w") as f:
                json.dump(score_dict, f, indent=4)

            self.done = True
        else:
            total_condition = 0
            done_condition = 0
            for event in self.events:
                total_condition += len(event.state_dict)

                done_condition += sum([1 for state in event.state_dict.values() if state])
            if self.final_event is not None:
                total_condition += len(self.final_event.state_dict)
                done_condition += sum([1 for state in self.final_event.state_dict.values() if state])
            score = (done_condition / total_condition)
            self.current_score = max(self.current_score, score)
            # 写入 data/score.json
            with open("data/score.json", "r") as f:
                score_dict = json.load(f)
                if str(self) not in score_dict.keys():
                    score_dict[str(self)] = {"score":self.current_score, "type":self.type, "task_description":self.task_description, 
                    "repeat_num":self.condition_repeat_num, "condition_num":len(self.condition), "activate_duration":self.activate_duration,
                    "current_time":time.time()}
            with open("data/score.json", "w") as f:
                json.dump(score_dict, f, indent=4)

        self.update_local_cache()

    def __str__(self) -> str:
        return f"---\ninit: {self.init}\ncondition: {self.condition}\neffect: {self.effect}\ncenter: {self.center}\n---"
    
class StateAgent:
    def __init__(self, idx):
        self.idx = idx
        self.inventory = {}
        self.position = [0, 0, 0]
        self.room = None
    
    def load(self, bot):
        if self.room is None:
            bot.chat(f"warning: agent {self.idx} has no start room")
            return
        bot.chat(f'/tp @r[distance=..3,gamemode=survival] {self.room[0]} {self.room[1]} {self.room[2]-3}')
        # print(f"/tp @r[distance=..3,gamemode=survival] {self.room[0]} {self.room[1]} {self.room[2]-3}")
        for key, value in self.inventory.items():
            bot.chat(f"/give @a[distance=..10,gamemode=survival] minecraft:{key} {value + 2}")
            time.sleep(.05)
            # print(f"/give @a[distance=..10,gamemode=survival] minecraft:{key} {value + 2}")
    
    
    def __str__(self) -> str:
        return f"---\nidx: {self.idx}\ninventory: {self.inventory}\nposition: {self.room}\nstart_room: {self.room}\n---"

class StateTree:
    def __init__(self, bot, Vec3, agent_num, bias = [110, -60, 140], file_path:str="data/escape_atom.json", max_task_num:int=10, max_time:float=1000, seed:int=0):
        self.agents = [StateAgent(i) for i in range(agent_num)]
        self.task_list = []
        self.atom_task_list = []
        self.max_task_num = max_task_num
        self.bias = bias
        self.bot = bot
        self.Vec3 = Vec3
        self.max_time = max_time
        self.start_time = time.time()
        self.complexity = 0
        self.seed = seed
        random.seed(seed)
        while True:
            self.load_atom_task_from_json(file_path)
            # 根据种子对任务重新排序
            random.shuffle(self.atom_task_list)
            for _ in range(self.max_task_num):
                self.generate()
            task_json_list = []
            for task in self.task_list:
                # print(task.export_json())
                task_json_list.append(task.export_json())

            if all(agent.room is not None for agent in self.agents):
                break

        with open("data/score.json", "w") as f:
            start_time = time.localtime()
            json.dump({"start_time": start_time}, f)

        with open(".cache/task.cache", "w") as f:
            json.dump(task_json_list, f, indent=4)

    
    def load_atom_task_from_json(self,  file_path:str="data/escape_atom.json"):
        data = load_atom_from_json(file_path)
        for item in data:
            if "in" not in item.keys():
                item["in"] = {}
            if "out" not in item.keys():
                item["out"] = {}
            if "activate_duration" not in item.keys():
                item["activate_duration"] = 300
            if "split" not in item.keys():
                item["split"] = False
            if "merge" not in item.keys():
                item["merge"] = False
            if "same_room" not in item.keys():
                item["same_room"] = True    
            if "room_height" not in item.keys():
                item["room_height"] = 3
            if "room_width" not in item.keys():
                item["room_width"] = 3
            if "wall_width" not in item.keys():
                item["wall_width"] = 1
            if "score" not in item.keys():
                item["score"] = 1
            if "wait_interval" not in item.keys():
                item["wait_interval"] = 4
            if "type" not in item.keys():
                item["type"] = "and"
            if "task_description" not in item.keys():
                item["task_description"] = ""
            if "min_player" not in item.keys():
                item["min_player"] = 1

            atom_task = AtomTask(self.bot, self.Vec3, init=item["init"], condition=item["condition"], effect=item["effect"], 
                                bias=self.bias, in_item=item["in"], out_item=item["out"], activate_duration=item["activate_duration"],
                                split=item["split"], merge=item["merge"], same_room=item["same_room"],
                                room_height=item["room_height"], room_width=item["room_width"], wall_width=item["wall_width"],
                                score=item["score"], wait_interval=item["wait_interval"], min_player=item["min_player"],
                                type_=item["type"], task_description=item["task_description"])
            self.atom_task_list.append(atom_task)

    def load(self, bot):
        room_width = 15 # 固定值是为了统一清除
        room_height = 6 # 固定值是为了统一清除
        wall_width = 1
        self.bot.chat("/kill @e[type=!minecraft:player]")
        self.bot.chat("/kill @e[type=!minecraft:player]")

        for i in range(self.max_task_num):
            for j in range(-len(self.agents)//2, len(self.agents)//2 + 1):
                center = [self.bias[0] + j * room_width, self.bias[1], self.bias[2] - i * room_width]
                # center = [self.bias[0], self.bias[1], self.bias[2] - 3 * i * room_width - 3 * room_width // 2]
                x_min = center[0] - room_width - wall_width 
                x_max = center[0] + room_width + wall_width 
                z_min = center[2] - room_width - wall_width 
                z_max = center[2] + room_width + wall_width 

                self.bot.chat(f"/fill {x_min} {center[1]} {z_min} {x_max} {center[1] + room_height} {z_max} air")
                self.bot.chat(f"/fill {x_min} {center[1]-1} {z_min} {x_max} {center[1]-1} {z_max} grass_block")

        for task in self.task_list:
            task.clear()
        
        for task in self.task_list:
            task.load()
        
        time.sleep(1)
        bot.chat(f"/kill @e[type=!player]")
        time.sleep(.1)
        bot.chat(f"/kill @e[type=item]")
        time.sleep(.1)

        self.bot.chat("/tp @a[gamemode=survival] @s")
        for agent in self.agents:
            agent.load(self.bot)
    
    def update(self):
        with open("data/score.json", "r") as f:
            if "max_time" in json.load(f).keys():
                return True
        
        all_done = True
        for task in self.task_list:
            if not task.done:
                all_done = False
                break

        if all_done:
            with open("data/score.json", "r") as f:
                score_dict = json.load(f)
                score_dict["max_time"] = self.max_time
                score_dict["end_time"] = time.localtime()
            with open("data/score.json", "w") as f:
                json.dump(score_dict, f, indent=4)
            return True

        if time.time() - self.start_time > self.max_time:
            with open("data/score.json", "r") as f:
                score_dict = json.load(f)
                score_dict["max_time"] = self.max_time
                score_dict["end_time"] = time.localtime()
            with open("data/score.json", "w") as f:
                json.dump(score_dict, f, indent=4)
            return True
    
        for task in self.task_list:
            task.event_update()
        return False

    def generate(self):
        candidate_agents = self.candidate_agent_group()
        spilt_merge_channel = 0
        # 1 给候选agent 挑选 候选 task 如果 task 有 merge标签的话 必须存在两组相邻的候选agent位置只有p[0]不一致并且相邻 merge则要求存在一组agent在同一位置个数大于一
        candidate_task_list = []
        candidate_agent_groups = []
        candidate_agent_groups_dict = {}
        for atom_task in self.atom_task_list:
            atom_task = atom_task.copy()
            out_item = atom_task.out_item # {"item_name":item_num}
            if atom_task.split:
                idx = spilt_merge_channel
                self.agents.sort(key=lambda agent: agent.position[idx])
                non_candidate_agents = [agent for agent in self.agents if agent not in candidate_agents]
                candidate_agent_groups = [[candidate_agents[0]]]

                # Group candidate agents based on non-candidate agents' positions
                for agent in candidate_agents[1:]:
                    if any(non_candidate_agent.position[idx] < agent.position[idx] < non_candidate_agent.position[idx] + 1 for non_candidate_agent in non_candidate_agents):
                        # If there is a non-candidate agent between the current agent and the previous agent, start a new group
                        candidate_agent_groups.append([agent])
                    else:
                        # Otherwise, add the current agent to the current group
                        candidate_agent_groups[-1].append(agent)
                # Ensure each group has at least two different pos[0] positions
                candidate_agent_groups = [group for group in candidate_agent_groups if len(set(agent.position[idx] for agent in group)) >= 2]
                # 这样的组可以物理合并了

                if len(candidate_agent_groups) == 0:
                    continue

            if atom_task.merge:
                # Group agents by position
                position_to_agents = {}
                for agent in candidate_agents:
                    if str(agent.position) not in position_to_agents:
                        position_to_agents[str(agent.position)] = []
                    position_to_agents[str(agent.position)].append(agent)

                # Ensure each group has at least two agent
                candidate_agent_groups = [agents for agents in position_to_agents.values() if len(agents) >= 2]
                if len(candidate_agent_groups) == 0:
                    continue
                
            if len(out_item) == 0:
                candidate_task_list.append(atom_task)
                candidate_agent_groups_dict[str(atom_task)] = candidate_agent_groups
                continue

            for agent in self.agents:
                if len(agent.inventory) == 0:
                    continue
                satisfied = True
                for key, value in out_item.items():
                    if key not in agent.inventory.keys() or agent.inventory[key] < value:
                        satisfied = False
                        break
                if satisfied:
                    candidate_task_list.append(atom_task)
                    candidate_agent_groups_dict[str(atom_task)] = candidate_agent_groups
        
        # 2 选择一个最合适的候选task
        if len(candidate_task_list) == 0:
            return
        print("seed", self.seed)
        print("task_len", len(self.task_list))
        print("candidate_len", len(candidate_task_list))
        
        print("select idx", (self.seed + len(self.task_list)) % len(candidate_task_list))
        selected_task = candidate_task_list[(self.seed + len(self.task_list)) % len(candidate_task_list)]
        selected_task = selected_task.copy()
        if not selected_task.same_room and not selected_task.split and not selected_task.merge:
            selected_task_2 = selected_task
            cross_tasks = [t for t in candidate_task_list if not t.same_room and not t.split and not t.merge and t != selected_task]
            if cross_tasks:
                selected_task_2 = random.choice(cross_tasks)
            selected_task_2 = selected_task_2.copy()
        executable_agents = []

        if selected_task.same_room:
            # Group agents by position
            position_to_agents = {}
            for agent in candidate_agents:
                if str(agent.position) not in position_to_agents:
                    position_to_agents[str(agent.position)] = []
                position_to_agents[str(agent.position)].append(agent)
            executable_agents = random.choice(list(position_to_agents.values()))

        elif selected_task.split or selected_task.merge:
            executable_agents = random.choice(candidate_agent_groups_dict[str(selected_task)])

        else:
            executable_agents = candidate_agents

        # 3 如果选择的task带有  更新agent状态
        agent_num = 0
        if selected_task.same_room or selected_task.split or selected_task.merge:
            for agent in executable_agents:
                satisfied = True
                # print(agent.inventory)
                # print(selected_task.out_item)
                for key, value in selected_task.out_item.items():
                    if key not in agent.inventory.keys() or agent.inventory[key] < value:
                        satisfied = False
                        break

                if satisfied:
                    agent_num += 1
                    
                    for key, value in selected_task.out_item.items():
                        agent.inventory[key] -= value
                    for key, value in selected_task.in_item.items():
                        if key not in agent.inventory.keys():
                            agent.inventory[key] = 0
                        agent.inventory[key] += value

                    agent.position[2] -= 3

            if selected_task.split: #->merge
                # print("split")
                spilt_pos = []
                for agent in executable_agents:
                    spilt_pos.append([agent.position[0] * selected_task.room_width * 3 + selected_task.bias[0], 
                                agent.position[1] * selected_task.room_height + selected_task.bias[1],
                                (agent.position[2] + 3) * selected_task.room_width + selected_task.bias[2]])
                    agent.position[spilt_merge_channel] = min(abs(agent.position[spilt_merge_channel]) for agent in executable_agents)
                pos = executable_agents[0].position
                selected_task.center = [pos[0] * selected_task.room_width * 3 + selected_task.bias[0], 
                                pos[1] * selected_task.room_height + selected_task.bias[1],
                                pos[2] * selected_task.room_width + selected_task.bias[2]]
                pos = None
                selected_task.condition_repeat_num = len(executable_agents)
                selected_task.split_pos = spilt_pos
                self.complexity += selected_task.score
                for agent in executable_agents:
                    agent.room = selected_task.center.copy()
                self.task_list.append(selected_task.copy())

            elif selected_task.merge: # -> split
                # print("merge")
                # print(selected_task)
                before_num = 0
                after_num = 0
                for agent in self.agents:
                    if agent.position[spilt_merge_channel] < executable_agents[0].position[spilt_merge_channel]:
                        before_num += 1
                    elif agent.position[spilt_merge_channel] > executable_agents[0].position[spilt_merge_channel]:
                        after_num += 1
                assert len(self.agents) == before_num + after_num + len(executable_agents), f"{before_num} {after_num} {len(executable_agents)} {len(self.agents)}"
                
                merge_pos = executable_agents[0].position
                merge_pos = [merge_pos[0] * selected_task.room_width * 3 + selected_task.bias[0],
                            merge_pos[1] * selected_task.room_height + selected_task.bias[1],
                            (merge_pos[2] + 3) * selected_task.room_width + selected_task.bias[2]]
                for idx, agent in enumerate(executable_agents):
                    agent.position[spilt_merge_channel] = before_num + idx - len(self.agents) // 2
                    pos = agent.position
                    selected_task.center = [pos[0] * selected_task.room_width * 3 + selected_task.bias[0], 
                                    pos[1] * selected_task.room_height + selected_task.bias[1],
                                    pos[2] * selected_task.room_width + selected_task.bias[2]]
                    pos = None
                    selected_task.condition_repeat_num = 1
                    selected_task.merge_pos = merge_pos
                    self.complexity += selected_task.score * len(executable_agents)
                    agent.room = selected_task.center.copy()
                    self.task_list.append(selected_task.copy())

            else: # same room
                pos = executable_agents[0].position
                selected_task.center = [pos[0] * selected_task.room_width * 3 + selected_task.bias[0], 
                                    pos[1] * selected_task.room_height + selected_task.bias[1],
                                    pos[2] * selected_task.room_width + selected_task.bias[2]]
                pos = None
                if agent_num == 0 or selected_task.min_player > agent_num:
                    # print("agent_num", agent_num)
                    return
                
                selected_task.condition_repeat_num = agent_num
                # print(selected_task, pos)
                self.complexity += selected_task.score * selected_task.condition_repeat_num * len(selected_task.condition) / selected_task.wait_interval
                for agent in executable_agents:
                    agent.room = selected_task.center.copy()
                self.task_list.append(selected_task.copy())

        else:
            # print("cross")
            # 交叉着来，随机选两个房间，一个房间的机关触发另一个房间的效果
            # Group agents by position
            position_to_agents = {}
            for agent in candidate_agents:
                if str(agent.position) not in position_to_agents:
                    position_to_agents[str(agent.position)] = []
                position_to_agents[str(agent.position)].append(agent)
            if len(position_to_agents.values()) < 2:
                return
            
            action_agents = random.choice(list(position_to_agents.values()))
            effect_agents = action_agents
            while effect_agents == action_agents:
                effect_agents = random.choice(list(position_to_agents.values()))
            # print(effect_agents[0].position, action_agents[0].position)
            for agent in action_agents:
                agent.position[2] -= 3
            for agent in effect_agents:
                agent.position[2] -= 3

            for agent in action_agents:
                satisfied = True
                for key, value in selected_task.out_item.items():
                    if key not in agent.inventory.keys() or agent.inventory[key] < value:
                        satisfied = False
                        break

                if satisfied:
                    agent_num += 1
                    for key, value in selected_task.out_item.items():
                        agent.inventory[key] -= value
                
            # cross
            for agent in effect_agents:
                satisfied = True    
                for key, value in selected_task_2.out_item.items():
                    if key not in agent.inventory.keys() or agent.inventory[key] < value:
                        satisfied = False
                        break

                if satisfied:
                    agent_num += 1
                    for key, value in selected_task_2.out_item.items():
                        agent.inventory[key] -= value
            
            for agent in effect_agents:
                for key, value in selected_task.in_item.items():
                    if key not in agent.inventory.keys():
                        agent.inventory[key] = 0
                    agent.inventory[key] += value
            
            # cross
            for agent in action_agents:
                for key, value in selected_task_2.in_item.items():
                    if key not in agent.inventory.keys():
                        agent.inventory[key] = 0
                    agent.inventory[key] += value

            pos = action_agents[0].position
            condition_center = [pos[0] * selected_task.room_width * 3 + selected_task.bias[0], 
                                    pos[1] * selected_task.room_height + selected_task.bias[1],
                                    pos[2] * selected_task.room_width + selected_task.bias[2]]
            selected_task.condition_repeat_num = len(action_agents)
            selected_task.center = condition_center
            new_task = selected_task.copy()
            pos = effect_agents[0].position
            effect_center = [pos[0] * selected_task.room_width * 3 + selected_task.bias[0], 
                                    pos[1] * selected_task.room_height + selected_task.bias[1],
                                    pos[2] * selected_task.room_width + selected_task.bias[2]]
            new_effects = []
            for effect in new_task.effect:
                p = [0,0,0]
                p[0] = effect["position"][0] + effect_center[0] - condition_center[0]
                p[1] = effect["position"][1] + effect_center[1] - condition_center[1]
                p[2] = effect["position"][2] + effect_center[2] - condition_center[2]
                e = effect.copy()
                e["position"] = p
                new_effects.append(e)
            new_task.effect = new_effects
            self.complexity += selected_task.score * len(action_agents)
            for agent in effect_agents:
                agent.room = effect_center.copy()
            self.task_list.append(new_task)

            # cross
            pos = effect_agents[0].position
            condition_center = [pos[0] * selected_task_2.room_width * 3 + selected_task_2.bias[0], 
                                    pos[1] * selected_task_2.room_height + selected_task_2.bias[1],
                                    pos[2] * selected_task_2.room_width + selected_task_2.bias[2]]
            selected_task_2.condition_repeat_num = len(effect_agents)
            selected_task_2.center = condition_center
            new_task = selected_task_2.copy()
            pos = action_agents[0].position
            effect_center = [pos[0] * selected_task_2.room_width * 3 + selected_task_2.bias[0], 
                                    pos[1] * selected_task_2.room_height + selected_task_2.bias[1],
                                    pos[2] * selected_task_2.room_width + selected_task_2.bias[2]]
            new_effects = []
            for effect in new_task.effect:
                p = [0,0,0]
                p[0] = effect["position"][0] + effect_center[0] - condition_center[0]
                p[1] = effect["position"][1] + effect_center[1] - condition_center[1]
                p[2] = effect["position"][2] + effect_center[2] - condition_center[2]
                e = effect.copy()
                e["position"] = p
                new_effects.append(e)
            new_task.effect = new_effects
            self.complexity += selected_task.score * len(effect_agents)
            for agent in action_agents:
                agent.room = effect_center.copy()
            self.task_list.append(new_task)
        # for agent in self.agents:
        #     print(agent)
    
    def candidate_agent_group(self):
        # 根据位置对代理进行排序
        self.agents.sort(key=lambda agent: agent.position[2], reverse=True)
        # 找出可以执行任务的代理组
        candidate_agents = []
        # print("candidate_agents:")
        for agent in self.agents:
            if agent.position[2] == self.agents[0].position[2]:
                candidate_agents.append(agent)
                # print(agent.position)
        return candidate_agents


def load_atom_from_json(file_path:str):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

if __name__ == "__main__":
    state_tree = StateTree(None, None, agent_num=2, bias=[110, -60, 140],file_path="data/escape_atom_test.json")
    for task in state_tree.task_list:
        print(task)
    for agent in state_tree.agents:
        print(agent)
