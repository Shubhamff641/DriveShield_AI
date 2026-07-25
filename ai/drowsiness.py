import pygame
import cv2
import math
import mediapipe as mp

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode


options = FaceLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="models/face_landmarker.task"
    ),
    running_mode=VisionRunningMode.IMAGE,
    num_faces=1,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False
)


landmarker = FaceLandmarker.create_from_options(options)
pygame.mixer.init()
pygame.mixer.music.load("static/sounds/alarm.mp3")

alarm_playing = False
EAR_THRESHOLD = 0.25
CLOSED_FRAMES = 30

closed_counter = 0
def detect_face(frame):

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    result = landmarker.detect(mp_image)

    return result

def draw_landmarks(frame, result):

    if not result.face_landmarks:
        return frame

    h, w, _ = frame.shape

    for face_landmarks in result.face_landmarks:

        for landmark in face_landmarks:

            x = int(landmark.x * w)
            y = int(landmark.y * h)

            cv2.circle(
                frame,
                (x, y),
                1,
                (0, 255, 0),
                -1
            )

    # Add these lines here
    ear = get_ear(result)

    if ear is not None:

        cv2.putText(
            frame,
            f"EAR: {ear:.3f}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

    return frame

    return frame
def distance(p1, p2):

    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2
    )
def calculate_ear(eye):

    vertical1 = distance(eye[1], eye[5])
    vertical2 = distance(eye[2], eye[4])

    horizontal = distance(eye[0], eye[3])

    ear = (vertical1 + vertical2) / (2 * horizontal)

    return ear
def get_ear(result):

    if not result.face_landmarks:
        return None

    face = result.face_landmarks[0]

    left_eye = [
        face[33],
        face[160],
        face[158],
        face[133],
        face[153],
        face[144]
    ]

    right_eye = [
        face[362],
        face[385],
        face[387],
        face[263],
        face[373],
        face[380]
    ]

    left_ear = calculate_ear(left_eye)
    right_ear = calculate_ear(right_eye)

    ear = (left_ear + right_ear) / 2

    return ear
def detect_drowsiness(result):

    global closed_counter
    global alarm_playing

    ear = get_ear(result)

    if ear is None:
        return False, None

    if ear < EAR_THRESHOLD:
        closed_counter += 1
    else:
        closed_counter = 0

        if alarm_playing:
            pygame.mixer.music.stop()
            alarm_playing = False

    if closed_counter >= CLOSED_FRAMES:

        if not alarm_playing:
            pygame.mixer.music.play(-1)
            alarm_playing = True

        return True, ear

    return False, ear