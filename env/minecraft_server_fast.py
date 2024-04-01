# Description: This is the fastapi server for the minecraft agent.
# This file still need to be tested, and it is not finished yet.

import argparse
import time
from math import floor
import names
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException
from functools import wraps
from env_api import *
import uvicorn

# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')
os.environ["REQ_TIMEOUT"] = "1800000"
app = FastAPI()
msg_list = []  # 用于存储消息队列，每次获取后清除当前的消息队列
# python minecraft_server_fast.py -U Tom
parser = argparse.ArgumentParser()
parser.add_argument('-P', '--port', type=int, default=25565)
parser.add_argument('-H', '--host', type=str, default='10.21.31.18')
parser.add_argument('-U', '--username', type=str, default=names.get_full_name().replace(' ', '_'))
parser.add_argument('-W', '--worldname', type=str)
parser.add_argument('-LP', '--local_port', type=int, default=5000)
parser.add_argument('-D', '--debug', type=bool, default=False)
args = parser.parse_args()
local_port = args.local_port
print(f"Agent {args.username} login {args.worldname} at {args.host}:{args.port}")
# VIEW_PORT = 3000
mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
collectBlock = require('mineflayer-collectblock')
pvp = require("mineflayer-pvp").plugin
minecraftHawkEye = require("minecrafthawkeye")
Vec3 = require("vec3")
# viewer = require('prismarine-viewer').mineflayer
Socks = require("socks5-client")
minecraftData = require('minecraft-data')
mcData = minecraftData('1.19.2')
# print(mcData.itemsByName['yellow_carpet'])
bot = mineflayer.createBot({
    "host": args.host,
    "port": args.port,
    'username': args.username.replace(' ', '_'),
    'checkTimeoutInterval': 600000,
    'auth': 'offline',
    'version': '1.19.2',
})
time.sleep(3)
bot.loadPlugin(pathfinder.pathfinder)
bot.loadPlugin(collectBlock.plugin)
bot.loadPlugin(pvp)
bot.loadPlugin(minecraftHawkEye)


def timeout(seconds: float):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise HTTPException(status_code=408, detail="Request timed out")
        return wrapper
    return decorator


@app.post("/post_render")
@timeout(10)
async def render_structure(request: Request):
    """render_structure: render the structure."""
    data = await request.json()
    id = data.get('id')
    center_pos = data.get('center_pos')
    try:
        with open("../minecraft/building_blue_print.json", "r") as f:
            structure_list = json.load(f)
        structure = structure_list[id]
        for b in structure["blocks"]:
            time.sleep(.05)  
            x, y, z = b["position"][0] + center_pos[0], b["position"][1] + center_pos[1], b["position"][2] + center_pos[2]
            if b["facing"] in ["W", "E", "S", "N"]:
                cvt = {"W": "west", "E": "east", "S": "south", "N": "north"}
                bot.chat(f'/setblock {x} {y} {z} {b["name"]}[facing={cvt[b["facing"]]}]')
            elif b["facing"] in ["x", "y", "z"]:
                bot.chat(f'/setblock {x} {y} {z} {b["name"]}[axis={b["facing"]}]')
            elif b["facing"] == "A":
                bot.chat(f'/setblock {x} {y} {z} {b["name"]}')

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"message": "render success", "status": True}

@app.post('/post_msg')  # 获取前端发来的消息
@timeout(10)
async def get_msg(request: Request):
    """get_msg: get the message from the message queue."""
    global msg_list
    msg = msg_list
    msg_list = []
    return JSONResponse({'message': msg, 'status': True})


@app.post('/post_time')  # 获取前端的时间
async def get_time(request: Request):
    return JSONResponse({'time': str(bot.time.timeOfDay)})


