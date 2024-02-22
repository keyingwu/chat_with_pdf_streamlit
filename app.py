# Import necessary libraries.
import datetime
import json
import logging
import os

import dotenv
import openai
import streamlit as st
from openai import AzureOpenAI
from PyPDF2 import PdfReader
from streamlit_chat import message

# Configure logging
log_dir = os.getenv("LOG_DIRECTORY", "./")
log_file_path = os.path.join(str(log_dir), "app.log")

logging.basicConfig(
    filename=log_file_path,
    filemode="a",
    format="[%(asctime)s] [%(levelname)s] [%(filename)s] [%(lineno)s:%(funcName)5s()] %(message)s",
    datefmt="%Y-%b-%d %H:%M:%S",
    level=logging.INFO,  # Set your desired log level here, e.g., logging.DEBUG
)
logger = logging.getLogger(__name__)

# region ENV + SDK SETUP
# Set web page title and icon.
st.set_page_config(page_title="Chat 💬 with your PDF 📄", page_icon=":robot:")

# Load environment variables
ENV = dotenv.dotenv_values(".env")
with st.sidebar.expander("Environment Variables"):
    st.write(ENV)

# Set up the Open AI Client

client = AzureOpenAI(
    api_key=ENV["AZURE_OPENAI_KEY"],
    api_version=ENV["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=ENV["AZURE_OPENAI_ENDPOINT"],
)
# endregion


default_prompt = """
You are an AI assistant  that helps users write concise\
 reports on sources provided according to a user query.\
 You will provide reasoning for your summaries and deductions by\
 describing your thought process. You will highlight any conflicting\
 information between or within sources. Greet the user by asking\
 what they'd like to investigate.
"""

system_prompt = st.sidebar.text_area("System Prompt", default_prompt, height=200)
seed_message = {"role": "system", "content": system_prompt}
# endregion

# region SESSION MANAGEMENT
# Initialise session state variables
if "generated" not in st.session_state:
    st.session_state["generated"] = []
if "past" not in st.session_state:
    st.session_state["past"] = []
if "messages" not in st.session_state:
    st.session_state["messages"] = [seed_message]
if "model_name" not in st.session_state:
    st.session_state["model_name"] = []
if "cost" not in st.session_state:
    st.session_state["cost"] = []
if "total_tokens" not in st.session_state:
    st.session_state["total_tokens"] = []
if "total_cost" not in st.session_state:
    st.session_state["total_cost"] = 0.0
if "pdf_added_to_prompt" not in st.session_state:
    st.session_state["pdf_added_to_prompt"] = False

# endregion

# Upload the PDF file.
pdf = st.file_uploader("Upload your PDF", type=["pdf"])
raw_text = ""
if pdf is not None:
    # Extract text from the uploaded PDF file.
    pdf_reader = PdfReader(pdf)
    for page in pdf_reader.pages:
        raw_text += page.extract_text()
else:
    st.session_state["pdf_added_to_prompt"] = False  # Reset the flag

# region SIDEBAR SETUP

counter_placeholder = st.sidebar.empty()
counter_placeholder.write(
    f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}"
)
clear_button = st.sidebar.button("Clear Conversation", key="clear")

if clear_button:
    st.session_state["generated"] = []
    st.session_state["past"] = []
    st.session_state["messages"] = [seed_message]
    st.session_state["number_tokens"] = []
    st.session_state["model_name"] = []
    st.session_state["cost"] = []
    st.session_state["total_cost"] = 0.0
    st.session_state["total_tokens"] = []
    st.session_state["pdf_added_to_prompt"] = False
    # clear pdf if it was uploaded
    pdf = None
    counter_placeholder.write(
        f"Total cost of this conversation: £{st.session_state['total_cost']:.5f}"
    )


download_conversation_button = st.sidebar.download_button(
    "Download Conversation",
    data=json.dumps(st.session_state["messages"]),
    file_name=f"conversation.json",
    mime="text/json",
)

# endregion


def generate_response(prompt):
    if (
        raw_text is not None
        and raw_text != ""
        and not st.session_state["pdf_added_to_prompt"]
    ):
        prompt = "Here is the information from PDF file: " + raw_text + "\n\n" + prompt
        st.session_state["pdf_added_to_prompt"] = True  # Update the flag

    # The rest of your function's code...

    st.session_state["messages"].append({"role": "user", "content": prompt})
    # if the raw_text is not empty, add it into the prompt

    try:

        completion = client.chat.completions.create(
            model=ENV["AZURE_OPENAI_CHATGPT_DEPLOYMENT"],
            messages=st.session_state["messages"],
            temperature=0,
        )
        response = completion.choices[0].message.content
    except openai.APIError as e:
        response = f"The API could not handle this content: {str(e)}"
        st.write(response)
    st.session_state["messages"].append({"role": "assistant", "content": response})

    # print(st.session_state['messages'])
    total_tokens = completion.usage.total_tokens
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    return response, total_tokens, prompt_tokens, completion_tokens


st.title("Streamlit Azure OpenAI Demo")

# container for chat history
response_container = st.container()
# container for text box
container = st.container()

with container:
    with st.form(key="my_form", clear_on_submit=True):
        user_input = st.text_area("You:", key="input", height=100)
        submit_button = st.form_submit_button(label="Send")

    if submit_button and user_input:
        output, total_tokens, prompt_tokens, completion_tokens = generate_response(
            user_input
        )
        logger.info(
            f"User input: {user_input}, output: {output}, total tokens: {total_tokens}, prompt tokens: {prompt_tokens}, completion tokens: {completion_tokens}"
        )

        st.session_state["past"].append(user_input)
        st.session_state["generated"].append(output)
        st.session_state["model_name"].append(ENV["AZURE_OPENAI_CHATGPT_DEPLOYMENT"])
        st.session_state["total_tokens"].append(total_tokens)

        # from https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/#pricing
        cost = total_tokens * 0.0015 / 1000

        st.session_state["cost"].append(cost)
        st.session_state["total_cost"] += cost


if st.session_state["generated"]:
    with response_container:
        for i in range(len(st.session_state["generated"])):
            message(
                st.session_state["past"][i],
                is_user=True,
                key=str(i) + "_user",
                avatar_style="shapes",
            )
            message(
                st.session_state["generated"][i], key=str(i), avatar_style="identicon"
            )
        counter_placeholder.write(
            f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}"
        )
