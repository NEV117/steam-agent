from typing_extensions import Annotated
import autogen
import os
import agentops
from dotenv import load_dotenv
from agentops.sdk.decorators import session, agent, operation

# Cargar variables de entorno
load_dotenv()

# Configurar AWS Bedrock
llm_config_bedrock = autogen.LLMConfig(
    api_type="bedrock",
    model="anthropic.claude-3-5-sonnet-20240620-v1:0",
    aws_region="us-east-1",
    aws_access_key=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_key=os.getenv("AWS_SECRET_KEY"),
    price=[0.003, 0.015],
    temperature=0.1,
    cache_seed=None,  # desactivar caching
)

# Crear los agentes de Autogen
assistant = autogen.AssistantAgent("assistant", llm_config=llm_config_bedrock)
user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", ""),
    max_consecutive_auto_reply=3,
    llm_config=llm_config_bedrock
)

# Inicializar AgentOps con la API Key y tags por defecto
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
agentops.init(AGENTOPS_API_KEY, default_tags=["AWS_Bedrock-Claude-3"])

# Definir un agente personalizado para rastrear la operación de chat
@agent(name="ChatAgent")
class ChatAgent:
    @operation
    def initiate_chat_operation(self):
        # Realiza la operación de chat utilizando el agente user_proxy
        return user_proxy.initiate_chat(
            assistant,
            message="Write a python program to print the first 10 numbers of the Fibonacci sequence. Just output the python code, no additional information.",
        )

# Definir el flujo de trabajo en una sesión para que las operaciones se tracen correctamente
@session
def chat_workflow():
    chat_agent = ChatAgent()
    return chat_agent.initiate_chat_operation()

# Ejecutar el flujo de trabajo
result = chat_workflow()

# Finalizar la sesión de AgentOps indicando el estado de la ejecución
agentops.end_session("Success")
