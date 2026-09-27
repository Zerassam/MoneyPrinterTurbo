import os

import uvicorn
from loguru import logger

from app.config import config

if __name__ == "__main__":
    # Railway injects the public service port at runtime. The local config
    # default remains 8080, but it must not override Railway's dynamic PORT.
    listen_port = int(os.environ.get("PORT", config.listen_port))
    logger.info(
        "start server, docs: http://127.0.0.1:" + str(listen_port) + "/docs"
    )
    # FFmpeg 探测已经移到 app/services/task.py 的共享任务流水线里，这样
    # API、CLI 和 WebUI 三条路径都能统一覆盖，这里不再单独检查。
    uvicorn.run(
        app="app.asgi:app",
        host=config.listen_host,
        port=listen_port,
        reload=config.reload_debug,
        log_level="warning",
    )
