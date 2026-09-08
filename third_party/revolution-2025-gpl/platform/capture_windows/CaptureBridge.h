#pragma once

#include <Windows.h> // Required for HWND

#ifdef __cplusplus
extern "C" {
#endif
    // Define the opaque type for the capture controller
    typedef struct CaptureControllerOpaque* CaptureControllerRef;

    typedef void (*FrameCallback)(int id, unsigned char* rgbaData, int length, int width, int height, int stride);
    typedef void (*ErrorCallback)(int id, const char* errorMessage);

    CaptureControllerRef CreateCaptureController(int id, HWND hwnd, FrameCallback frameCallback, ErrorCallback errorCallback);

    void StartCaptureController(CaptureControllerRef controller);

    void StopCaptureController(CaptureControllerRef controller);

    void DestroyCaptureController(CaptureControllerRef controller);
#ifdef __cplusplus
}
#endif