@app.post('/post_find')
@timeout(10)
async def find(request: Request):
    """find name distance count: find tag in the distance, and count is the number of items you want to find."""
    data = await request.json()
    name, distance, count = data.get('name'), data.get('distance'), data.get('count')
    name = name_check(bot, Vec3, mcData, name)
    bot.chat(f"name_check {name}")
    if name == "":
        return JSONResponse({'message': "can not find anything match", 'status': False, 'data':[]})
    observation = ""
    name, pos_list_raw = find_everything_(bot, get_envs_info(bot, 128), mcData, name, distance, count)
    # remove duplicate
    pos_list = []
    for pos in pos_list_raw:
        for pos2 in pos_list:
            if floor(pos.x + .5) == floor(pos2.x + .5) and floor(pos.y + .5) == floor(pos2.y + .5) and floor(pos.z + .5) == floor(
                    pos2.z + .5):
                break
        else:
            pos_list.append(pos)

    pos_data = []
    if len(pos_list) > 0:
        str_pos_list = f'I found {name} '
        # if pos_list is dict:
        if type(pos_list) == dict:
            for pos in pos_list:
                str_pos_list += f'at {pos},'
                pos_data.append({"x": floor(pos["x"] + .5), "y": floor(pos["y"] + .5), "z": floor(pos["z"] + .5)})
        else:
            for pos in pos_list:
                str_pos_list += f'at {floor(pos.x + .5)} {floor(pos.y + .5)} {floor(pos.z + .5)},'
                pos_data.append({"x": floor(pos.x + .5), "y": floor(pos.y + .5), "z": floor(pos.z + .5)})
        observation += str_pos_list
        done = True
        return JSONResponse({'message': observation, 'status': done, 'data':pos_data})
    else:
        observation += f"can not find {name}, there is no {name} around."
        done = False
        return JSONResponse({'message': observation, 'status': done, 'data':[]})
    
@app.post('/post_hand')
@timeout(10)
async def hand(request: Request):
    """hand item to entity_name: hand item to entity_name."""
    data = await request.json()
    entity_name, item_name, count = data.get('target_name'), data.get('item_name'), data.get('count')
    envs_info = get_envs_info(bot, 128)
    tag, msg = move_to_nearest_(pathfinder, bot, Vec3, envs_info, mcData, 1, entity_name)
    if not tag:
        return JSONResponse({'message': msg, 'status': False})
    
    # toss item
    msg, tag = toss(bot, mcData, item_name, count)
    return JSONResponse({'message': msg, 'status': tag})

@app.post('/post_move_to')
@timeout(10)
async def move_to_(request: Request):
    """move_to name: move to the entity by name or postion x y z."""
    data = await request.json()
    name = data.get('name')
    envs_info = get_envs_info(bot, 128)
    tag, msg = move_to_nearest_(pathfinder, bot, Vec3, envs_info, mcData, 1, name)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_move_to_pos')
@timeout(10)
async def move_to_pos(request: Request):
    """move_to_pos x y z: move to the position x y z."""
    data = await request.json()
    x, y, z = data.get('x'), data.get('y'), data.get('z')
    tag, msg = move_to(pathfinder, bot, Vec3, 3, Vec3(x, y, z))
    done = tag
    # lookAtPlayer(bot, entity['position'])
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_use_on')
@timeout(10)
async def use_on(request: Request):
    """use_on item_name entity_name: For example, you can use shears on sheep, use bucket on cow."""
    data = await request.json()
    item_name, entity_name = data.get('item_name'), data.get('entity_name')
    envs_info = get_envs_info(bot, 128)
    msg, tag = useOnNearest(bot, envs_info, mcData, item_name, entity_name)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_sleep')
@timeout(10)
async def sleep_():
    """sleep: to sleep."""
    msg = sleep(bot, Vec3, mcData)
    done = True
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_wake')
@timeout(10)
async def wake_():
    """wake: to wake."""
    msg = wake(bot)
    done = True
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_dig')
@timeout(10)
async def dig(request: Request):
    """dig x y z: dig block at x y z."""
    data = await request.json()
    x, y, z = data.get('x'), data.get('y'), data.get('z')
    msg, tag = dig_at(bot, pathfinder, Vec3, (x, y, z))
    return JSONResponse({'message': msg, 'status': tag})


@app.post('/post_place')
@timeout(10)
async def place(request: Request):
    """place item_name x y z facing: place item at x y z, facing is one of [W, E, S, N, x, y, z]."""
    data = await request.json()
    item_name, x, y, z, facing = data.get('item_name'), data.get('x'), data.get('y'), data.get('z'), data.get('facing')
    if facing.lower() == 'default':
        facing = 'A'
    if facing.lower() == 'up' or facing.lower() == 'down':
        facing = 'y'
    if facing.lower() == 'north' or facing.lower() == 'south':
        facing = 'z'
    if facing.lower() == 'west' or facing.lower() == 'east':
        facing = 'x'
    if facing not in ['x', 'y', 'z', "W", "E", "S", "N", "A"]:
        return JSONResponse({'message': "facing is one of [W, E, S, N, x, y, z, A]", 'status': False})
    flag, msg = await place_axis(bot, mcData, pathfinder, Vec3, item_name, (x, y, z), facing)
    if not flag and item_name == 'ladder':
        return JSONResponse({'message': f"{msg}, there is no dirt block to support it.", 'status': False})
    return JSONResponse({'message': msg, 'status': flag})


