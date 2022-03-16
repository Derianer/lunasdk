"""
Module realize simple examples following features:
    * redetect one human detection
    * redetect several humans
"""
import asyncio
import pprint

from lunavl.sdk.detectors.base import ImageForRedetection
from lunavl.sdk.faceengine.engine import VLFaceEngine
from lunavl.sdk.image_utils.geometry import Rect
from lunavl.sdk.image_utils.image import VLImage
from resources import EXAMPLE_SEVERAL_FACES, EXAMPLE_O


def detectHumans():
    """
    Redetect human body on images.
    """
    faceEngine = VLFaceEngine()
    detector = faceEngine.createHumanDetector()

    imageWithOneHuman = VLImage.load(filename=EXAMPLE_O)
    detection = detector.detectOne(imageWithOneHuman, detectLandmarks=False)
    pprint.pprint(detector.redetectOne(image=imageWithOneHuman, bBox=detection))
    pprint.pprint(detector.redetectOne(image=imageWithOneHuman, bBox=detection.boundingBox.rect))

    imageWithSeveralHumans = VLImage.load(filename=EXAMPLE_SEVERAL_FACES)
    severalHumans = detector.detect([imageWithSeveralHumans], detectLandmarks=False)

    pprint.pprint(
        detector.redetect(
            images=[
                ImageForRedetection(imageWithSeveralHumans, [human.boundingBox.rect for human in severalHumans[0]]),
                ImageForRedetection(imageWithOneHuman, [detection.boundingBox.rect]),
                ImageForRedetection(imageWithOneHuman, [Rect(0, 0, 100, 100)]),
            ]
        )
    )


async def asyncRedetectHumans():
    """
    Async redetect human body on images.
    """
    faceEngine = VLFaceEngine()
    detector = faceEngine.createHumanDetector()

    imageWithOneHuman = VLImage.load(filename=EXAMPLE_O)
    detection = detector.detectOne(imageWithOneHuman, detectLandmarks=False)
    detection = await detector.redetectOne(image=imageWithOneHuman, bBox=detection, asyncEstimate=True)
    imageWithSeveralHumans = VLImage.load(filename=EXAMPLE_SEVERAL_FACES)
    severalHumans = detector.detect([imageWithSeveralHumans], detectLandmarks=False)

    task1 = detector.redetect(
        images=[
            ImageForRedetection(imageWithSeveralHumans, [human.boundingBox.rect for human in severalHumans[0]]),
        ],
        asyncEstimate=True,
    )
    task2 = detector.redetect(
        images=[
            ImageForRedetection(imageWithOneHuman, [detection.boundingBox.rect]),
        ],
        asyncEstimate=True,
    )
    for task in (task1, task2):
        pprint.pprint(task.get())


if __name__ == "__main__":
    detectHumans()
    asyncio.run(asyncRedetectHumans())
