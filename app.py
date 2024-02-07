import os
import time

from openai import AzureOpenAI

import fastapi
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import json

auth_scheme = HTTPBearer()
app = fastapi.FastAPI()

os.environ["AZURE_OPENAI_ENDPOINT"] = "https://chattool.openai.azure.com"
client = AzureOpenAI(api_key="e9400657633348a8bdb1e9dee3c02908", azure_endpoint="https://chattool.openai.azure.com", api_version="2023-10-01-preview")
deployment_name = "gpt4t"

from fastapi import Body

from pydantic import BaseModel

class QueryModel(BaseModel):
    query: str
    
    
def ask_statesman(query: str):
    #prompt = router(query)

    completion_reason = None
    response = ""
    
    openai_stream = client.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "user", "content": query}],
        temperature=0.0,
        stream=True,
    )
    collected_events = []
    collected_message = ""
    completion_text = ""
    is_correct = None
    judged_flag = 0
    for event in openai_stream:
        
        collected_events.append(event)
        if len(event.choices) == 0:
            continue
        if event.choices[0].finish_reason is not None:
            print(f"finish reason is {event.choices[0].finish_reason}")
            completion_reason = 1
            break
        if event.choices[0].delta.content:
                
            event_text = event.choices[0].delta.content
            collected_message += event_text
            completion_text += event_text  # append the text
            
            if "答案：正确" in completion_text and judged_flag ==0:
                is_correct = 1
                judged_flag = 1
            if "答案：错误" in completion_text and judged_flag ==0:
                is_correct = 0
                judged_flag = 1
            print(f"completion is {completion_text}")
            if is_correct is not None:
                print(f" is cor {is_correct}")
                
                yield sse_pack('message',  event_text, is_correct)
            else:
                yield sse_pack('message',  event_text)
            # yield sse_pack('message', {'content': event_text})
    yield sse_pack('done', {
        'messageId': 1,
        'conversationId': 1,
        'newDocId': 1,
    })
           
@app.get("/")
def read_root():
    return {"Hello": "World"}


def sse_pack(event, message, flag=None):
    # Format data as an SSE message
    packet = "event: %s\n" % event
    data = {'message': message}

    # Only add 'flag' to the data if it is not None
    if flag is not None:
        data['flag'] = flag

    packet += "data: %s\n" % json.dumps(data)
    packet += "\n"
    return packet

@app.post("/")
async def request_handler(query: QueryModel):
    print(f" query is {query}")
    print(f"query is {query.query}")
    stream_response = ask_statesman(query.query)
    response = StreamingResponse(stream_response, media_type="text/event-stream")
    # response['X-Accel-Buffering'] = 'no'
    # response['Cache-Control'] = 'no-cache'
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501, debug=True, log_level="debug")