import os
import json
# 指定根目录
root_dir = "result"

max_action_num = 10
max_failed_num = 2

# 遍历根目录下的所有子文件夹
for folder_name in os.listdir(root_dir):
    folder_path = os.path.join(root_dir, folder_name)
    if os.path.isdir(folder_path):  # 确保是文件夹
        flag = True
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):  # 确保是文件
                if "action" in file_path:
                    with open(file_path, "r") as f:
                        action_log = json.dump(f)
                        if "Alice" in action_log:
                            action_list = action_log["Alice"]
                            if len(action_list) > max_action_num:
                                flag = False
                            else:
                                failed_action_num = len([action for action in action_list if not action["result"]["status"]])
                                if failed_action_num > max_failed_num:
                                    flag = False
                                    
                        else:
                            flag = False
                elif "score" in file_path:
                    with open(file_path, "r") as f:
                        score = json.dump(f)
                        if score["score"] != 100:
                            flag = False
                            
