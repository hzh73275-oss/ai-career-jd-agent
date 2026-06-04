import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(override=True)

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-3.5-turbo-1106")


def build_client() -> OpenAI:
  if not API_KEY:
    raise RuntimeError("未配置 OPENAI_API_KEY。请在 .env 中填写你自己的 API Key 后再使用大模型能力。")

  client_config = {"api_key": API_KEY}
  if BASE_URL:
    client_config["base_url"] = BASE_URL
  return OpenAI(**client_config)


class Chat:
  def __init__(self, system="", model=None):
    self.system = system
    self.model = model or MODEL_NAME
    self.messages = []

    if self.system:
      self.messages.append({"role": "system", "content": self.system})

  def __call__(self, message):
    self.messages.append({"role": "user", "content": message})
    result = self.execute()
    self.messages.append({"role": "assistant", "content": result})
    return result

  def execute(self):
    completion = build_client().chat.completions.create(
      model=self.model,
      messages=self.messages,
      temperature=0.2,
    )
    return completion.choices[0].message.content
