import json
import yaml
import re

def find_correct_data(dict_data, guard_keys=[]):
    # 如果当前层包含正确的key，返回当前层
    hit = True
    for key in guard_keys:
        if key not in dict_data.keys():
            hit = False
    if hit:
        return dict_data
    # 否则，遍历当前层的每一个key
    for key in dict_data:
        # 如果当前key的值是字典，递归查找
        if isinstance(dict_data[key], dict):
            result = find_correct_data(dict_data[key], guard_keys)
            # 如果找到了包含正确key的层，返回结果
            if result is not None:
                return result
        # 如果当前key的值是列表，遍历列表中的每一个元素
        elif isinstance(dict_data[key], list):
            result_list = []
            for item in dict_data[key]:
                # 如果列表中的元素是字典，递归查找
                if isinstance(item, dict):
                    result = find_correct_data(item, guard_keys)
                    # 如果找到了包含正确key的层，返回结果
                    if result is not None:
                        if isinstance(result, list):
                            result_list += result
                        else:
                            result_list.append(result)
            if len(result_list) > 0:
                return result_list
    # 如果没有找到，返回None
    return None


def extract_info(text: str, guard_keys=[]) -> [dict]:
    try:
        # Initialize an empty list to store the extracted dictionaries
        info_list = []

        # Initialize an empty string to store the current dictionary text
        dict_text = ''
        
        # Initialize a counter for the number of open braces
        brace_count = 0

        # Iterate over each character in the text
        for char in text:
            # If the character is a '{', increase the brace count and add it to the dictionary text
            if char == '{':
                brace_count += 1
                dict_text += char
            # If the character is a '}', decrease the brace count
            elif char == '}':
                brace_count -= 1
                dict_text += char
                # If the brace count is zero, it's the end of a dictionary
                if brace_count == 0:
                    # json False -> false True -> true None -> null
                    dict_text = dict_text.replace("False", "false").replace("True", "true").replace("None", "null")
                    # 处理注释 string // annotation
                    dict_text = re.sub(r'//.*?\n', '\n', dict_text)
                    try:
                        # Convert the dictionary text to a dictionary and add it to the list
                        dict_data = json.loads(dict_text)
                    except Exception as e:
                        print(f"extract with json error, try yaml \n{e}\nerror text:\n{dict_text}")
                        dict_data = None
                    if dict_data is None:
                        # 如果转换失败，尝试使用yaml
                        dict_data = yaml.load(dict_text, Loader=yaml.FullLoader)
                    # 存在一种情况 llm 对 数据进行了包裹，导致数据格式为 {"data":{...}} 或者 {"task":{...}}
                    # 这种情况下，我们需要将数据提取出来
                    # 假设第一层正确的key为 description
                    correct_data = find_correct_data(dict_data, guard_keys)
                    if correct_data is not None:
                        if isinstance(correct_data, list):
                            info_list += correct_data
                        else:
                            info_list.append(correct_data)
                    else:
                        print(f"Warning: {guard_keys} not found in {dict_data}")
                    # Reset the dictionary text
                    dict_text = ''
            # If the character is neither '{' nor '}', add it to the dictionary text if it's part of a dictionary
            elif brace_count > 0:
                dict_text += char
        return info_list
    except Exception as e:
        print(f"extract_info error: {e}")
        return []
