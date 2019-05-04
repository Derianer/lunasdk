"""
Module contains function for detection faces on images.
"""
from enum import Enum
from typing import Optional, Union, List, NamedTuple, Dict

from FaceEngine import ObjectDetectorClassType, DetectionType, Face  # pylint: disable=E0611,E0401
from FaceEngine import Landmarks5 as CoreLandmarks5  # pylint: disable=E0611,E0401
from FaceEngine import Landmarks68 as CoreLandmarks68  # pylint: disable=E0611,E0401
from FaceEngine import DetectionFloat, FSDKError  # pylint: disable=E0611,E0401
from FaceEngine import dt5Landmarks, dt68Landmarks  # pylint: disable=E0611,E0401

from lunavl.sdk.estimators.base_estimation import BaseEstimation
from ..errors.errors import ErrorInfo
from ..errors.exceptions import LunaSDKException
from ..image_utils.geometry import Rect, Landmarks
from ..image_utils.image import VLImage, ColorFormat


class ImageForDetection(NamedTuple):
    """
    Structure for the transfer to detector an image and detect an area.

    Attributes
        image (VLImage): image for detection
        detectArea (Rect[float]):
    """
    image: VLImage
    detectArea: Rect[float]


class DetectorType(Enum):
    """
    Detector types enum
    """
    FACE_DET_DEFAULT = "FACE_DET_DEFAULT"  #: what is default?
    FACE_DET_V1 = "FACE_DET_V1"  #: todo description
    FACE_DET_V2 = "FACE_DET_V2"
    FACE_DET_V3 = "FACE_DET_V3"

    @property
    def coreDetectorType(self) -> ObjectDetectorClassType:
        """
        Convert  self to core detector type

        Returns:
            ObjectDetectorClassType
        """
        return getattr(ObjectDetectorClassType, self.value)


class Landmarks5(Landmarks):
    """
    Landmarks5
    """

    def __init__(self, coreLandmark5: CoreLandmarks5):
        """
        Init

        Args:
            coreLandmark5: core landmarks
        """
        super().__init__(coreLandmark5)


class Landmarks68(Landmarks):
    """
    Landmarks68
    """

    def __init__(self, coreLandmark68: CoreLandmarks68):
        """
        Init

        Args:
            coreLandmark68: core landmarks
        """
        super().__init__(coreLandmark68)


class BoundingBox(BaseEstimation):
    """
    Detection bounding box, it is characterized of rect and score:

        - rect (Rect[float]): face bounding box
        - score (float): face score (0,1), detection score is the measure of classification confidence
                         and not the source image quality. It may be used topick the most "*confident*" face of many.
    """

    def __init__(self, boundingBox: DetectionFloat):
        """
        Init.

        Args:
            boundingBox: core bounding box
        """
        super().__init__(boundingBox)

    @property
    def score(self) -> float:
        """
        Get score

        Returns:
            number in range [0,1]
        """
        return self._coreEstimation.score

    @property
    def rect(self) -> Rect[float]:
        """
        Get rect.

        Returns:
            float rect
        """
        return Rect.fromCoreRect(self._coreEstimation.rect)


class FaceDetection(BaseEstimation):
    """
    Attributes:
        boundingBox (BoundingBox): face bounding box
        landmarks5 (Optional[Landmarks5]): optional landmarks5
        landmarks68 (Optional[Landmarks68]): optional landmarks5
        _image (VLImage): source of detection

    """
    __slots__ = ("boundingBox", "landmarks5", "landmarks68", "_coreDetection", "_image", "_emotions",
                 "_quality", "_mouthState")

    def __init__(self, coreDetection: Face, image: VLImage):
        """
        Init.

        Args:
            coreDetection: core detection
        """
        super().__init__(coreDetection)

        self.boundingBox = BoundingBox(coreDetection.detection)
        if coreDetection.landmarks5_opt.isValid():
            self.landmarks5 = Landmarks5(coreDetection.landmarks5_opt.value())
        else:
            self.landmarks5 = None

        if coreDetection.landmarks68_opt.isValid():
            self.landmarks68 = Landmarks68(coreDetection.landmarks68_opt.value())
        else:
            self.landmarks68 = None
        self._image = image
        self._emotions = None
        self._quality = None
        self._mouthState = None

    @property
    def image(self) -> VLImage:
        """
        Get source of detection.

        Returns:
            source image
        """
        return self._image

    def asDict(self) -> Dict[str, Union[dict, list]]:
        """
        Convert face detection to dict (json).

        Returns:
            dict. required keys: 'rect', 'score'. optional keys: 'landmarks5', 'landmarks68'
        """
        res = {"rect": self.boundingBox.rect.asDict(), "score": self.boundingBox.score}
        if self.landmarks5 is not None:
            res["landmarks5"] = [point.asDict() for point in self.landmarks5.points]
        if self.landmarks68 is not None:
            res["landmarks68"] = [point.asDict() for point in self.landmarks68.points]
        # TODO: may be nullable landmarks5?
        return res


