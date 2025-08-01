"""
Main file for the url2_image app
"""

import os
import io
import pathlib
import hashlib
import time
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import WebDriverException, InvalidArgumentException
from selenium import webdriver
from flask import Flask, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
)
from PIL import Image

from url2_image_env import (
    JWT_SECRET_KEY,
    JWT_USER,
    JWT_PASSWORD,
    FLASK_DEBUG,
    USE_LOGIN,
    JWT_ACCESS_TOKEN_EXPIRES,
    SELENIUM_WEB_DRIVER_URL,
)
from login_util import conditional_decorator

# pylint: disable=invalid-name
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = JWT_ACCESS_TOKEN_EXPIRES
app.config["SELENIUM_WEB_DRIVER_URL"] = SELENIUM_WEB_DRIVER_URL
jwt = JWTManager(app)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERSION = "v0.1"

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["2 per minute", "1 per second"],
)

if FLASK_DEBUG:
    limiter.enabled = False

print(f"USE_LOGIN: {USE_LOGIN}")


@conditional_decorator(jwt_required, USE_LOGIN)
@app.route("/")
def hello():
    """
    Return "Hello World" as a default for the "/" route
    """
    return "Hello World"


@conditional_decorator(jwt_required, USE_LOGIN)
@app.route("/version")
def get_version():
    """
    API endpoint to retrieve version information of the service.

    Example:
        The Api endpoint can be queried as follows::

            $ curl "localhost:5000/version"
            $ curl "localhost:5000/version?format=json"

    Args:
        format (str): (Optional) when format=json a json object is returned
    Returns:
        Version information of the service either as plaintext or json. Information contains version number, git hash (one commit behind) and git branch.
    """
    req_format = request.args.get("format")
    sha = ""
    branch = ""
    print(f"Path: {pathlib.Path().absolute()}")
    with open(".git-commit") as f:
        for line in f:
            sha = line

    with open(".git-branch") as f:
        for line in f:
            branch = line

    if req_format == "json":
        response = {"Version": VERSION, "Hash": sha, "Branch": branch}
        return jsonify(response)
    elif req_format is None:
        return f"Version: {VERSION} - Git Hash: {sha} branch: {branch}"
    return "Bad Request", 400


@conditional_decorator(jwt_required, USE_LOGIN)
@app.route("/capture")
def get_image():
    """
    Main API endpoint. This takes in an URL and returns an image.

    Args:
        url (str): The URL of the target website to be downloaded.

        width (int): Width of the target image (default=1920)

        height (int): Height of the target image (default=1080)

        format (str): The format of the target image. Either png or jpg (default=png)

        quality (int): JPEG Quality from 0 to 100 (default=60)

        timeout (int): Timeout in seconds (default=60)

        delay (int): Delay in seconds (default=0)

        fullPage (bool): Whether to download the whole page (default=False)    Returns:
        A bytestream containing the downloaded website as image
    """
    req_url = request.args.get("url")
    if req_url is None:
        return "Bad Request", 400

    req_width = 1920
    if request.args.get("width") is not None:
        req_width = int(request.args.get("width"))

    req_height = 1080
    if request.args.get("height") is not None:
        req_height = int(request.args.get("height"))

    delay = 0
    if request.args.get("delay") is not None:
        delay = int(request.args.get("delay")) / 1000

    firefox_opts = Options()
    firefox_opts.add_argument(f"--width={req_width}")
    firefox_opts.add_argument(f"--height={req_height}")
    firefox_opts.add_argument("--disable-gpu")
    browser_driver = webdriver.Remote(
        command_executor=SELENIUM_WEB_DRIVER_URL, options=firefox_opts
    )
    try:
        browser_driver.get(req_url)
    except (WebDriverException, InvalidArgumentException) as e:
        browser_driver.quit()
        return f"Bad Request: {e}", 400
    fname = hashlib.md5(req_url.encode("utf-8")).hexdigest()
    destination = os.path.join(BASE_DIR, "tmp_images", fname + ".png")

    if request.args.get("fullPage") in ["True", "true"]:
        longest_height = (
            browser_driver.find_element("tag name", "body").size["height"] + 1000
        )
        browser_driver.set_window_size(req_width, longest_height)
    time.sleep(delay)
    if browser_driver.save_screenshot(destination):
        print("File saved in the destination filename")
    browser_driver.quit()

    req_format = "png"
    if request.args.get("format") is not None:
        # never trust user input
        wanted_format = request.args.get("format")
        if "jpg" in wanted_format:
            req_format = "jpg"

    req_quality = 60
    if request.args.get("quality") is not None:
        req_quality = int(request.args.get("quality"))

    if req_format == "jpg":
        im = Image.open(destination)
        rgb_im = im.convert("RGB")
        destination = os.path.join(BASE_DIR, "tmp_images", fname + ".jpg")
        rgb_im.save(destination, quality=req_quality, optimize=True, progressive=True)
        with open(destination, "rb") as f:
            return send_file(
                io.BytesIO(f.read()),
                download_name="url.jpg",
                mimetype="image/jpg",
            )

    with open(destination, "rb") as f:
        return send_file(
            io.BytesIO(f.read()), download_name="url.png", mimetype="image/png"
        )

    return "Image download error", 500


@app.route("/login", methods=["POST"])
def login():
    """
    Login the user using flask_jwt_extented. Accepts json as input and returns an access token.
    The configuration can be set via environment variables:

    - JWT_SECRET_KEY: The secret key for JWT

    - JWT_USER: The username of the JWT login. Default: user

    - JWT_PASSWORD: The password for the JWT login. Default: url2image

    - USE_LOGIN: Enables/Disables the requirement for login via JWT. Default: True

    - JWT_ACCESS_TOKEN_EXPIRES: The expiration time (in seconds) of `False` for no expiration of the JWT. Default: False

    A basic login can be achieved via::

        curl -H "Content-Type: application/json" -X POST -d '{"username":"user", "password":"url2image" }' "http://localhost:5000/login"
        {
            "access_token": "TOKEN"
        }

    The authorization is then done in the header::

        curl -H "Authorization: Bearer TOKEN" "http://localhost:5000/getImage?url=google.de"

    Args:

        username: The username to login

        password: The users password

    Returns:
        The generated access token.
    """
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get("username", None)
    password = request.json.get("password", None)

    if not username:
        return jsonify({"msg": "Missing username parameter"}), 400

    if not password:
        return jsonify({"msg": "Missing password parameter"}), 400

    if username != JWT_USER or password != JWT_PASSWORD:
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0")
# pylint: enable=invalid-name
