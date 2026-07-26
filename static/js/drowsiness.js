import {
    FaceLandmarker,
    FilesetResolver
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35";


const app =
    document.getElementById(
        "drowsinessApp"
    );

const video =
    document.getElementById(
        "cameraVideo"
    );

const canvas =
    document.getElementById(
        "landmarkCanvas"
    );

const canvasContext =
    canvas.getContext(
        "2d"
    );

const cameraPlaceholder =
    document.getElementById(
        "cameraPlaceholder"
    );

const cameraBadge =
    document.getElementById(
        "cameraBadge"
    );

const alertOverlay =
    document.getElementById(
        "alertOverlay"
    );

const startButton =
    document.getElementById(
        "startButton"
    );

const stopButton =
    document.getElementById(
        "stopButton"
    );

const awakeButton =
    document.getElementById(
        "awakeButton"
    );

const awakeOverlayButton =
    document.getElementById(
        "awakeOverlayButton"
    );

const statusMessage =
    document.getElementById(
        "statusMessage"
    );

const faceValue =
    document.getElementById(
        "faceValue"
    );

const eyeValue =
    document.getElementById(
        "eyeValue"
    );

const earValue =
    document.getElementById(
        "earValue"
    );

const closedDurationValue =
    document.getElementById(
        "closedDurationValue"
    );


const MEDIAPIPE_VERSION =
    "0.10.35";

const WASM_ROOT =
    "https://cdn.jsdelivr.net/npm/" +
    "@mediapipe/tasks-vision@" +
    MEDIAPIPE_VERSION +
    "/wasm";

const MODEL_URL =
    "https://storage.googleapis.com/" +
    "mediapipe-models/face_landmarker/" +
    "face_landmarker/float16/latest/" +
    "face_landmarker.task";


const EAR_THRESHOLD = 0.25;

const DROWSINESS_DURATION_MS =
    3000;

const INFERENCE_INTERVAL_MS =
    80;

const AWAKE_COOLDOWN_MS =
    3000;


const LEFT_EYE = [
    33,
    160,
    158,
    133,
    153,
    144
];

const RIGHT_EYE = [
    362,
    385,
    387,
    263,
    373,
    380
];


let faceLandmarker = null;

let mediaStream = null;

let detectionRunning = false;

let animationFrameId = null;

let lastVideoTime = -1;

let lastInferenceTime = 0;

let eyesClosedSince = null;

let drowsinessDetected = false;

let awakeCooldownUntil = 0;

let audioUnlocked = false;


const alarmAudio =
    new Audio(
        app.dataset.alarmUrl
    );

alarmAudio.loop = true;

alarmAudio.preload = "auto";


function updateStatus(
    message,
    type = "info"
) {

    statusMessage.textContent =
        message;

    statusMessage.className =
        "status-message mb-3";

    if (type !== "info") {

        statusMessage
            .classList
            .add(type);
    }
}


function setDetectionValues({
    faceDetected = false,
    eyesClosed = false,
    ear = 0,
    closedDurationMs = 0
}) {

    faceValue.textContent =
        faceDetected
            ? "Detected"
            : "Not Detected";

    eyeValue.textContent =
        faceDetected
            ? (
                eyesClosed
                    ? "Closed"
                    : "Open"
            )
            : "Waiting";

    earValue.textContent =
        Number(ear)
            .toFixed(3);

    closedDurationValue.textContent =
        (
            closedDurationMs / 1000
        ).toFixed(1) + " s";
}


function resetDetectionState() {

    eyesClosedSince = null;

    drowsinessDetected = false;

    alertOverlay
        .classList
        .remove("active");

    awakeButton.disabled = true;

    stopAlarm();

    setDetectionValues({});
}


async function unlockAlarm() {

    if (audioUnlocked) {
        return;
    }

    try {

        alarmAudio.volume = 0;

        await alarmAudio.play();

        alarmAudio.pause();

        alarmAudio.currentTime = 0;

        alarmAudio.volume = 1;

        audioUnlocked = true;

    } catch (error) {

        console.warn(
            "Alarm audio could not be unlocked:",
            error
        );
    }
}


async function startAlarm() {

    if (!alarmAudio.paused) {
        return;
    }

    try {

        alarmAudio.currentTime = 0;

        await alarmAudio.play();

    } catch (error) {

        console.error(
            "Unable to play alarm:",
            error
        );

        updateStatus(
            "Drowsiness detected, but the browser blocked alarm audio.",
            "danger"
        );
    }
}


function stopAlarm() {

    alarmAudio.pause();

    alarmAudio.currentTime = 0;
}


function landmarkDistance(
    firstPoint,
    secondPoint
) {

    const horizontal =
        (
            firstPoint.x -
            secondPoint.x
        ) * video.videoWidth;

    const vertical =
        (
            firstPoint.y -
            secondPoint.y
        ) * video.videoHeight;

    return Math.hypot(
        horizontal,
        vertical
    );
}


function calculateEyeAspectRatio(
    landmarks,
    eyeIndices
) {

    const point1 =
        landmarks[
            eyeIndices[0]
        ];

    const point2 =
        landmarks[
            eyeIndices[1]
        ];

    const point3 =
        landmarks[
            eyeIndices[2]
        ];

    const point4 =
        landmarks[
            eyeIndices[3]
        ];

    const point5 =
        landmarks[
            eyeIndices[4]
        ];

    const point6 =
        landmarks[
            eyeIndices[5]
        ];

    const firstVertical =
        landmarkDistance(
            point2,
            point6
        );

    const secondVertical =
        landmarkDistance(
            point3,
            point5
        );

    const horizontal =
        landmarkDistance(
            point1,
            point4
        );

    if (horizontal <= 0) {
        return 0;
    }

    return (
        firstVertical +
        secondVertical
    ) / (
        2 * horizontal
    );
}


function drawEyeLandmarks(
    landmarks
) {

    if (
        canvas.width !==
        video.videoWidth
        ||
        canvas.height !==
        video.videoHeight
    ) {

        canvas.width =
            video.videoWidth;

        canvas.height =
            video.videoHeight;
    }

    canvasContext.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );

    const eyeIndices = [
        ...LEFT_EYE,
        ...RIGHT_EYE
    ];

    canvasContext.fillStyle =
        "#22c55e";

    canvasContext.strokeStyle =
        "#facc15";

    canvasContext.lineWidth = 2;

    for (
        const eye of [
            LEFT_EYE,
            RIGHT_EYE
        ]
    ) {

        canvasContext.beginPath();

        eye.forEach(
            (
                landmarkIndex,
                position
            ) => {

                const landmark =
                    landmarks[
                        landmarkIndex
                    ];

                const x =
                    landmark.x *
                    canvas.width;

                const y =
                    landmark.y *
                    canvas.height;

                if (position === 0) {

                    canvasContext
                        .moveTo(
                            x,
                            y
                        );

                } else {

                    canvasContext
                        .lineTo(
                            x,
                            y
                        );
                }
            }
        );

        canvasContext.closePath();

        canvasContext.stroke();
    }

    eyeIndices.forEach(
        landmarkIndex => {

            const landmark =
                landmarks[
                    landmarkIndex
                ];

            const x =
                landmark.x *
                canvas.width;

            const y =
                landmark.y *
                canvas.height;

            canvasContext.beginPath();

            canvasContext.arc(
                x,
                y,
                3,
                0,
                Math.PI * 2
            );

            canvasContext.fill();
        }
    );
}


