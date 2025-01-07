import os
import json
import names

def convert_to_llama_format(data):
    # 构建基础模板
    template = {
        "instruction": "",
        "input": "",
        "output": ""
    }
    dialog = template.copy()

    # 构建instruction (包含系统消息和任务描述)
    instruction = "You are Minecraft BaseAgent. You need to complete the task by following the environment feedback.\n\n"
    instruction += data.get("instruction", "")
    dialog["instruction"] = instruction
    
    input_accumulate = ""
    for action_observation in data.get("input_action_observation", []):

        
        action = action_observation.get("action", {})
        thought = action.get("log", "") if "Thought" in action.get("log", "") else ""
        if "\n\nAction:\n```" in thought:
            thought = thought.split("\n\nAction:\n```")[0]
        action_content = f"{thought}\nTool: {action.get('tool')}\nTool Input: {action.get('tool_input')}".strip()

        feedback = action_observation.get("feedback", {})
        observation_content = f"Feedback: {feedback.get('message')}\nStatus: {feedback.get('status')}\nNew Events: {feedback.get('new_events')}"
        input_accumulate += action_content + "\n"
        input_accumulate += observation_content + "\n"

    
    dialog["input"] = input_accumulate.strip()
    
    final_action = data.get("output_action", {})
    thought = final_action.get("log", "") if "Thought" in final_action.get("log", "") else ""
    if "\n\nAction:\n```" in thought:
        thought = thought.split("\n\nAction:\n```")[0]
    dialog["output"] = f"{thought}\nTool: {final_action.get('tool')}\nTool Input: {final_action.get('tool_input')}".strip()
    
    return dialog

def convert_to_conversation_format(data):
    conversations = []
    
    # 添加系统消息
    system_msg = {
        "role": "system",
        "content": "You are Minecraft BaseAgent. You need to complete the task by following the environment feedback."
    }
    conversations.append(system_msg)
    
    # 添加初始任务指令
    instruction = data.get("instruction", "")
    user_msg = {
        "role": "user",
        "content": f"Instruction: {instruction}"
    }
    conversations.append(user_msg)
    
    # 处理行动和观察
    for action_observation in data.get("input_action_observation", []):
        # 助手的行动
        action = action_observation.get("action", {})
        thought = action.get("log", "") if "Thought" in action.get("log", "")  else ""
        if "\n\nAction:\n```" in thought:
            thought = thought.split("\n\nAction:\n```")[0]
        # content = f"{thought}\nTool: {action.get('tool')}\nTool Input: {action.get('tool_input')}".strip()
        action.pop("log", None)
        content = f"{thought}\nAction: {action}".strip()
        
        assistant_msg = {
            "role": "assistant",
            "content": content,
        }
        conversations.append(assistant_msg)
        
        # 环境反馈
        feedback = action_observation.get("feedback", {})
        user_msg = {
            "role": "user",
            "content": f"Feedback: {feedback.get('message')}\nStatus: {feedback.get('status')}\nNew Events: {feedback.get('new_events')}"
        }
        conversations.append(user_msg)
    
    # 最后的行动
    if "due to iteration" not in str(data.get("output_action", {})):
        final_action = data.get("output_action", {})
        thought = final_action.get("log", "") if "Thought" in final_action.get("log", "")  else ""
        if "\n\nAction:\n```" in thought:
            thought = thought.split("\n\nAction:\n```")[0]

        final_action.pop("log", None)
        content = f"{thought}\nAction: {final_action}".strip()
        assistant_msg = {
            "role": "assistant",
            "content": content,
        }
        conversations.append(assistant_msg)
    else:
        conversations.pop(-1)
    
    return conversations

def save_to_jsonl(conversations, output_file):
    import json
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "messages": conversations
        }, f, ensure_ascii=False, indent=2)