@app.post('/post_attack')
@timeout(10)
async def attack_(request: Request):
    """attack name:  to attack the nearest entity."""
    data = await request.json()
    name = data.get('name')
    envs_info = get_envs_info(bot, 128)
    msg, tag = await attack(bot, envs_info, mcData, name)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_equip')
@timeout(10)
async def equip_(request: Request):
    """equip slot item_name:  to equip item on hand,head,torso,legs,feet,off-hand."""
    data = await request.json() 
    slot, item_name = data.get('slot'), data.get('item_name')
    observation = ""
    value_data = []
    try:
        if not findInventoryItems(bot, item_name):
            observation += f"I don't have {item_name} in my inventory"
            return JSONResponse({'message': observation, 'status': False, 'data': []})
        else:
            msg, done = equip(bot, item_name, slot)
            observation += msg
            return JSONResponse({'message': observation, 'status': done, 'data': value_data})
    except:
        observation += "equip fail"
        done = False
        return JSONResponse({'message': observation, 'status': done, 'data': value_data})


@app.post('/post_toss')
@timeout(10)
async def toss_(request: Request):
    """toss item_name count:  to throw item out."""
    data = await request.json()
    item_name, count = data.get('item_name'), data.get('count', 1)
    msg, tag = toss(bot, mcData, item_name, count)
    return JSONResponse({'message': msg, 'status': tag})


@app.post('/post_environment')
@timeout(10)  # 获取环境信息
async def environment(request: Request):
    """environment:  to get the environment info."""
    msg = get_envs_info2str(bot, RENDER_DISTANCE=32, same_entity_num=3)
    blocks = BlocksNearby(bot, Vec3, mcData, RenderRange=16, max_same_block=3)
    hint = readNearestSign(bot, Vec3, mcData, max_distance=5)
    for block in blocks:
        for key in block.keys():
            if key != 'facing':
                msg += f"{key} at {block[key]}\n"
    if hint:
        msg += f"the sign nearby said: {hint}"
    
    if os.path.exists(".cache/env.cache"):
        with open(".cache/env.cache", "r") as f:
            cache = json.load(f)
        # 找到距离小于5的cache
        for c in cache:
            pos = c["center"]
            if (pos[0] - bot.entity.position.x) ** 2 + (pos[1] - bot.entity.position.y) ** 2 + (
                    pos[2] - bot.entity.position.z) ** 2 < 25:
                msg += f"the env in the room: {c['state']}"
    done = True
    return JSONResponse({'message': msg, 'status': done})

@app.post('/post_environment_dict')
@timeout(10)  # 获取环境信息
async def environment_info(request: Request):
    """environment:  to get the environment info."""
    msg = get_envs_info_dict(bot, RENDER_DISTANCE=32, same_entity_num=3)
    blocks = BlocksNearby(bot, Vec3, mcData, RenderRange=32, max_same_block=3)
    hint = readNearestSign(bot, Vec3, mcData, max_distance=5)
    msg["blocks"] = blocks
    msg["sign"] = hint
    if os.path.exists(".cache/env.cache"):
        with open(".cache/env.cache", "r") as f:
            cache = json.load(f)
        # 找到距离小于5的cache
        for c in cache:
            pos = c["center"]
            if (pos[0] - bot.entity.position.x) ** 2 + (pos[1] - bot.entity.position.y) ** 2 + (
                    pos[2] - bot.entity.position.z) ** 2 < 25:
                msg["sign"] += f"The env in the room: {c['state']}"
    done = True
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_entity')
@timeout(10)
async def entity(request: Request):
    """entity distance name:  to get the entity info in range distance."""
    data = await request.json()
    name = data.get('name', "")
    info, num = get_agent_info2str(bot, RENDER_DISTANCE=32, idle=False, with_humans=False, name=name)
    return JSONResponse({'message': info, 'status': True, 'data': num})


@app.post('/post_get')
@timeout(10)
async def get(request: Request):
    """get item_name count:  to get item from one chest, container, etc."""
    data = await request.json()
    item_name, from_name, item_count = data.get('item_name'), data.get('from_name'), data.get('item_count')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, from_name, get_item_name=item_name, count=-item_count)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_put')
