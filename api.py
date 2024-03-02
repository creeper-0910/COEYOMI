import requests

import config as cfg

# COEIROINK API

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

def setdict(text,accent):
    response = requests.post(
        cfg.engine_api + '/predict',
        json={
            'dictionaryWords': []
        })