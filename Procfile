# Command for launching the web API server for ReadAlongs-Studio on Heroku
web: gunicorn --workers 5 --worker-class uvicorn.workers.UvicornWorker readalongs.web_api:web_api_app
