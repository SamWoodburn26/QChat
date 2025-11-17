import azure.functions as func
import logging
from chat import main as chat_handler

app = func.FunctionApp()

@app.function_name(name="chat")
@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    return chat_handler(req)