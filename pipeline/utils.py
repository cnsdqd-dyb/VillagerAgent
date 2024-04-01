import re
import json
import logging
import colorlog
import os
import yaml
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.vectorstores.chroma import Chroma
from langchain.docstore.document import Document
from langchain.retrievers import ParentDocumentRetriever
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.storage import InMemoryStore

from typing import Union

import functools
import time

def timed_cache(max_age):
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal cache
            current_time = time.time()
            key = (args, tuple(sorted(kwargs.items())))
            # key to string
            key = str(key)
            
            # Check if the cache entry exists and is still valid
            if key in cache and current_time - cache[key]['timestamp'] < max_age:
                return cache[key]['value']
            
            # Call the function and cache the result
            value = func(*args, **kwargs)
            cache[key] = {'value': value, 'timestamp': current_time}
            
            # Optional: Clean up expired cache entries
            expired_keys = [k for k, v in cache.items() if current_time - v['timestamp'] >= max_age]
            for k in expired_keys:
                del cache[k]
            
            return value
        return wrapper
    return decorator


def format_string(template: str, data: dict) -> str:
    # 检查template中的{{}}是否都在data中
    keys = re.findall(r'{{(.*?)}}', template)
    for key in keys:
        if key not in data:
            raise ValueError(f'when format:\n{template} \nkey {key} not found in data')

    # 替换{{}}为data中的值
    for key, value in data.items():
        template = template.replace('{{' + key + '}}', str(value))
    return template


def document2string(document: Union[dict, list[dict]], MAX_LENGTH=2048, MIN_VALUE_LENGTH=128) -> str:
    MAX_LENGTH = MAX_LENGTH  # Set your own threshold
    MIN_VALUE_LENGTH = MIN_VALUE_LENGTH  # Set your own threshold
    if isinstance(document, dict):
        document = [document]

    if len(str(document)) > MAX_LENGTH:
        # If the document is too long, only display the keys and the number of data
        keys = ', '.join(document[0].keys())
        summary = f'The document has {len(str(document))} words. Due to the large amount of data, not all information can be displayed. The keys are: {keys}. '
        # Check the length of each value, if it's short enough, display it
        for doc in document:
            for key, value in doc.items():
                if len(str(value)) <= MIN_VALUE_LENGTH:
                    summary += f'{key}: {value}, '
        return summary
    else:
        # If the document is not too long, display all the information
        return str(document)


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


def smart_truncate(data, max_length):
    max_length = 4 * max_length # tokenization will increase the length of the text
    def truncate_non_strings(item):
        if isinstance(item, dict):
            new_dict = {k: truncate_non_strings(v) for k, v in item.items()}
            if all(value == '...' for value in new_dict.values()):
                return '...'  # Collapse entire dict if all values are '...'
            return new_dict
        elif isinstance(item, list):
            new_list = [truncate_non_strings(elem) for elem in item]
            if all(elem == '...' for elem in new_list):
                return '...'  # Collapse entire list if all elements are '...'
            return new_list
        elif isinstance(item, str):
            return item  # Keep strings intact
        else:
            return '...'  # Replace non-string scalar values with '...'

    def truncate_strings(item, max_str_length):
        if isinstance(item, dict):
            new_dict = {k: truncate_strings(v, max_str_length) for k, v in item.items()}
            if all(isinstance(value, str) and value.endswith('...') for value in new_dict.values()):
                return '...'  # Collapse entire dict if all values are truncated strings
            return new_dict
        elif isinstance(item, list):
            new_list = [truncate_strings(elem, max_str_length) for elem in item]
            if all(isinstance(elem, str) and elem.endswith('...') for elem in new_list):
                return '...'  # Collapse entire list if all elements are truncated strings
            return new_list
        elif isinstance(item, str) and len(item) > max_str_length:
            return item[:max_str_length] + '...'  # Truncate long strings
        else:
            return item

    if len(str(data)) <= max_length:
        return json.dumps(data, ensure_ascii=False)
    # First stage: truncate non-string data
    truncated_data = truncate_non_strings(data)
    json_str = json.dumps(truncated_data, ensure_ascii=False)
    

    # Second stage: truncate strings if necessary
    max_str_length = max_length
    # print(f"The data {len(json_str)} truncating the strings to {max_str_length} characters...")
    while len(json_str) > max_length:
        max_str_length -= 1  # Reduce the allowed string length
        truncated_data = truncate_strings(truncated_data, max_str_length)
        json_str = json.dumps(truncated_data, ensure_ascii=False)

    return json_str
