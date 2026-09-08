#include "CaptureBridge.h"
#include "CaptureController.h"
#include "stdio.h"
#include <Windows.h>

struct CaptureControllerOpaque {
    CaptureController* controller;
};

// Create an instance of the capture controller
CaptureControllerRef CreateCaptureController(int id, HWND hwnd, FrameCallback frameCallback, ErrorCallback errorCallback) {
    CaptureControllerOpaque* ref = new CaptureControllerOpaque;
    ref->controller = new CaptureController(id, hwnd, frameCallback, errorCallback);
    return ref;
}

// Start the capture loop
void StartCaptureController(CaptureControllerRef controllerRef) {
    if (controllerRef && controllerRef->controller) {
        controllerRef->controller->StartCapture();
    }
}

// Stop the capture loop
void StopCaptureController(CaptureControllerRef controllerRef) {
    if (controllerRef && controllerRef->controller) {
        controllerRef->controller->StopCapture();
    }
}

// Destroy the controller and clean up resources
void DestroyCaptureController(CaptureControllerRef controllerRef) {
    if (controllerRef) {
        delete controllerRef->controller;
        delete controllerRef;
    }
}
