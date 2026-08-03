from modal_entry import app


@app.function()
def check():
    import sys

    sys.path.insert(0, "/root/backend")
    import appwrite

    print("APPWRITE_VERSION", appwrite.__version__)
    from agent_arena.main import app as fast
    from agent_arena.config import settings

    print("ENV_PROJECT", settings()["APPWRITE_PROJECT_ID"])
    print("SMOKE_IMPORT_OK", fast.title)