def init_logger(name: str, level=logging.ERROR, dump=False, silent=False):
    if silent:
        class empty_logger():
            def __init__(self):
                pass

            def info(self, *args, **kwargs):
                pass

            def debug(self, *args, **kwargs):
                pass

            def warning(self, *args, **kwargs):
                pass

            def error(self, *args, **kwargs):
                pass

            def critical(self, *args, **kwargs):
                pass

        return empty_logger()
    # 创建一个logger
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(level)  # 设置日志级别

    # 定义handler的输出格式
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    color_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        log_colors={
            'DEBUG': 'green',
            'INFO': 'cyan',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    # 创建一个handler，用于输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(color_formatter)
    logger.addHandler(console_handler)

    # 创建一个handler，用于写入日志文件
    if dump:
        if not os.path.exists("logs"):
            os.mkdir("logs")
        file_name = f"logs/{name}.log"
        file_handler = logging.FileHandler(file_name)
        file_handler.setLevel(level)
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

    return logger


def dict2document(dict: dict, db_name: str):
    """
    Convert a dict to a document in Chroma
    return a document
    """
    if db_name == "blueprint":
        page_content = "The building " + dict["description"] + " contains: \n"
        for block in dict["blocks"]:
            page_content += f"{block['name']} at {block['position']} facing {block['facing']}\n"

        return Document(
            page_content=page_content,
            metadata={"tag": dict["description"]},
            title=dict["description"],
        )

    elif db_name == "conversation":
        return Document(
            page_content=dict["content"],
            metadata={"tag": ""},
            title="",
        )

    elif db_name == "requirement":
        return Document(
            page_content=dict["content"],
            metadata={"tag": ""},
            title="",
        )

    else:
        raise NotImplementedError


def load_db_name(db_name, update=False, verbose=False, json_path="", query_type="ParentDocument"):
    if query_type == "ParentDocument":
        if verbose:
            print(f"Loading {db_name}...")
        json_data = json.load(open(json_path, "r"))
        documents = []
        for item in json_data:
            document = dict2document(item, db_name)
            documents.append(document)
        return documents

    else:
        if os.path.exists(f"db_{db_name}/") and not update:
            vectordb = Chroma(persist_directory=f"db_{db_name}/",
                              embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY))
        else:
            if verbose:
                print(f"Loading {db_name}...")
            json_data = json.load(open(json_path, "r"))
            documents = []
            for item in json_data:
                document = dict2document(item, db_name)
                documents.append(document)
            # Split
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
            splits = text_splitter.split_documents(documents)

            # VectorDB
            embedding = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
            vectordb = Chroma.from_documents(documents=splits, embedding=embedding,
                                             persist_directory=f"db_{db_name}/")
    return vectordb


def query_from_db(llm, db_dict, db_name, query="", verbose=False, query_type=""):
    if db_name not in db_dict.keys():
        db_dict[db_name + f"_{query_type}"] = load_db_name(db_name=db_name, update=False, verbose=verbose,
                                                           json_path=f"experience/{db_name}.json",
                                                           query_type=query_type)
    vectordb = db_dict[db_name + f"_{query_type}"]
    if query_type == "SelfQuery":
        metadata_field_info = [
            AttributeInfo(
                name="tag",
                description="the description",
                type="string",
            ),
        ]
        self_query_retriever = SelfQueryRetriever.from_llm(
            llm,
            vectordb,
            f"{db_name}_database",
            metadata_field_info,
        )
        unique_docs = self_query_retriever.invoke(query)
    elif query_type == "ParentDocument":
        # This text splitter is used to create the child documents
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=400)
        # The vectorstore to use to index the child chunks
        vectorstore = Chroma(
            collection_name="full_documents", embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        )
        # The storage layer for the parent documents
        store = InMemoryStore()
        retriever = ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=store,
            child_splitter=child_splitter,
        )
        retriever.add_documents(vectordb, ids=None)
        unique_docs = retriever.get_relevant_documents(query, top_k=1)

    else:
        # MultiQuery
        retriever_from_llm = MultiQueryRetriever.from_llm(
            retriever=vectordb.as_retriever(), llm=llm
        )
        unique_docs = retriever_from_llm.get_relevant_documents(query=query, top_k=1)

    text_results = ""
    for doc in unique_docs:
        text_results += doc.page_content + "\n"
    if verbose:
        print(f"[Debug] {text_results[:10]} ... {text_results[-10:]}\n")

    return f"{text_results}", unique_docs


def flatten_json(y, threshold=200):
    # 这个函数是将任意的json文件转换为一维的dict 方便进行retreival search
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            if len(str(x)) < threshold:
                out[name[:-1]] = x
                # print(x)
            else:
                for a in x:
                    flatten(x[a], name + a + '_')
        elif type(x) is list:
            if len(str(x)) < threshold:
                out[name[:-1]] = str(x)
                # print(x)
            else:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

# if __name__ == "__main__":
#     response = """
# {
#   "subtasks": [
#     {
#       "subtask description": "Gather necessary materials",
#       "milestones": [
#         "Identify the required materials from the blueprint data",
#         "Locate the materials in the vicinity"
#       ],
#       "related data": [
#         "Blueprint data",
#         "Blocks in the vicinity"
#       ]
#     },
#     {
#       "subtask description": "Prepare the construction site",
#       "milestones": [
#         "Identify the location specified in the blueprint data",
#         "Clear the area if necessary",
#         "Ensure the area is suitable for construction"
#       ],
#       "related data": [
#         "Blueprint data",
#         "Current location of the agents"
#       ]
#     },
#     {
#       "subtask description": "Build the construction according to the blueprint",
#       "milestones": [
#         "Follow the blueprint data to place the cut sandstone block at the specified position and facing direction",
#         "Place the terracotta block at the specified position and facing direction",
#         "Install the torch at the specified position and facing direction"
#       ],
#       "related data": [
#         "Blueprint data",
#         "Cut sandstone block",
#         "Terracotta block",
#         "Torch"
#       ]
#     }
#   ]
# }"""
#     result = extract_info(response, ["related data"]) 
#     print(result)
