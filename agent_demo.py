import time
from env.env import MaMcEnv, env_type, Agent
from pipeline.agent import BaseAgent
from pipeline.controller import GlobalController
from pipeline.data_manager import DataManager
from pipeline.task_manager import TaskManager
from model.openai_models import OpenAILanguageModel
import json

if __name__ == "__main__":


    # 为了加速，我们使用了多个API KEY，同时api_base也改为了国内的服务器
    openai_key_list = json.load(open("API_KEY_LIST", "r"))["OPENAI"]
    base_url = "https://api.chatanywhere.tech/v1"
    llm = OpenAILanguageModel(api_model="gpt-4-1106-preview", api_base=base_url, api_key_list=openai_key_list)
    Agent.model = "gpt-4-1106-preview"
    Agent.base_url = base_url
    Agent.api_key_list = openai_key_list

    # llm = OpenAILanguageModel(api_model="gpt-3.5-turbo-1106")

    env = MaMcEnv(env_type.none, 1, _virtual_debug=False, host = "10.21.31.18", port=25565, dig_needed=True)

    agent_tool = [Agent.scanNearbyEntities, Agent.navigateTo, Agent.attackTarget,
            Agent.UseItemOnEntity, Agent.sleep, Agent.wake,
            Agent.MineBlock, Agent.placeBlock, Agent.equipItem,
            Agent.handoverBlock, Agent.SmeltingCooking,
            Agent.withdrawItem, Agent.storeItem, Agent.craftBlock,
            Agent.enchantItem, Agent.trade, Agent.repairItem, Agent.eat,
            Agent.fetchContainerContents, Agent.ToggleAction]

    env.agent_register(agent_tool=agent_tool, agent_number=2, name_list=["Amy","Andrew"])
    
    with env.run(fast_api=False): # 新增加了一个参数，用于控制是否使用fastapi server

        start_time = time.time()
        dm = DataManager()
        dm.update_database_init(env.get_init_state())
        while True:
            feedback, detail = env.step("Andrew", '''You are a powerful ai act as minecraft agent. Try to cook the raw rabbit to get the cooked rabbit. You can use the furnace''')