@timeout(10)
async def put(request: Request):
    """put item_name count:  to put item to one chest, container, etc."""
    data = await request.json()
    item_name, to_name, item_count = data.get('item_name'), data.get('to_name'), data.get('item_count')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, to_name, get_item_name=item_name, count=item_count)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_smelt')
@timeout(10)
async def smelt(request: Request):
    """smelt item_name item_count material:  to smelt item in the furnace. fuel_item is one of [wood, coal, charcoal, lava_bucket, etc]."""
    data = await request.json()
    item_name, item_count, fuel_item_name = data.get('item_name'), data.get('item_count'), data.get('fuel_item_name')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, item_name, get_item_name=item_count,
                                             fuel_item_name=fuel_item_name)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_craft')
@timeout(10)
async def craft(request: Request):
    """craft item_name count:  to craft item in the crafting_table."""
    data = await request.json()
    item_name, count = data.get('item_name'), data.get('count')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, 'crafting', get_item_name=item_name, count=count)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_enchant')
@timeout(10)
async def enchant(request: Request):
    """enchant item_name count:  to enchant item in the enchanting_table."""
    data = await request.json()
    item_name, count = data.get('item_name'), data.get('count')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, 'enchanting_table', get_item_name=item_name,
                         count=count)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_trade')
@timeout(10)
async def trade(request: Request):
    """trade item_name count:  to trade item with the entity."""
    data = await request.json()
    item_name, with_name, count = data.get('item_name'), data.get('with_name'), data.get('count')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, with_name, get_item_name=item_name, count=count)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_repair')
@timeout(10)
async def repair(request: Request):
    """repair item_name material:  to repair item in the anvil. material is one of [wood, stone, iron, diamond, gold]."""
    data = await request.json()
    item_name, material = data.get('item_name'), data.get('material')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, 'anvil', repair_item_name=item_name,
                                             get_item_name=material)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_eat')
@timeout(10)
async def eat(request: Request):
    """eat item_name:  to eat item."""
    data = await request.json()
    item_name = data.get('item_name')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, item_name)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_drink')
@timeout(10)
async def drink(request: Request):
    """drink item_name count:  to drink item."""
    data = await request.json()
    item_name, count = data.get('item_name'), data.get('count')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, item_name)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_wear')
@timeout(10)
async def wear(request: Request):
    """wear slot item_name:  to wear item on head,torso,legs,feet,off-hand."""
    data = await request.json()
    slot, item_name = data.get('slot'), data.get('item_name')
    observation = ""
    value_data = []
    try:
        if not findInventoryItems(bot, item_name):
            envs_info = get_envs_info(bot, 128)
            msg, flag, value_data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, 'chest', get_item_name=item_name)
            observation += msg
        msg, done = equip(bot, item_name, slot)
        observation += msg
        return JSONResponse({'message': observation, 'status': done, 'data': value_data})
    except:
        observation += "equip fail"
        done = False
        return JSONResponse({'message': observation, 'status': done, 'data': value_data})
    
@app.post('/post_find_inventory')
@timeout(10)
async def find_inventory(request: Request):
    """find_inventory item_name:  to find if there is item in the inventory and return count."""
    data = await request.json()
    item_name = data.get('item_name')
    tag, count = findInventoryItems(bot, item_name)
    return JSONResponse({'message': "", 'status': tag, 'data': count})


@app.post('/post_open')
@timeout(10)
async def open_(request: Request):
    """open item_name:  to open the door, gate, fence_gate, trapdoor, chest, etc, return the items names if open chest"""
    data = await request.json()
    item_name = data.get('item_name')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, item_name)
    return JSONResponse({'message': tag, 'status': flag, 'data': data})


@app.post('/post_close')
@timeout(10)
async def close_(request: Request):
    """close item_name:  to close the door, gate, fence_gate, trapdoor, chest, etc."""
    data = await request.json()
    item_name = data.get('item_name')
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, item_name)
    if flag:
        return JSONResponse({'message': "I close " + item_name, 'status': flag, 'data': data})
    else:
        return JSONResponse({'message': "I cannot close " + item_name + ", it is still open.", 'status': flag, 'data': data})