class FaceDetector:
    """
    Face detector.

    Attributes:
        _detector (IDetectorPtr): core detector

    """
    __slots__ = ["_detector", "detectorType"]

    def __init__(self, detectorPtr, detectorType: DetectionType):
        self._detector = detectorPtr
        self.detectorType = detectorType

    @staticmethod
    def _getDetectionType(detect5Landmarks: bool = True, detect68Landmarks: bool = False) -> DetectionType:
        """
        Get  core detection type

        Args:
            detect5Landmarks: detect or not landmarks5
            detect68Landmarks: detect or not landmarks68

        Returns:
            detection type
        """
        toDetect = 0

        if detect5Landmarks:
            toDetect = toDetect | dt5Landmarks
        if detect68Landmarks:
            toDetect = toDetect | dt68Landmarks

        return DetectionType(toDetect)

    def detectOne(self, image: VLImage, detectArea: Optional[Rect[float]] = None, detect5Landmarks: bool = True,
                  detect68Landmarks: bool = False) -> Union[None, FaceDetection]:
        """
        Detect just one best detection on the image.

        Args:
            image: image. Format must be R8G8B8 (todo check)
            detectArea: rectangle area which contains face to detect. If not set will be set image.rect
            detect5Landmarks: detect or not landmarks5
            detect68Landmarks: detect or not landmarks68
        Returns:
            face detection if face is found otherwise None
        Raises:
            LunaSDKException: if detectOne is failed
        """
        if detectArea is None:
            _detectArea = image.coreImage.getRect()
        else:
            _detectArea = detectArea.coreRect

        detectRes = self._detector.detectOne(image.coreImage, _detectArea,
                                             self._getDetectionType(detect5Landmarks, detect68Landmarks))
        if detectRes[0].isError:
            if detectRes[0].FSDKError == FSDKError.BufferIsEmpty:
                return None
            error = ErrorInfo.fromSDKError(123, "detection", detectRes[0])
            raise LunaSDKException(error)
        coreDetection = detectRes[1]
        if not coreDetection.detection.isValid():
            raise ValueError("WTF bad rect")  # todo check
        return FaceDetection(coreDetection, image)

    def detect(self, images: List[Union[VLImage, ImageForDetection]], limit: int = 5, detect5Landmarks: bool = True,
               detect68Landmarks: bool = False) -> List[List[FaceDetection]]:
        """
        Batch detect faces on images.

        Args:
            images: input images list. Format must be R8G8B8
            limit: max number of detections per input image
            detect5Landmarks: detect or not landmarks5
            detect68Landmarks: detect or not landmarks68
        Returns:
            return list of lists detection, order of detection lists is corresponding to order input images
        Raises:
            LunaSDKException: if any image has bad format or detect is failed

        """
        imgs = []
        detectAreas = []
        for image in images:

            if isinstance(image, VLImage):
                img = image
                detectArea = image.coreImage.getRect()
            else:
                img = image[0]
                detectArea = image[1].coreRect
            if img.format != ColorFormat.R8G8B8:
                error = ErrorInfo(126, "bad format",
                                  "Bad image format for detection {}, img {}".format(img.format.value, img.format))
                raise LunaSDKException(error)
            imgs.append(img.coreImage)
            detectAreas.append(detectArea)

        detectRes = self._detector.detect(imgs, detectAreas, limit,
                                          self._getDetectionType(detect5Landmarks, detect68Landmarks))
        if detectRes[0].isError:
            raise LunaSDKException(ErrorInfo.fromSDKError(124, "detection", detectRes[0]))
        res = []
        for numberImage, imageDetections in enumerate(detectRes[1]):
            res.append([FaceDetection(coreDetection, images[numberImage]) for coreDetection in imageDetections])
        return res

    def redetectOne(self):
        """
        todo: wtf
        Returns:

        """
        pass

    def redect(self):
        """
        todo: wtf
        Returns:

        """
        pass

    def setDetectionComparer(self):
        """
        todo: wtf
        Returns:

        """
        pass
