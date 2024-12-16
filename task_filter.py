import json
from collections import defaultdict

def load_and_filter_tasks(json_file_path):
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    # 使用字典来按scenario和action分组
    task_groups = defaultdict(list)
    
    # 对任务进行分组
    for task in tasks:
        scenario = task['task_scenario']
        action = task['evaluation_arg'].get('action', '')  # 如果action不存在则为空字符串
        group_key = f"{scenario}_{action}"
        task_groups[group_key].append(task)
    
    # 从每个组中选择一个任务
    filtered_tasks = []
    for group in task_groups.values():
        filtered_tasks.append(group[0])  # 选择每组的第一个任务
    
    return filtered_tasks

def save_filtered_tasks(filtered_tasks, output_file_path):
    # 保存筛选后的任务到新的JSON文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_tasks, f, indent=4, ensure_ascii=False)

def main():
    input_file = 'gpt_4_1106_preview_launch_config_meta.json'  # 输入文件路径
    output_file = 'filtered_tasks.json'  # 输出文件路径
    
    # 处理任务
    filtered_tasks = load_and_filter_tasks(input_file)
    
    # 保存结果
    save_filtered_tasks(filtered_tasks, output_file)
    
    # 打印结果统计
    print(f"Filtered tasks: {len(filtered_tasks)}")
    
    # 打印每个保留的任务的基本信息
    for task in filtered_tasks:
        print(f"Kept task - Scenario: {task['task_scenario']}, "
              f"Action: {task['evaluation_arg'].get('action', '')}, "
              f"Task name: {task['task_name']}")

if __name__ == "__main__":
    main()