def check_folders():
    # Get current directory
    current_dir = os.getcwd()
    
    # Track deleted folders
    action_history_files = []
    
    # Iterate through all folders in current directory
    for folder in os.listdir(current_dir):
        folder_path = os.path.join(current_dir, folder)
        
        # Check if it's a directory
        if os.path.isdir(folder_path):
            score_file = os.path.join(folder_path, 'score.json')
            action_history_file = os.path.join(folder_path, 'Alice_history.json')
            # Check if score file exists
            if os.path.exists(score_file) and os.path.exists(action_history_file):
                try:
                    with open(score_file, 'r') as f:
                        data = json.load(f)
                        
                    # Check score value
                    if data.get('score') and data.get('score') < 50:
                        continue
                    else:
                        with open(action_history_file, 'r') as f:
                            action_history = json.load(f)
                        action_history_files.append(action_history)
                        
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Error reading {score_file}: {e}")

    return action_history_files

def filter_actions(action_history_files):
    # Filter actions

    filtered_actions = []
    action_distribution = {}
    for action_history in action_history_files:
        new_name = names.get_first_name()
        new_name_2 = names.get_first_name()
        action_history_str = json.dumps(action_history)
        action_history_str = action_history_str.replace('Alice', new_name)
        action_history_str = action_history_str.replace('alice', new_name)
        action_history_str = action_history_str.replace('Bob', new_name_2)
        action_history_str = action_history_str.replace('bob', new_name_2)
        action_historys = json.loads(action_history_str)
        new_action_historys = []
        for action_history in action_historys:
            input_, action_list, final_answer = action_history['input'], action_history['action_list'], action_history['final_answer']
            
            filtered_action_list = []
            for action in action_list:
                act, obs = action['action'], action['feedback']
                if type(obs) != dict:
                    continue
                if obs['status']:
                    filtered_action_list.append(action)
                    if act['tool'] not in action_distribution:
                        action_distribution[act['tool']] = 0
                    action_distribution[act['tool']] += 1

            new_action_history = {
                'input': input_,
                'action_list': filtered_action_list,
                'final_answer': final_answer
            }
            new_action_historys.append(new_action_history)
        filtered_actions.append(new_action_historys)

    return filtered_actions, action_distribution

def split_filtered_actions(filtered_actions):
    # Split filtered actions
    new_filtered_actions = []
    for action_history in filtered_actions:
        for action in action_history:
            if len(action['action_list']) == 0:
                continue
            # 构造多轮action
            instruction = action['input']
            input_act_obs = []
            output_act = action['action_list'][0]['action']
            new_action_history = {
                'instruction': instruction,
                'input_action_observation': input_act_obs.copy(),
                'output_action': output_act
            }
            new_filtered_actions.append(new_action_history.copy())
            for i in range(0, len(action['action_list'])-1):
                input_act_obs.append(action['action_list'][i])
                output_act = action['action_list'][i+1]['action']
                new_action_history = {
                    'instruction': instruction,
                    'input_action_observation': input_act_obs.copy(),
                    'output_action': output_act
                }
                new_filtered_actions.append(new_action_history.copy())
            input_act_obs.append(action['action_list'][-1])
            output_act = {"tool": "stop", "tool_input": {"final_answer": action['final_answer'] }}
            new_action_history = {
                'instruction': instruction,
                'input_action_observation': input_act_obs.copy(),
                'output_action': output_act
            }
            new_filtered_actions.append(new_action_history.copy())

    return new_filtered_actions

def save_filtered_actions(filtered_actions):
    # /high_quality_action/
    if not os.path.exists('high_quality_action'):
        os.makedirs('high_quality_action')

    for i, action_history in enumerate(filtered_actions):
        with open(f'high_quality_action/{i}.json', 'w') as f:
            json.dump(action_history, f, indent=4)

# Run the function
if __name__ == "__main__":
    action_history_files = check_folders()
    filtered_actions, action_distribution = filter_actions(action_history_files)
    print(f"action distribution: {action_distribution}")
    filtered_actions = split_filtered_actions(filtered_actions)
    # save_filtered_actions(filtered_actions)
    print(f"Filtered {len(filtered_actions)} actions saved to high_quality_action folder.")

    conversations = [convert_to_conversation_format(action_history) for action_history in filtered_actions]
    # llama_format = [convert_to_llama_format(action_history) for action_history in filtered_actions]
    save_to_jsonl(conversations, 'high_quality_action.jsonl')
    # save_to_jsonl(llama_format, 'high_quality_action_llama.jsonl')