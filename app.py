import json
import os

import boto3
import requests as r
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request


def current_account() -> str:
    CONFIG = json.loads(os.environ.get("AWS_CONFIG", "{}"))
    config = Config(connect_timeout=5, retries={"max_attempts": 0})

    sts = boto3.client("sts", config=config, **CONFIG)
    return sts.get_caller_identity()["Account"]


def current_region() -> str:
    session = boto3.session.Session()
    return session.region_name


# Pull config
codeartifact_region = os.getenv("CODEARTIFACT_REGION") or current_region()
codeartifact_account_id = os.environ.get("CODEARTIFACT_ACCOUNT_ID") or current_account()

assert all((codeartifact_account_id, codeartifact_region))

codeartifact_domain = os.environ["CODEARTIFACT_DOMAIN"]
codeartifact_repository = os.environ["CODEARTIFACT_REPOSITORY"]

# Make flask
app = Flask(__name__)
if auth_incoming := os.getenv("PROXY_AUTH"):
    from flask_basicauth import BasicAuth

    username, password = auth_incoming.split(":")
    app.config["BASIC_AUTH_USERNAME"] = username
    app.config["BASIC_AUTH_PASSWORD"] = password
    app.config["BASIC_AUTH_FORCE"] = True
    basic_auth = BasicAuth(app)


# Token management
client = boto3.client("codeartifact", region_name=codeartifact_region)
AUTH_TOKEN: str


def update_auth_token():
    global AUTH_TOKEN
    AUTH_TOKEN = client.get_authorization_token(
        domain=codeartifact_domain,
        domainOwner=codeartifact_account_id,
        durationSeconds=43200,
    )["authorizationToken"]
    app.logger.info("Got new token")
    app.logger.debug("New token: " + AUTH_TOKEN)


def generate_url(path: str) -> str:
    if path.startswith("/"):
        path = path[1:]
    return f"https://aws:{AUTH_TOKEN}@{codeartifact_domain}-{codeartifact_account_id}.d.codeartifact.{codeartifact_region}.amazonaws.com/pypi/{codeartifact_repository}/simple/{path}"


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>", methods=["GET", "POST"])
def proxy(path):
    app.logger.info(f"{request.method} {request.path}")

    if request.method == "GET":
        response = r.get(f"{generate_url(path)}")
        return response.content
    elif request.method == "POST":
        response = r.post(f"{generate_url(path)}", json=request.get_json())
        return response.content

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


if __name__ == "__main__":
    update_auth_token()

    scheduler = BackgroundScheduler()
    job = scheduler.add_job(update_auth_token, "interval", seconds=21600)
    scheduler.start()

    app.run(host="0.0.0.0", port=5000)
