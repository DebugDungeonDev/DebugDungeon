import glob
import os

import yaml

from frontend.frontend_update import FrontendUpdate
from frontend.run_code import run_code
from interview_master.interview_master import InterviewMaster
from interview_master.scenario import Scenario
from llm.chat import Message
from llm.clients.gemini import Gemini
import requests
import random 
import subprocess
import json
import shlex


IM: InterviewMaster = None

safe_chars = "abcdefghijklmnopqrstuvwxyz .,"

def update_video_feed(state):
    # Run the curl command using a subprocess
    text = state["chat"].get_last_bot_message()
    
    safe_escaped_text = [c for c in text if c.lower() in safe_chars]
    safe_escaped_text = "".join(safe_escaped_text)

    command = f"""
    curl -X POST http://localhost:5000/switch_video -H "Content-Type: application/json" -d '{{"text": "{safe_escaped_text}"}}'
    """

    print("Command being sent:\n", command)

    subprocess.run(command, shell=True)

    r = random.randint(0, 1000000)

    state['video'] = f"""
    <video id="digital_human" 
           autoplay 
           muted 
           controls 
           style="width: 100%; height: auto; border-radius: 10px;">
        <source src="http://localhost:5000/combined_feed?nocache={r}" type="video/mp4">
    </video>
    """

def update_state_from_fru(state, fru):
    state["chat"] = fru.chat
    state["code"] = fru.code
    state["code_output"] = fru.code_output
    state["current_task"] = fru.current_task
    return state


def save_code(code, state):
    state["code"] = code
    return state, state["code"], state["code_output"]

def run_the_code(code, state):
    state["code"] = code
    state["code_output"] = run_code(code)
    return state, state["code"], state["code_output"]

def submit_code(code, state):
    state["code"] = code
    state["code_output"] = run_code(code)

    FRU = IM.handle_code_submission(Gemini("llm/clients/google.key"), FrontendUpdate(state["chat"], state["code"], state["code_output"], state["current_task"]))
    state = update_state_from_fru(state, FRU)

    task_details = f"### Task {IM.task_manager.previous_tasks.__len__() + 1}: **{FRU.current_task.name}**\n\n{FRU.current_task.description}"

    return state["code"], state["code_output"], task_details, state["chat"].to_history(), state


def handle_chat(user_input, state):
    global IM
    chat = state["chat"]  # Get the chat from state

    # Append user input to chat
    chat.messages.append(Message(True, user_input))  # True means it's from the human

    # Simulate an AI response (replace with your AI model here)
    FRU = IM.handle_chat_message(Gemini("llm/clients/google.key"), FrontendUpdate(chat, state["code"], state["code_output"], state["current_task"]))
    state = update_state_from_fru(state, FRU)

    task_details = f"### Task {IM.task_manager.previous_tasks.__len__() + 1}: **{FRU.current_task.name}**\n\n{FRU.current_task.description}"
    # Return updated chat history and clear user input

    update_video_feed(state)

    return state["code"], state["code_output"], task_details, state["chat"].to_history(), state, "", state["video"]


def update_selected_scenario(selected_scenario, state):
    global IM
    # Get scenario names
    #iterate through the scenarios folder until find a name that matches
    scenarios_path = "scenarios"
    scenario_files = glob.glob(os.path.join(scenarios_path, "*.yaml"))
    print("Scenario files found:", scenario_files)  # Debugging
    for scenario_file in scenario_files:
        # store it as name : path
        print("Checking scenario file:", scenario_file)
        with open(scenario_file, "r") as f:
            scenario_data = yaml.safe_load(f)
            if scenario_data["name"] == selected_scenario:
                selected_scenario_file = scenario_file
                break

    state["scenario_name"] = selected_scenario  # No need for `.value`

    # Load scenario into InterviewMaster
    IM = InterviewMaster(Scenario(Gemini("llm/clients/google.key"), selected_scenario_file))
    FRU = IM.handle_start()

    task_details = f"### Task {IM.task_manager.previous_tasks.__len__() + 1}: **{FRU.current_task.name}**\n\n{FRU.current_task.description}"
    state = update_state_from_fru(state, FRU)



    return state["code"], state["code_output"], task_details, state["chat"].to_history(), state # , state['video']