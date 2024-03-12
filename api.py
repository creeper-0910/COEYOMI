import json

import requests
from requests.exceptions import ConnectionError

import config as cfg

# COEIROINK API

def heartbeat():
    try:
        response = requests.get(
            cfg.engine_api
            )
        return response.json()["status"]
    except ConnectionError as e:
        return "stop"

def genvoice(text,speaker_uuid=cfg.default_uuid, speaker_id=cfg.default_id):
    response = requests.post(
        cfg.engine_api + '/v1/predict',
        json={
            'text': text,
            'speakerUuid': speaker_uuid,
            'styleId': speaker_id,
            'prosodyDetail': None,
            'speedScale': 1
        })
    return response.content

def getspeaker():
    response = requests.get(
        cfg.engine_api + '/v1/speakers'
        )
    return response.json()

def setdict(text,accent):
    response = requests.post(
        cfg.engine_api + '/v1/set_dictionary',
        json={
            'dictionaryWords': []
        })