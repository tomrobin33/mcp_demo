from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.get("/sse")
async def sse_endpoint(request: Request):
    async def event_generator():
        count = 0
        while True:
            # 客户端断开则退出
            if await request.is_disconnected():
                break
            # 这里可以集成文件转换进度推送
            yield f"data: 服务器推送消息 {count}\n\n"
            count += 1
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081) 