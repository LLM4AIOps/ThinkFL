import json
import sys
import traceback

import requests

from llm import chat_api
from tools import print_result_function, search_traces_function, search_fluctuating_metrics_function


def pack_get_parameter(d):
    try:
        if type(d) is str:
            d = json.loads(d)
        result = ""
        for k, v in d.items():
            result += k.strip() + "=" + str(v).strip() + "&"
        return result[:-1]
    except Exception as e:
        return ""


base_tool_path = "http://127.0.0.1:5000"


def get_response(path, parameters):
    url = base_tool_path + "/" + path + "?" + pack_get_parameter(parameters)
    try:
        response = requests.get(url)
        return response.content.decode('utf-8')
    except:
        return ""


def get_tool_names(tools):
    names = []
    for tool in tools:
        if "function" in tool:
            names.append(tool["function"]["name"])
        else:
            names.append(tool["name"])
    return names


def get_tool_from_content(content, tool_names):
    tools = []
    lines = content.split("\n")
    name = None
    for line in lines:
        if line.startswith("Action: "):
            name = line[len("Action: "):]
        elif line.startswith("✿FUNCTION✿: "):
            name = line[len("✿FUNCTION✿: "):]
        elif line.startswith("✿ARGS✿: "):
            arguments = line[len("✿ARGS✿: "):]
            if name in tool_names:
                tools.append({
                    "function": {
                        "name": name,
                        "arguments": arguments
                    }
                })
        elif line.startswith("Action Input: "):
            arguments = line[len("Action Input: "):]
            if name in tool_names:
                tools.append({
                    "function": {
                        "name": name,
                        "arguments": arguments
                    }
                })
    return tools


def inspect_trace(root_trace_line, sub_path):
    print("=" * 50)
    print(root_trace_line)

    root_prompt = '''Please read the following root trace and identify corresponding root cause service.
            A possible approach is to recursively search for the traces you suspect have issues, and combine with metrics data to confirm the root cause.''' + root_trace_line
    think_process = [root_prompt]
    prompts = [{"role": "user", "content": root_prompt}]
    res_content = chat_api(prompts, tools=[search_traces_function])
    res_tools = get_tool_from_content(res_content, get_tool_names([search_traces_function]))

    # initial think
    while res_tools and len(res_tools) > 0 and res_tools[0]["function"]["name"] != "print_results":
        think_process.append(res_content)
        prompts.append({"role": "assistant", "content": str(res_tools)})
        for tool in res_tools:
            print("think:" + str(tool))
            tool_result = get_response(tool["function"]["name"], tool["function"]["arguments"])
            think_process.append(tool_result)
            prompts.append({"role": "assistant", "content": tool_result})
            round_prompt = '''Please continue to further identify the root cause service.
                        You may use the provided tools or choose not to.
                        If you use the trace tool, we often find that the root cause originates from a specific downstream trace.
                        If you have already define the root cause service, just call the print_result function.
                                    '''
            think_process.append(round_prompt)
            prompts.append({"role": "user", "content": round_prompt})
            res_content = chat_api(prompts, tools=[print_result_function, search_traces_function])
            res_tools = get_tool_from_content(res_content,
                                              get_tool_names([print_result_function, search_traces_function]))
    print(res_content)
    think_process.append(res_content)
    prompts.append({"role": "user", "content": str(res_tools[0]["function"])})

    rethink_prompt = '''We think it's better to inspect more deeper into the trace tree. So, even you have already define the root cause service, you must use the following tool to inspect more deeper to confirm that there are no deeper root cause.
                                    '''
    think_process.append(rethink_prompt)
    prompts.append({"role": "user", "content": rethink_prompt})
    res_content = chat_api(prompts, tools=[search_traces_function])
    res_tools = get_tool_from_content(res_content, get_tool_names([search_traces_function]))
    # rethink
    while res_tools and len(res_tools) > 0 and res_tools[0]["function"]["name"] != "print_results":
        think_process.append(res_content)
        prompts.append({"role": "assistant", "content": str(res_tools)})
        for tool in res_tools:
            print("rethink:" + str(tool))
            tool_result = get_response(tool["function"]["name"], tool["function"]["arguments"])
            think_process.append(tool_result)
            prompts.append({"role": "assistant", "content": tool_result})
            round_prompt = '''Please continue to further identify the root cause service.\n
                                    You may inspect deeper by search trace tool or combine with metrics data to confirm the root cause.\n
                                    If you use the trace tool, we often find that the root cause originates from a specific downstream trace.\n
                                    If you have already define the root cause service, just call the print_result function.
                                    '''
            think_process.append(round_prompt)
            prompts.append({"role": "user", "content": round_prompt})
            res_content = chat_api(prompts, tools=[print_result_function, search_traces_function,
                                                   search_fluctuating_metrics_function])
            res_tools = get_tool_from_content(res_content, get_tool_names(
                [print_result_function, search_traces_function, search_fluctuating_metrics_function]))
    print(res_content)
    think_process.append(res_content)
    if res_tools and len(res_tools) > 0:
        prompts.append({"role": "assistant", "content": str(res_tools[0]["function"])})
    else:
        prompts.append({"role": "assistant", "content": res_content})
    final_think_prompt = '''Please rethink the above think process and return the correct root cause and reason by the print_result function.\n
            '''

    think_process.append(final_think_prompt)
    prompts.append({"role": "user", "content": final_think_prompt})
    res_content = chat_api(prompts, tools=[print_result_function])
    res_tools = get_tool_from_content(res_content, get_tool_names([print_result_function]))
    think_process.append(res_content)
    prompts.append({"role": "assistant", "content": str(res_tools)})
    print(res_content)
    return think_process


def inspect_all_traces(sub_path):
    error_file_path = f"data/{sub_path}/hipstershop.Frontend/Recv._durations.txt"
    fr = open(error_file_path, "r")
    lines = fr.readlines()
    for i in range(1, len(lines)):
        try:
            if sub_path == "2022-03-20-cloudbed3" and i <= 107:
                continue
            root_trace = lines[0] + lines[i]
            think_processes = inspect_trace(root_trace, sub_path)

            conversation_file_path = f"data/{sub_path}/result/conversation_trace_{i}.txt"
            with open(conversation_file_path, 'w') as file:
                for think_process in think_processes:
                    file.write(str(think_process) + "\n")
        except Exception as e:
            traceback.print_exc()
            print(e)
            i -= 1


if __name__ == "__main__":
    # inspect_all_traces("2022-03-20-cloudbed1")
    inspect_all_traces(sys.argv[1])
