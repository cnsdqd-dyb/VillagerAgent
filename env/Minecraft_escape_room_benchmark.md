# Minecraft Escape Room Benchmark Usage Document
点击此处查看 [中文版 README](Minecraft_escape_room_benchmark_zh.md)。

This document provides a detailed explanation of how to use the provided JSON files to configure cooperative puzzle games in Minecraft. Each JSON file defines a series of atomic operations for cooperative puzzle gameplay.

## JSON File Structure

Each JSON file contains the following properties:

- `init`: Defines the state at the start of the operation.
- `condition`: Defines the conditions that trigger the effects.
- `effect`: Defines the effects that occur when the conditions are met.
- `in`: Defines the items required to enter the current state.
- `out`: Defines the items obtained after completing the current state.
- `activate_duration`: Defines the duration of the activated state.
- `split`: Defines whether to split players into different scenes in multiplayer mode.
- `merge`: Defines whether to merge players into the same scene in multiplayer mode.
- `same_room`: Defines whether to be in the same room.

The outermost layer of the JSON file also contains the following optional properties:

- `room_height`: Defines the height of a single scene, default is 3.
- `room_width`: Defines the width of a single scene, default is 3.
- `wall_width`: Defines the thickness of the edges of a single scene, default is 1.
- `score`: Defines the score obtained after clearing the level, default is 1.
- `wait_interval`: Defines the judgment interval when multiple conditions are triggered simultaneously, default is 4 seconds.
- `type`: Defines the satisfaction mode of the conditions, if it is "and", all conditions must be met; if it is "or", only one condition needs to be met.
- `task_description`: Defines the hint description of the task.

## Property Details

### init, condition, effect

The `init`, `condition`, `effect` properties are object arrays, each object contains the following properties:

- `name`: Defines the name of the block or entity. Supports the names of all Minecraft blocks and entities. In `init` and `effect`, it also supports the syntax `"name": "summon_sheep"` for spawning entities.
- `position`: Defines the position of the block or entity. It is an array containing three integers representing the x, y, z coordinates. For doors, its coordinates are the bottom coordinates.
- `facing`: Defines the orientation of the block. Valid values are "east", "west", "north", "south".
- `face`: Defines the installation surface of levers or buttons. Valid values are "floor", "wall".
- `powered`: Defines whether the lever or button is activated. Valid values are true or false.
- `open`: Defines whether the door or fence gate is open. Valid values are true or false.
- `axis`: Defines the axial orientation of certain blocks (such as logs, pillars, etc.). Valid values are "x", "y", "z".
- `lock_key`: Defines the item tag for locking a container.
- `command`: Defines a command. In the command, `_pos_` is replaced with the current item's position, `_position_` is replaced with the position in the format "x=x, y=y, z=z", `_merge_pos_` is used in merged levels and is replaced with the merge location at the end of the task, `_split_pos_` is used when multiple players are split into multiple scenes and is replaced with the corresponding location after splitting.

### in, out

The `in`, `out` properties are objects, each key-value pair represents an item and its quantity.

### activate_duration

The `activate_duration` property defines the duration of the activated state. It is an integer, with the unit being seconds.

### split, merge, same_room

The `split`, `merge`, `same_room` properties all define the distribution of players. Valid values are true or false.

### room_height, room_width, wall_width

The `room_height`, `room_width`, `wall_width` properties all define the dimensions of the scene. They are integers.

### score

The `score` property defines the score obtained after clearing the level. It is an integer.

### wait_interval

The `wait_interval` property defines the judgment interval when multiple conditions are triggered simultaneously. It is an integer, with the unit being seconds.

### type

The `type` property defines the satisfaction mode of the conditions. It can have the following values:

- `and`: All conditions must be met.
- `or`: Only one condition needs to be met.

### task_description

The `task_description` property defines the hint description of the task. It is a string.

### min_player

The `min_player` is used by default in the generation of cooperative tasks in the same room, requiring at least min_player players to generate the task.

## Example

### command

The `command` property defines a command that can be used in `init` and `effect`. In the command, the following placeholders can be used:

- `_pos_`: Will be replaced with the current item's position, in the format "x y z".
- `_position_`: Will be replaced with the current item's position, in the format "x=x, y=y, z=z".
- `_merge_pos_`: Used in merged levels, will be replaced with the merge location at the end of the task.
- `_split_pos_`: Used when multiple players are split into multiple scenes, will be replaced with the corresponding location after splitting.

Here are some examples of `command` usage:

- `/give @a[_position_,distance=..2] minecraft:tripwire_hook{display:{Name:'{"text":"key"}'}}`: Gives all players within 2 blocks a key-named item.
- `/tp @r[_position_,distance=..2] _merge_pos_`: Teleports a random player within 2 blocks to the merge location at the end of the task.
- `/tp @r[_position_,distance=..2] _split_pos_`: Teleports a random player within 2 blocks to the corresponding location after splitting.
- `/item replace block _pos_ container.0 with gold_block`: Replaces the item in the first slot of the container at the current position with a gold block.

Here is an example that defines a lever. When the lever is activated, it gives all players within 2 blocks a key-named item and teleports a random player to the merge location at the end of the task.

```json
{
    "init": [
        {
            "name": "lever",
            "position": [0, 0, 1],
            "powered": false
        }
    ],
    "condition": [
        {
            "name": "lever",
            "position": [0, 0, 1],
            "powered": true,
            "random": false,
            "activate_mode": "level"
        }
    ],
    "effect": [
        {
            "name": "lever",
            "position": [0, 0, 1],
            "command": "/give @a[_position_,distance=..2] minecraft:tripwire_hook{display:{Name:'{"text":"key"}'}}"
        },
        {
            "name": "lever",
            "position": [0, 0, 1],
            "command": "/tp @r[_position_,distance=..2] _merge_pos_"
        }
    ],
    "in": {},
    "out": {},
    "activate_duration": 2,
    "split": false,
    "merge": true,
    "same_room": false,
    "room_height": 3,
    "room_width": 3,
    "wall_width": 1,
    "score": 1,
    "wait_interval": 4,
    "type": "and",
    "task_description": "Activate the lever to get a key and teleport to the merge point."
}
```

In this example, the lever's initial position is (0, 0, 1), and the initial state is not activated. When the lever is activated, two commands will be executed: one gives all players within 2 blocks a key-named item, and the other teleports a random player within 2 blocks to the merge location at the end of the task. The activated state lasts for 2 seconds, does not split players in multiplayer mode, but merges players at the end of the task. The scene height is 3, width is 3, edge thickness is 1, the score obtained after clearing the level is 1, the judgment interval for multiple conditions triggered simultaneously is 4 seconds, all conditions must be met, the task's hint description is "Activate the lever to get a key and teleport to the merge point.", blocks cannot be placed randomly and must be placed according to the given position, the block's activation mode is level-triggered.