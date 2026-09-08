#ifndef CAPTURE_BRIDGE_H
#define CAPTURE_BRIDGE_H

#include <CoreGraphics/CoreGraphics.h> // For CGWindowID
#include <stddef.h>                    // For size_t
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/// Opaque reference to a capture controller
typedef void* CaptureControllerRef;

typedef void (*FrameCallback)(
    int id,
    unsigned char* data,
    size_t length,
    int width,
    int height,
    int stride
);

/// Creates a new capture controller
CaptureControllerRef CreateCaptureController(void);

/// Releases a capture controller
void ReleaseCaptureController(CaptureControllerRef controllerRef);

/// Sets the frame callback
void SetFrameCallback(CaptureControllerRef controllerRef, FrameCallback cb);

/// Sets the ID
void SetID(CaptureControllerRef controllerRef, int id);

/// Starts capturing the specified CGWindowID
bool StartCapture(CaptureControllerRef controllerRef, CGWindowID windowID);

/// Stops capturing
void StopCapture(CaptureControllerRef controllerRef);

#ifdef __cplusplus
}
#endif

#endif // CAPTURE_BRIDGE_H
