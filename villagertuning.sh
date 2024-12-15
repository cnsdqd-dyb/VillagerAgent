__conda_setup="$('/opt/conda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        . "/opt/conda/etc/profile.d/conda.sh"
    else
        export PATH="/opt/conda/bin:$PATH"
    fi
fi
unset __conda_setup
export PATH="/home/yubo/.nvm/versions/node/v18.19.0/bin:$PATH"
echo $NODE_PATH
export NODE_PATH=/home/yubo/.nvm/versions/node/v18.19.0/lib/node_modules
node -v
npm -v
conda activate villageragent
cd /home/yubo/VillagerAgent-Minecraft-multiagent-framework
export http_proxy=http://10.39.23.15:808
export https_proxy=http://10.39.23.15:808
npm install idealTree debug mineflayer prismarine-viewer mineflayer-pathfinder mineflayer-collectblock mineflayer-pvp minecrafthawkeye vec3 socks5-client minecraft-data
unset http_proxy
unset https_proxy
npm fund
python /home/yubo/VillagerAgent-Minecraft-multiagent-framework/js_setup.py
python /home/yubo/VillagerAgent-Minecraft-multiagent-framework/auto_gen_gpt_task.py