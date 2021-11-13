from flask import Flask
import os
from common.storage.storage import Storage
from common.queue.queue import Queue
from common.event.request_dto import Request
from common.event.response_dto import Response
from common.config.config import Configuration
import threading
import random
import logging
import torch
from torch import nn
from torch.autograd import Variable
from torchvision import datasets, transforms, models
from PIL import Image


LOGGER = logging
app = Flask(__name__)
RESULT_MART = dict()
MODEL_EXEC = None


@app.route("/stats", methods=["GET"])
def get_request_stats():
    global RESULT_MART
    return str(RESULT_MART)


def load_model(model_path, device):
    mm = models.resnet18(pretrained=True)
    mm.fc = nn.Linear(in_features=512, out_features=2).to(device)
    cats = mm.load_state_dict(torch.load(model_path, map_location=torch.device(device)))
    return cats


def image_loader(image_path, device):
    imsize = 256
    loader = transforms.Compose([transforms.Scale(imsize), transforms.ToTensor()])
    image = Image.open(image_path)
    image = loader(image).float()
    image = Variable(image, requires_grad=True)
    image = image.unsqueeze(0)
    if device == "cuda":
        return image.cuda()
    else:
        return image.cpu()


def infer():
    global RESULT_MART
    global MODEL_EXEC
    queue = Queue(QUEUE_BACKEND, QUEUE_CONFIG)
    for event in queue.scan_events(QUEUE_RCV_CHANNEL, Request()):
        LOGGER.debug(f"Got inference request with id {event['_id']}")
        resp = Response()
        resp.correlation_id = event['_id']
        image_classes = ["cat", "dog", "neither"]

        try:
            image_path = STORAGE.get_file(event.image_path)
            image = image_loader(image_path, INFERENCE_DEVICE)
            resp.image_class = MODEL_EXEC(image)
        except:
            resp.image_class = random.choice(image_classes)

        if resp.image_class in RESULT_MART:
            RESULT_MART[resp.image_class] += 1
        else:
            RESULT_MART[resp.image_class] = 1

        queue.publish_event(QUEUE_SEND_CHANNEL, resp)


if __name__ == "__main__":
    config = Configuration()
    config.load_config(config_file_path=os.getenv("CONFIG_FILE", default=None))

    # Flask configuration
    APP_HOST = config.categorize_app_host
    APP_PORT = int(config.categorize_app_port)
    LOGLEVEL_DEBUG = config.categorize_app_debug

    # App configuration
    MODEL_PATH = config.categorize_model_path
    INFERENCE_DEVICE = config.categorize_inference_device

    # Integrations configuration
    STORAGE = Storage(backend=config.storage_backend)

    QUEUE_BACKEND = config.queue_backend
    QUEUE_CONFIG = config.queue_config
    QUEUE_SEND_CHANNEL = config.queue_response_channel
    QUEUE_RCV_CHANNEL = config.queue_input_channel

    MODEL_EXEC = load_model(MODEL_PATH, INFERENCE_DEVICE)
    update_thread = threading.Thread(target=infer, name="inference")
    update_thread.start()
    app.run(host=APP_HOST, port=APP_PORT, debug=LOGLEVEL_DEBUG)
