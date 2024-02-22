import os

import dotenv
from openai import AzureOpenAI

# Load environment variables
ENV = dotenv.dotenv_values(".env")
client = AzureOpenAI(
    api_key=ENV["AZURE_OPENAI_KEY"],
    api_version=ENV["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=ENV["AZURE_OPENAI_ENDPOINT"],
)

response = client.chat.completions.create(
    model="gpt-35-turbo",  # model = "deployment_name".
    messages=[
        {
            "role": "system",
            "content": "Assistant is a large language model trained by OpenAI.",
        },
        {"role": "user", "content": "Who were the founders of Microsoft?"},
    ],
)

# print(response)
print(response.model_dump_json(indent=2))
print(response.choices[0].message.content)