function clearLandmarks() {

    canvasContext.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );
}


async function createFaceLandmarker() {

    if (faceLandmarker) {
        return;
    }

    updateStatus(
        "Loading MediaPipe face model..."
    );

    const vision =
        await FilesetResolver
            .forVisionTasks(
                WASM_ROOT
            );

    const options = {
        baseOptions: {
            modelAssetPath:
                MODEL_URL,

            delegate:
                "GPU"
        },

        runningMode:
            "VIDEO",

        numFaces:
            1,

        minFaceDetectionConfidence:
            0.5,

        minFacePresenceConfidence:
            0.5,

        minTrackingConfidence:
            0.5,

        outputFaceBlendshapes:
            false,

        outputFacialTransformationMatrixes:
            false
    };

    try {

        faceLandmarker =
            await FaceLandmarker
                .createFromOptions(
                    vision,
                    options
                );

    } catch (gpuError) {

        console.warn(
            "GPU initialization failed. Retrying with CPU.",
            gpuError
        );

        delete options
            .baseOptions
            .delegate;

        faceLandmarker =
            await FaceLandmarker
                .createFromOptions(
                    vision,
                    options
                );
    }
}


async function startDetection() {

    if (detectionRunning) {
        return;
    }

    startButton.disabled = true;

    startButton.textContent =
        "Loading...";

    try {

        if (
            !navigator.mediaDevices
            ||
            !navigator.mediaDevices
                .getUserMedia
        ) {

            throw new Error(
                "This browser does not support camera access."
            );
        }

        await unlockAlarm();

        await createFaceLandmarker();

        mediaStream =
            await navigator
                .mediaDevices
                .getUserMedia({
                    video: {
                        facingMode:
                            "user",

                        width: {
                            ideal: 960
                        },

                        height: {
                            ideal: 720
                        }
                    },

                    audio:
                        false
                });

        video.srcObject =
            mediaStream;

        await video.play();

        detectionRunning =
            true;

        lastVideoTime =
            -1;

        lastInferenceTime =
            0;

        cameraPlaceholder.style.display =
            "none";

        cameraBadge.textContent =
            "Camera On";

        stopButton.disabled =
            false;

        updateStatus(
            "Looking for your face..."
        );

        startButton.textContent =
            "Detection Running";

        animationFrameId =
            requestAnimationFrame(
                detectionLoop
            );

    } catch (error) {

        console.error(
            "Unable to start detection:",
            error
        );

        startButton.disabled =
            false;

        startButton.textContent =
            "▶ Start Detection";

        let errorMessage =
            error.message
            ||
            "Unable to start camera.";

        if (
            error.name ===
            "NotAllowedError"
        ) {

            errorMessage =
                "Camera permission was denied. Allow camera access in browser settings.";
        }

        if (
            error.name ===
            "NotFoundError"
        ) {

            errorMessage =
                "No camera was found on this device.";
        }

        updateStatus(
            errorMessage,
            "danger"
        );
    }
}