@app.post('/post_activate')
@timeout(10)
async def activate(request: Request):
    """activate item_name:  to activate the button, lever, pressure_plate, etc."""
    data = await request.json()
    item_name = data.get('item_name')
    x, y, z = data.get('x'), data.get('y'), data.get('z')
    if x is not None and y is not None and z is not None:
        move_to(pathfinder, bot, Vec3, 1, Vec3(x, y, z))
    envs_info = get_envs_info(bot, 128)
    tag, flag, data = await interact_nearest(pathfinder, bot, envs_info, mcData, 3, item_name, target_position=Vec3(x, y, z))
    if flag:
        return JSONResponse({'message': "I activate " + item_name, 'status': flag, 'data': data})
    else:
        return JSONResponse({'message': "I cannot activate " + item_name + ", it is not working.", 'status': flag,
                        'data': data})


@app.post('/post_mount')
@timeout(10)
async def mount_(request: Request):
    """mount entity_name:  to mount the entity."""
    data = await request.json()
    entity_name = data.get('entity_name')
    try:
        msg, done = mount(bot, entity_name)
        return JSONResponse({'message': msg, 'status': done})
    except:
        done = False
        return JSONResponse({'message': "mount fail", 'status': done})


@app.post('/post_dismount')
@timeout(10)
async def dismount_(request: Request):
    """dismount:  to dismount the entity."""
    try:
        msg, done = dismount(bot)
        return JSONResponse({'message': msg, 'status': done})
    except:
        done = False
        return JSONResponse({'message': "dismount fail", 'status': done})


@app.post('/post_ride')
@timeout(10)
async def ride(request: Request):
    """ride entity_name:  to ride the entity."""
    data = await request.json()
    entity_name = data.get('entity_name')
    try:
        msg, done = mount(bot, entity_name)
        return JSONResponse({'message': msg, 'status': done})
    except:
        done = False
        return JSONResponse({'message': "ride fail", 'status': done})


@app.post('/post_disride')
@timeout(10)
async def disride(request: Request):
    """disride:  to disride the entity."""
    try:
        msg, done = dismount(bot)
        return JSONResponse({'message': msg, 'status': done})
    except:
        done = False
        return JSONResponse({'message': "disride fail", 'status': done})


@app.post('/post_talk_to')
@timeout(10)
async def talk_to(request: Request):
    """talk_to entity_name message:  to talk to the entity."""
    data = await request.json()
    entity_name, message = data.get('entity_name'), data.get('message')
    chat_long(bot, entity_name, message, "talk")
    return JSONResponse({'message': f"I talk to {entity_name} {message}", 'status': True})


@app.post('/post_done')
@timeout(10)
async def done(request: Request):
    """done:  to end the task."""
    data = await request.json()
    feedback = data.get('feedback')
    print(feedback)
    return JSONResponse({'message': "I done", 'status': True})


@app.post('/post_action')
@timeout(10)
async def action(request: Request):
    """action action_name seconds:  to do action for seconds, action_name is one of [swing_arm, forward, back, left, right, jump, sprint]."""
    data = await request.json()
    action_name, seconds = data.get('action_name'), data.get('seconds')
    if action_name == 'swing_arm':
        start_time = time.time()
        while time.time() - start_time < seconds:
            bot.swingArm()
        return JSONResponse({'message': "I swing my arms.", 'status': True})
    elif action_name == 'forward':
        while seconds > 0:
            bot.setControlState('forward', True)
            seconds -= 1
            time.sleep(1)
        bot.setControlState('forward', False)
        return JSONResponse({'message': "I move forward in a few seconds", 'status': True})
    elif action_name == 'back':
        while seconds > 0:
            bot.setControlState('back', True)
            seconds -= 1
            time.sleep(1)
        bot.setControlState('back', False)
        return JSONResponse({'message': "I move back in a few seconds", 'status': True})
    elif action_name == 'left':
        seconds = 1
        while seconds > 0:
            bot.setControlState('left', True)
            seconds -= 1
            time.sleep(1)
        bot.setControlState('left', False)
        return JSONResponse({'message': "I move left in a few seconds", 'status': True})
    elif action_name == 'right':
        while seconds > 0:
            bot.setControlState('right', True)
            seconds -= 1
            time.sleep(1)
        bot.setControlState('right', False)
        return JSONResponse({'message': "I move right in a few seconds", 'status': True})
    elif action_name == 'sprint':
        while seconds > 0:
            bot.setControlState('sprint', True)
            seconds -= 1
            time.sleep(1)
        bot.setControlState('sprint', False)
        return JSONResponse({'message': "I sprint in a few seconds", 'status': True})
    elif action_name == 'jump':
        while seconds > 0:
            bot.setControlState('jump', True)
            seconds -= 1
            time.sleep(1)
        bot.setControlState('jump', False)
        return JSONResponse({'message': "I jump in a few seconds", 'status': True})
    else:
        return JSONResponse({'message': "I cannot do this action", 'status': False})


