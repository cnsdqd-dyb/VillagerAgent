## Minecraft Multi-agent Benchmark API Library
### scanNearbyEntities
- args: (player_name: str, item_name: str, radius: int = 10, item_num: int = -1)

- description: Find minecraft item blocks creatures in a radius,

- return: ('message': msg, 'status': True/False, 'data':[('x':x,'y':y,'z':z),...]) This function can not find items in the chest, container,or player's inventory.

### navigateTo
- args: (player_name: str, x: int, y: int, z: int)

- description: Move to a Specific Position x y z,

- return: string result

### attackTarget
- args: (player_name: str, target_name: str)

- description: Attack the Nearest Entity with a Specific Name

### navigateToBuilding
- args: (player_name: str, building_name: str)

- description: Move to a building by name,

- return: string result

### navigateToAnimal
- args: (player_name: str, animal_name: str)

- description: Move to an animal by name,

- return: string result

### navigateToPlayer
- args: (player_name: str, target_name: str)

- description: Move to a target Player,

- return: ('message': msg, 'status': True/False)

### UseItemOnEntity
- args: (player_name: str, item_name: str, entity_name: str)

- description: Use a Specific Item on a Specific Entity,

- return: string result

### sleep
- args: (player_name: str)

- description: Go to Sleep

### wake
- args: (player_name: str)

- description: Wake Up

### MineBlock
- args: (player_name: str, x: int, y: int, z: int)

- description: Dig Block at Specific Position x y z

### placeBlock
- args: (player_name: str, item_name: str, x: int, y: int, z: int, facing: str)

- description: Place a Specific Item at Specific Position x y z with Specific facing in one of [W, E, S, N, x, y, z, A] default is 'A'.,

- return: ('message': msg, 'status': True/False)

### equipItem
- args: (player_name: str, slot: str, item_name: str)

- description: Equip a Specific Item on a Specific Slot | to equip item on hand,head,torso,legs,feet,off-hand.

### tossItem
- args: (player_name: str, item_name: str, count: int = 1)

- description: Throw a Specific Item Out with a Specific Count

### talkTo
- args: (player_name: str, entity_name: str, message: str)

- description: Talk to the Entity

### handoverBlock
- args: (player_name: str, target_player_name: str, item_name: str, item_count: int)

- description: Hand Item to a target player you work with,

- return: ('message': msg, 'status': True/False), item num will be automatically checked and player will automatically move to the target player

### withdrawItem
- args: (player_name: str, item_name: str, from_name: str, item_count: int)

- description: Take out Item from nearest 'chest' | 'container' | 'furnace'

- return: string result

### storeItem
- args: (player_name: str, item_name: str, to_name: str, item_count: int)

- description: Put in Item to One Chest, Container, etc,

- return: string result

### craftBlock
- args: (player_name: str, item_name: str, count: int)

- description: Craft Item in the Crafting Table

### SmeltingCooking
- args: (player_name: str, item_name: str, item_count: int, fuel_item_name: str)

- description: Smelt or Cook Item in the Furnace

### erectDirtLadder
- args: (player_name: str, top_x, top_y, top_z)

- description: Helpful to place item at higher place Erect a Dirt Ladder Structure at Specific Position x y z, remember to dismantle it after use

### dismantleDirtLadder
- args: (player_name: str, top_x, top_y, top_z)

- description: Dismantle a Dirt Ladder Structure from ground to top at Specific Position x y z

### enchantItem
- args: (player_name: str, item_name: str, count: int)

- description: Enchant Item in the Enchanting Table

### trade
- args: (player_name: str, item_name: str, with_name: str, count: int)

- description: Trade Item with the villager npc,

- return: the details of trade items and num.

### repairItem
- args: (player_name: str, item_name: str, material: str)

- description: Repair Item in the Anvil

### eat
- args: (player_name: str, item_name: str)

- description: Eat Item

### drink
- args: (player_name: str, item_name: str, count: int)

- description: Drink Item

### wear
- args: (player_name: str, slot: str, item_name: str)

- description: Wear Item on Specific Slot

### layDirtBeam
- args: (player_name: str, x_1, y_1, z_1, x_2, y_2, z_2)

- description: Lay a Dirt Beam from Position x1 y1 z1 to Position x2 y2 z2

### removeDirtBeam
- args: (player_name: str, x_1, y_1, z_1, x_2, y_2, z_2)

- description: Remove a Dirt Beam from Position x1 y1 z1 to Position x2 y2 z2

### openContainer
- args: (player_name: str, container_name: str, position=[0, 0, 0])

- description: Open the nearest but might not the correct 'chest' | 'container' | 'furnace' position is optional,

- return: ('message': msg, 'status': True/False, 'data':[('name':name, 'count':count),...])

### closeContainer
- args: (player_name: str, item_name: str, position=[0, 0, 0])

- description: Close 'chest' | 'container' | 'furnace' position is optional.

### fetchContainerContents
- args: (player_name: str, item_name: str, position=[0, 0, 0])

- description: Get the details of item_name 'chest' | 'container' | 'furnace' position is optional,

- return: ('message': msg, 'status': True/False, 'data':[('name':name, 'count':count),...])

### ToggleAction
- args: (player_name: str, item_name: str, x: int, y: int, z: int)

- description: open/close Gate, Lever, Press Button (pressure_plate need to stand on it, iron door need to be powered, they are not included), at Specific Position x y z

### get_entity_info
- args: (player_name: str, target_name: str = '')

- description: Get the Entity Information,

- return: string contains entity name, entity pos x y z, entity held item

### get_environment_info
- args: (player_name: str)

- description: Get the Environment Information,

- return: string contains time of day, weather

### performMovement
- args: (player_name: str, action_name: str, seconds: int)

- description: Perform Action jump forward back left right for Seconds

### lookAt
- args: (player_name: str, name: str)

- description: Look at Someone or Something

### startFishing
- args: (player_name: str)

- description: Start Fishing

### stopFishing
- args: (player_name: str)

- description: Stop Fishing

### read
- args: (player_name: str, item_name: str)

- description: Read Book or Sign neaby,

- return: string details

### readPage
- args: (player_name: str, item_name: str, page: int)

- description: Read Content from Book Page

### write
- args: (player_name: str, item_name: str, content: str)

- description: Write Content on Writable Book or Sign

