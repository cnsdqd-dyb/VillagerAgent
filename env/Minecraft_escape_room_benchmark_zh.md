# Minecraft escape room benchmark 使用文档
Click here to view the [English version](Minecraft_escape_room_benchmark.md).

这个文档详细说明了如何使用提供的JSON文件来配置Minecraft的合作解谜插件。每个JSON文件定义了一系列的合作解谜游戏的原子操作。

## JSON文件结构

每个JSON文件包含以下属性：

- `init`: 定义了操作开始时的状态。
- `condition`: 定义了触发效果的条件。
- `effect`: 定义了满足条件后的效果。
- `in`: 定义了进入当前状态所需的物品。
- `out`: 定义了完成当前状态后获得的物品。
- `activate_duration`: 定义了激活状态的持续时间。
- `split`: 定义了是否在多人模式下分割玩家到不同的场景。
- `merge`: 定义了是否在多人模式下合并玩家到同一场景。
- `same_room`: 定义了是否在同一场景中。

JSON文件的最外层还包含以下可选属性：

- `room_height`: 定义了单个场景的高度，默认为3。
- `room_width`: 定义了单个场景的宽度，默认为3。
- `wall_width`: 定义了单个场景边缘的厚度，默认为1。
- `score`: 定义了过关后的得分，默认为1。
- `wait_interval`: 定义了多个条件同时触发的判定间隔，默认为4秒。
- `type`: 定义了条件的满足方式，如果为"and"，则所有条件都需要满足；如果为"or"，则只需满足任一条件。
- `task_description`: 定义了任务的提示描述。

## 属性详解

### init, condition, effect

`init`, `condition`, `effect`属性都是对象数组，每个对象包含以下属性：

- `name`: 定义了方块或生物的名称。支持所有Minecraft方块和生物的名称。在`init`和`effect`中，也支持`"name": "summon_sheep"`的写法用于生成生物。
- `position`: 定义了方块或生物的位置。它是一个包含三个整数的数组，分别代表x，y，z坐标。对于门它的坐标是底部的坐标。
- `facing`: 定义了方块的朝向。可选值为"east"，"west"，"north"，"south"。
- `face`: 定义了lever或button的安装面。可选值为"floor"，"wall"。
- `powered`: 定义了lever或button是否被激活。可选值为true或false。
- `open`: 定义了门或栅栏门是否打开。可选值为true或false。
- `axis`: 定义了某些方块（如log，pillar等）的轴向。可选值为"x"，"y"，"z"。
- `lock_key`: 定义了container上锁的物品标签。
- `command`: 定义了一条命令。在命令中，`_pos_`会被替换为当前物品的位置，`_position_`会被替换为"x=0, y=0, z=0"的形式的位置，`_merge_pos_`会在合并关卡使用，被替换为任务结束时的合并地点，`_split_pos_`在多人分到多个场景时使用，会被替换到分解后的对应地点。
- `random`: 定义了该方块是否允许随意放置位置。如果为false，该方块需要按照给定的相对位置放置。
  - 几种特殊情况：random定义为正整数，认定为随机将该条件生成该次数；
  - 如果定义随机条件为负数，例如-k，则默认计算该房间的玩家数num-k为该条件的生成数量。
- `activate_mode`: 定义了方块的激活方式。如果为"level"，则表示电平触发，例如从0变为1；如果为"pulse"，则表示脉冲触发，例如从0变为1再变为0。
- `sub_event`: 定义condition和effect属性的对应子任务，同一名称的条件会触发相同名称的子任务，如果存在 sub_event: "final" 则该字段认为是判定字段，否则认为 所有子任务完成为判定结束
### in, out

`in`, `out`属性都是对象，每个键值对表示一种物品及其数量。

### activate_duration

`activate_duration`属性定义了激活状态的持续时间。它是一个整数，单位为秒。

### split, merge, same_room

`split`, `merge`, `same_room`属性都定义了玩家的分布情况。可选值为true或false。

### room_height, room_width, wall_width

`room_height`, `room_width`, `wall_width`属性都定义了场景的尺寸。它们都是整数。

### score

`score`属性定义了过关后的得分。它是一个整数。

### wait_interval

`wait_interval`属性定义了多个条件同时触发的判定间隔。它是一个整数，单位为秒。

### type

`type`属性定义了条件的满足方式。它可以有以下值：

- `and`: 所有条件都需要满足。
- `or`: 只需满足任一条件。

### task_description

`task_description`属性定义了任务的提示描述。它是一个字符串。

### min_player

`min_player` 默认使用在同一个房间的合作任务生成中，要求生成该任务时至少包含 min_player 名玩家。

## 示例

### command

`command`属性定义了一条命令，可以在`init`和`effect`中使用。在命令中，可以使用以下占位符：

- `_pos_`: 会被替换为当前物品的位置，格式为"x y z"。
- `_position_`: 会被替换为当前物品的位置，格式为"x=x, y=y, z=z"。
- `_merge_pos_`: 在合并关卡使用，会被替换为任务结束时的合并地点。
- `_split_pos_`: 在多人分到多个场景时使用，会被替换到分解后的对应地点。

以下是一些`command`的使用示例：

- `/give @a[_position_,distance=..2] minecraft:tripwire_hook{display:{Name:'{\"text\":\"key\"}'}}`: 给2格内的所有玩家一个名为"key"的物品。
- `/tp @r[_position_,distance=..2] _merge_pos_`: 将2格内的一个随机玩家传送到任务结束时的合并地点。
- `/tp @r[_position_,distance=..2] _split_pos_`: 将2格内的一个随机玩家传送到分解后的对应地点。
- `/item replace block _pos_ container.0 with gold_block`: 将当前位置的容器的第一个格子的物品替换为金块。

以下是一个示例，它定义了一个lever，当lever被激活时，会给2格内的所有玩家一个名为"key"的物品，并将一个随机玩家传送到任务结束时的合并地点。

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
            "command": "/give @a[_position_,distance=..2] minecraft:tripwire_hook{display:{Name:'{\"text\":\"key\"}'}}"
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
    "task_description": "Activate the lever to get a key and teleport to the merge point.",
}
```

在这个示例中，lever的初始位置是(0, 0, 1)，并且初始状态是未激活的。当lever被激活时，会执行两条命令：一条是给2格内的所有玩家一个名为"key"的物品，另一条是将2格内的一个随机玩家传送到任务结束时的合并地点。激活状态持续2秒，不会在多人模式下分割玩家，但会在任务结束时合并玩家。场景的高度为3，宽度为3，边缘厚度为1，过关后的得分为1，多个条件同时触发的判定间隔为4秒，所有条件都需要满足，任务的提示描述为"Activate the lever to get a key and teleport to the merge point."，方块不能随机放置，需要按照给定的位置放置，方块的激活方式为电平触发。