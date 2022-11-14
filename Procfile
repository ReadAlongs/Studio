# Command for launching the web API server for ReadAlongs-Studio on Heroku
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker readalongs.web_api:web_api_app
