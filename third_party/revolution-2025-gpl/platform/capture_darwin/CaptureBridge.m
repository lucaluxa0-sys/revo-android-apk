#import "CaptureBridge.h"
#import "CaptureController.h" // Our actual Objective-C implementation
#import <ScreenCaptureKit/ScreenCaptureKit.h>

static SCWindow* findSCWindow(CGWindowID windowID) {
    dispatch_semaphore_t sem = dispatch_semaphore_create(0);
    __block SCWindow *found = nil;

    [SCShareableContent getShareableContentWithCompletionHandler:^(SCShareableContent * _Nullable content, NSError * _Nullable error) {
        if (content) {
            for (SCWindow *w in content.windows) {
                if (w.windowID == windowID) {
                    found = w;
                    break;
                }
            }
        }
        dispatch_semaphore_signal(sem);
    }];

    dispatch_semaphore_wait(sem, DISPATCH_TIME_FOREVER);
    return found;
}

CaptureControllerRef CreateCaptureController(void) {
    CaptureController *obj = [[CaptureController alloc] init];
    return (__bridge_retained void*)obj;
}

void ReleaseCaptureController(CaptureControllerRef controllerRef) {
    if (!controllerRef) return;
    CaptureController *obj = (__bridge_transfer CaptureController*)controllerRef;
    obj = nil;
}

void SetFrameCallback(CaptureControllerRef controllerRef, FrameCallback cb) {
    if (!controllerRef) return;
    CaptureController *obj = (__bridge CaptureController*)controllerRef;
    obj.frameCallback = cb;
}

void SetID(CaptureControllerRef controllerRef, int id) {
    if (!controllerRef) return;
    CaptureController *obj = (__bridge CaptureController*)controllerRef;
    obj.id = id;
}


bool StartCapture(CaptureControllerRef controllerRef, CGWindowID windowID) {
    if (!controllerRef) return false;
    CaptureController *obj = (__bridge CaptureController*)controllerRef;
    SCWindow *scWin = findSCWindow(windowID);
    if (!scWin) {
        NSLog(@"Failed to find SCWindow for ID=%u", windowID);
        return false;
    }
    [obj startWindowCapture:scWin];
    return true;
}

void StopCapture(CaptureControllerRef controllerRef) {
    if (!controllerRef) return;
    CaptureController *obj = (__bridge CaptureController*)controllerRef;
    [obj stopCapture];
}