function stopDetection() {

    detectionRunning =
        false;

    if (animationFrameId) {

        cancelAnimationFrame(
            animationFrameId
        );

        animationFrameId =
            null;
    }

    if (mediaStream) {

        mediaStream
            .getTracks()
            .forEach(
                track =>
                    track.stop()
            );

        mediaStream =
            null;
    }

    video.srcObject =
        null;

    clearLandmarks();

    resetDetectionState();

    cameraPlaceholder.style.display =
        "flex";

    cameraBadge.textContent =
        "Camera Off";

    startButton.disabled =
        false;

    startButton.textContent =
        "▶ Start Detection";

    stopButton.disabled =
        true;

    updateStatus(
        "Detection stopped."
    );
}


function markAwake() {

    awakeCooldownUntil =
        performance.now() +
        AWAKE_COOLDOWN_MS;

    eyesClosedSince =
        null;

    drowsinessDetected =
        false;

    stopAlarm();

    alertOverlay
        .classList
        .remove("active");

    awakeButton.disabled =
        true;

    closedDurationValue
        .textContent =
        "0.0 s";

    updateStatus(
        "Alert cancelled. Continue looking toward the camera.",
        "success"
    );
}


function handleNoFace() {

    clearLandmarks();

    eyesClosedSince =
        null;

    drowsinessDetected =
        false;

    stopAlarm();

    alertOverlay
        .classList
        .remove("active");

    awakeButton.disabled =
        true;

    setDetectionValues({});

    updateStatus(
        "No face detected. Move into the camera frame.",
        "warning"
    );
}


function handleFace(
    landmarks,
    currentTime
) {

    drawEyeLandmarks(
        landmarks
    );

    const leftEar =
        calculateEyeAspectRatio(
            landmarks,
            LEFT_EYE
        );

    const rightEar =
        calculateEyeAspectRatio(
            landmarks,
            RIGHT_EYE
        );

    const averageEar =
        (
            leftEar +
            rightEar
        ) / 2;

    const eyesClosed =
        averageEar <
        EAR_THRESHOLD;

    let closedDurationMs =
        0;

    if (
        eyesClosed
        &&
        currentTime >=
        awakeCooldownUntil
    ) {

        if (
            eyesClosedSince ===
            null
        ) {

            eyesClosedSince =
                currentTime;
        }

        closedDurationMs =
            currentTime -
            eyesClosedSince;

        if (
            closedDurationMs >=
            DROWSINESS_DURATION_MS
        ) {

            if (
                !drowsinessDetected
            ) {

                drowsinessDetected =
                    true;

                startAlarm();
            }

            alertOverlay
                .classList
                .add("active");

            awakeButton.disabled =
                false;

            updateStatus(
                "Drowsiness detected! Please wake up and stop safely.",
                "danger"
            );

        } else {

            updateStatus(
                "Eyes appear closed. Monitoring duration...",
                "warning"
            );
        }

    } else {

        eyesClosedSince =
            null;

        closedDurationMs =
            0;

        if (drowsinessDetected) {

            stopAlarm();
        }

        drowsinessDetected =
            false;

        alertOverlay
            .classList
            .remove("active");

        awakeButton.disabled =
            true;

        updateStatus(
            "Face detected. Eyes are open.",
            "success"
        );
    }

    setDetectionValues({
        faceDetected:
            true,

        eyesClosed:
            eyesClosed,

        ear:
            averageEar,

        closedDurationMs:
            closedDurationMs
    });
}


function detectionLoop(
    currentTime
) {

    if (!detectionRunning) {
        return;
    }

    if (
        video.readyState >= 2
        &&
        video.currentTime !==
            lastVideoTime
        &&
        currentTime -
            lastInferenceTime >=
            INFERENCE_INTERVAL_MS
    ) {

        lastVideoTime =
            video.currentTime;

        lastInferenceTime =
            currentTime;

        try {

            const result =
                faceLandmarker
                    .detectForVideo(
                        video,
                        currentTime
                    );

            const landmarks =
                result
                    .faceLandmarks
                    ?.[0];

            if (landmarks) {

                handleFace(
                    landmarks,
                    currentTime
                );

            } else {

                handleNoFace();
            }

        } catch (error) {

            console.error(
                "Face detection error:",
                error
            );

            updateStatus(
                "Face detection error. Stop and start detection again.",
                "danger"
            );
        }
    }

    animationFrameId =
        requestAnimationFrame(
            detectionLoop
        );
}


startButton.addEventListener(
    "click",
    startDetection
);

stopButton.addEventListener(
    "click",
    stopDetection
);

awakeButton.addEventListener(
    "click",
    markAwake
);

awakeOverlayButton
    .addEventListener(
        "click",
        markAwake
    );


window.addEventListener(
    "beforeunload",
    stopDetection
);