@app.post('/post_look_at')
@timeout(10)
async def look_at(request: Request):
    """look_at name: use this to look at someone or something."""
    data = await request.json()
    name = data.get('name')
    envs_info = get_envs_info(bot, 128)
    pos = find_nearest_(bot, envs_info, mcData, name)
    if pos != None:
        lookAtPlayer(bot, pos)
    done = pos != None
    if not done:
        return JSONResponse({'message': f"cannot find {name}.", 'status': done})
    else:
        return JSONResponse({'message': f"I look at {name}.", 'status': done})


@app.post('/post_start_fishing')
@timeout(10)
async def start_fishing(request: Request):
    """start_fishing: start fishing."""
    envs_info = get_envs_info(bot, 128)
    msg, tag = startFishing(bot, envs_info, mcData)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_stop_fishing')
@timeout(10)
async def stop_fishing(request: Request):
    """stop_fishing: stop fishing."""
    msg, tag = stopFishing(bot)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_read')
@timeout(10)
async def read_(request: Request):
    """read name: only support read book or sign."""
    data = await request.json()
    name = data.get('name')
    envs_info = get_envs_info(bot, 128)
    msg, tag = read(bot, envs_info, mcData, name)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_read_page')
@timeout(10)
async def read_page(request: Request):
    """read name: this is how you read content from book page."""
    data = await request.json()
    name, page = data.get('name'), data.get('page')
    envs_info = get_envs_info(bot, 128)
    msg, tag = read(bot, envs_info, mcData, name, page)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_write')
@timeout(10)
async def write_(request: Request):
    """write name: this is how you write content on writable book or sign."""
    data = await request.json()
    name, content = data.get('name'), data.get('content')
    envs_info = get_envs_info(bot, 128)
    msg, tag = write(bot, envs_info, mcData, name, content)
    done = tag
    return JSONResponse({'message': msg, 'status': done})


@app.post('/post_chat')
@timeout(10)
async def chat_(request: Request):
    """chat message: this is how you chat."""
    data = await request.json()
    message = data.get('msg')
    message_copy = message
    while True:
        if len(message_copy) > 256:
            bot.chat(message_copy[:256])
            time.sleep(.5)
            message_copy = message_copy[256:]
        else:
            bot.chat(message_copy)
            break
    return JSONResponse({'message': f"I chat {message}", 'status': True})


@On(bot, 'spawn')
async def handleViewer(*args):
    path = [bot.entity.position]

    bot.chat('/gamemode survival')
    bot.chat('/clear @s')
    bot.chat('/give @s minecraft:book 1')
    bot.chat('/give @s minecraft:ladder 64')

    @On(bot, 'move')
    def handleMove(*args):
        try:
            if (path[-1].distanceTo(bot.entity.position) > 1.5):
                path.append(bot.entity.position)
                # bot.viewer.drawLine('path', path)
        except:
            pass

    @On(bot, 'chat')
    def handle(this, username, message, *args):
        try:
            global msg_list
            msg_list += [{"username": username, "message": message}]
        except:
            pass
        
    @On(bot, "whisper")
    def handle(this, username, message, *args):
        global msg_list
        msg_list += [{"username": username, "message": message}]


@On(bot, "itemDrop")
def handle(this, entity, *args):
    # bot.chat("item drop")
    dis = distanceTo(bot.entity.position, entity['position'])
    if dis < 4:
        move_to(pathfinder, bot, Vec3, 1, entity['position'])

async def main():
    assert False, "This module needs to be rewrite"
    # 配置 Uvicorn 服务器
    config = uvicorn.Config("minecraft_server_fast:app", port=local_port)
    server = uvicorn.Server(config)

    # 启动服务器
    await server.serve()
    
# The entry point for starting the application
if __name__ == "__main__":
    # Detect if the current context is already running inside an event loop
    try:
        # If this raises an exception, we're not in an event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, we can use asyncio.run()
        asyncio.run(main())
    else:
        # An event loop is running, we should configure and start the server directly
        uvicorn.run(app="minecraft_server_fast:app", port=local_port)