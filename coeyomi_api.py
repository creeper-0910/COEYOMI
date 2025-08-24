from urllib.parse import urljoin

import aiohttp


# TODO:レスポンス200以外の処理
class COEIROINK_API:
    def __init__(self, api_url: str):
        self.url = api_url

    async def heartbeat(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    response_data = await response.json()
                    return response_data["status"]
        except aiohttp.ClientConnectorError:
            return "stop"

    async def getspeaker(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(urljoin(self.url, "/v1/speakers")) as response:
                return await response.json()

    async def getprosody(self, text):
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url + "/v1/estimate_prosody", json={"text": text}) as response:
                response_data = await response.json()
                return response_data["detail"]

    async def setdict(self,dicts):
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url + "/v1/set_dictionary", json={"dictionaryWords": dicts}):
                return None

    async def getpredictwithduration(
        self, text: str, speaker_uuid: str, speaker_id: int, prosody
    ):
        async with aiohttp.ClientSession() as session:
            async with session.post(
            self.url + "/v1/predict_with_duration",
            json={
                "speakerUuid": speaker_uuid,
                "styleId": speaker_id,
                "text": text,
                "prosodyDetail": prosody,
                "speedScale": 1,
            },
            ) as response:
                return await response.json()

    async def genvoice(
        self,
        text: str,
        speaker_uuid: str,
        speaker_id: int,
        pitch: float = 0.00,
        intonation: float = 1.00,
        algorithm: str = "world",
    ):
        prosody = await self.getprosody(text)
        prdwithdur = await self.getpredictwithduration(
            text, speaker_uuid, speaker_id, prosody
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url + "/v1/process",
            json={
                "volumeScale": 1,
                "pitchScale": pitch,
                "intonationScale": intonation,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
                "outputSamplingRate": 44100,
                "sampledIntervalValue": 3,
                "processingAlgorithm": algorithm,
                "startTrimBuffer": prdwithdur["startTrimBuffer"],
                "endTrimBuffer": prdwithdur["endTrimBuffer"],
                "pauseLength": 0,
                "pauseStartTrimBuffer": 0.1,
                "pauseEndTrimBuffer": 0,
                "wavBase64": prdwithdur["wavBase64"],
                "moraDurations": prdwithdur["moraDurations"],
            }) as response:
                return await response.read()
