#include "base.h"
#include <stdio.h>

typedef struct Frame {
    int width;
    int height;
    int x;
    int y;
    float scale;
} Frame;

typedef struct Frames {
    int len;
    Frame* frames;
} Frames;

typedef struct Screenshot {
    size_t width;
    size_t height;
    size_t stride;

    unsigned int len;
    unsigned char* data;
} Screenshot;

#if defined(IS_MACOSX)

static Boolean(*gAXIsProcessTrustedWithOptions) (CFDictionaryRef);
static CFStringRef* gkAXTrustedCheckOptionPrompt;

static bool check_ax_enabled(bool showPrompt) {
    // Statically load all required functions one time
    static dispatch_once_t once; dispatch_once (&once,
    ^{
        // Open the frameworkw
        void* handle = dlopen("/System/Library/Frameworks/Application"
            "Services.framework/ApplicationServices", RTLD_LAZY);

        // Validate the handle
        if (handle != NULL) {
            *(void**) (&gAXIsProcessTrustedWithOptions) = dlsym (handle, "AXIsProcessTrustedWithOptions");
            gkAXTrustedCheckOptionPrompt = (CFStringRef*) dlsym (handle, "kAXTrustedCheckOptionPrompt");
        }
    });

    // Check for new OSX 10.9 function
    if (gAXIsProcessTrustedWithOptions) {
        // Check whether to show prompt
        CFBooleanRef displayPrompt = showPrompt ? kCFBooleanTrue : kCFBooleanFalse;

        // Convert display prompt value into a dictionary
        const void* k[] = { *gkAXTrustedCheckOptionPrompt };
        const void* v[] = { displayPrompt };
        CFDictionaryRef o = CFDictionaryCreate(NULL, k, v, 1, NULL, NULL);

        // Determine whether the process is actually trusted
        bool result = (*gAXIsProcessTrustedWithOptions)(o);
        // Free memory
        CFRelease(o);
        return result;
    } else {
        // Ignore deprecated warnings
        #pragma clang diagnostic push
        #pragma clang diagnostic ignored "-Wdeprecated-declarations"

        // Check whether we have accessibility access
        return AXAPIEnabled() || AXIsProcessTrusted();
        #pragma clang diagnostic pop
    }
}

extern AXError _AXUIElementGetWindow(AXUIElementRef, CGWindowID* out);

typedef struct Window {
	AXUIElementRef window;
	CGWindowID     id;
} Window;

static int get_display_count() {
	CGDirectDisplayID displays[32];
	uint32_t count;

    if (CGGetActiveDisplayList(32, displays, &count) != kCGErrorSuccess)
    {
        return -1;
    }

    return count;
}

static Frames* get_display_frames() {
	CGDirectDisplayID displays[32];
	uint32_t count;

    if (CGGetActiveDisplayList(32, displays, &count) != kCGErrorSuccess)
    {
        return NULL;
    }


    Frames* frames = malloc(sizeof(Frames));
    Frame* data = malloc(sizeof(Frame) * count);
    frames->len = count;
    frames->frames = data;

    for (int i = 0; i < count; i++) {
        CGFloat scaleFactor = 1.0;
        CGDisplayModeRef mode = CGDisplayCopyDisplayMode(displays[i]);
        size_t pixelWidth = CGDisplayModeGetPixelWidth(mode);
        size_t pointWidth = CGDisplayModeGetWidth(mode);

        if (pointWidth != 0) {
            scaleFactor = (CGFloat)pixelWidth / (CGFloat)pointWidth;
        }

        CFRelease(mode);
    	CGRect bounds = CGDisplayBounds(displays[i]);

    	Frame *frame = malloc(sizeof(Frame));
    	frame->width = (int)bounds.size.width;
    	frame->height = (int)bounds.size.height;
    	frame->x = bounds.origin.x;
    	frame->y = bounds.origin.y;
    	frame->scale = scaleFactor;
    	data[i] = *frame;
    }

    return frames;
}

static void set_window_frame(const Window* window, const int width, const int height, const int x, const int y) {
	CGPoint* position = malloc(sizeof(CGPoint));
	position->x = x;
	position->y = y;
	CFTypeRef positionStorage = AXValueCreate(kAXValueCGPointType, position);
	AXUIElementSetAttributeValue(window->window, (CFStringRef)kAXPositionAttribute, positionStorage);
	CFRelease(positionStorage);
	free(position);
	
	CGSize* size = malloc(sizeof(CGSize));
	size->width = width;
	size->height = height;

	CFTypeRef sizeStorage = AXValueCreate(kAXValueCGSizeType, size);
	AXUIElementSetAttributeValue(window->window, (CFStringRef)kAXSizeAttribute, sizeStorage);
	CFRelease(sizeStorage);
	free(size);
}

static Frame* get_window_frame(const Window* window) {
    if (!window || !window->window) {
        return NULL;
    }

    CFTypeRef sizeStorage = NULL;
    CFTypeRef positionStorage = NULL;
    Frame* frame = NULL;

    AXError result = AXUIElementCopyAttributeValue(window->window,
                                                   (CFStringRef)kAXSizeAttribute,
                                                   &sizeStorage);

    CGSize size = CGSizeZero;
    if (result == kAXErrorSuccess && sizeStorage) {
        if (!AXValueGetValue(sizeStorage, kAXValueCGSizeType, (void *)&size)) {
            size = CGSizeZero;
        }
        CFRelease(sizeStorage);
        sizeStorage = NULL;
    }

    result = AXUIElementCopyAttributeValue(window->window,
                                           (CFStringRef)kAXPositionAttribute,
                                           &positionStorage);

    CGPoint topLeft = CGPointZero;
    if (result == kAXErrorSuccess && positionStorage) {
        if (!AXValueGetValue(positionStorage, kAXValueCGPointType, (void *)&topLeft)) {
            topLeft = CGPointZero;
        }
        CFRelease(positionStorage);
        positionStorage = NULL;
    }

    frame = (Frame*)malloc(sizeof(Frame));
    if (!frame) {
        return NULL;
    }

    frame->width = size.width;
    frame->height = size.height;
    frame->x = topLeft.x;
    frame->y = topLeft.y;

    return frame;
}

static void activate_window(const Window* window) {
	if (AXUIElementPerformAction(window->window, kAXRaiseAction) != kAXErrorSuccess) {
		pid_t pid = 0;
		if (AXUIElementGetPid(window->window, &pid) != kAXErrorSuccess || !pid) { return; }

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"

		ProcessSerialNumber psn;
		if (GetProcessForPID(pid, &psn) == 0) {
			SetFrontProcessWithOptions(&psn, kSetFrontProcessFrontWindowOnly);
		}

#pragma clang diagnostic pop
	}
}

static int get_window_count(pid_t pid) {
    AXUIElementRef application = AXUIElementCreateApplication(pid);
    if (application == NULL) {
        return 0;
    }

    CFArrayRef windows = NULL;
    if (AXUIElementCopyAttributeValues(application, kAXWindowsAttribute, 0, 1024, &windows) != kAXErrorSuccess) {
        CFRelease(application);
        return 0;
    }

    int count = 0;
    if (windows != NULL) {
        count = CFArrayGetCount(windows);
        CFRelease(windows);
    }

    CFRelease(application);
    return count;
}

static Window* get_window_with_pid(pid_t pid) {
	AXUIElementRef application = AXUIElementCreateApplication(pid);
	if (application == 0) {return NULL;}

	CFArrayRef windows = NULL;
	// Get all windows associated with the app
	AXUIElementCopyAttributeValues(application, kAXWindowsAttribute, 0, 1024, &windows);
	CGWindowID win = 0;

	if (windows != NULL) {
		int count = CFArrayGetCount(windows);
		if (count == 1) {
            AXUIElementRef element = (AXUIElementRef) CFArrayGetValueAtIndex(windows, 0);

			CGWindowID temp = 0;
			_AXUIElementGetWindow(element, &temp);

            CFRetain(element);
            CFRelease(windows);
            Window* window = malloc(sizeof(window));
            window->window = element;
            window->id = temp;
            return window;
		}
	}

	return NULL;
};
#endif
#if defined(IS_WINDOWS)
#include <windows.h>
#include <shlwapi.h>
#include <shellscalingapi.h>
#include <stdlib.h>
#include <stdio.h>

#pragma comment(lib, "Shcore.lib")
typedef struct Window {
	DWORD pid;
	HWND hwnd;
} Window;

typedef struct WindowCount {
	DWORD pid;
	int windowCount;
} WindowCount;

static int get_display_count() {
	int displayCount = GetSystemMetrics(SM_CMONITORS);
	if (displayCount <= 0) {
		return 0;
	}
    return displayCount;
}

static Screenshot* screenshot_window(const Window* window) {
    if (!window || !window->hwnd) {
        printf("exit 1\n");
        return NULL;  // Invalid input
    }

    // Get the client area dimensions
    RECT clientRect;
    if (!GetClientRect(window->hwnd, &clientRect)) {
        printf("exit 2\n");
        return NULL;  // Failed to get client rect
    }

    // Convert client coordinates to screen coordinates
    POINT topLeft = {clientRect.left, clientRect.top};
    POINT bottomRight = {clientRect.right, clientRect.bottom};
    MapWindowPoints(window->hwnd, NULL, &topLeft, 1);
    MapWindowPoints(window->hwnd, NULL, &bottomRight, 1);

    int windowWidth = bottomRight.x - topLeft.x;
    int windowHeight = bottomRight.y - topLeft.y;

    // Get the screen DC
    HDC hScreenDC = GetDC(NULL);
    if (!hScreenDC) {
        return NULL;
    }

    // Create a memory DC and compatible bitmap
    HDC hMemoryDC = CreateCompatibleDC(hScreenDC);
    if (!hMemoryDC) {
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    HBITMAP hBitmap = CreateCompatibleBitmap(hScreenDC, windowWidth, windowHeight);
    if (!hBitmap) {
        DeleteDC(hMemoryDC);
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    HBITMAP hOldBitmap = (HBITMAP)SelectObject(hMemoryDC, hBitmap);

    // Copy the client area from the screen to the memory DC
    if (!BitBlt(hMemoryDC, 0, 0, windowWidth, windowHeight, hScreenDC, topLeft.x, topLeft.y, SRCCOPY)) {
        SelectObject(hMemoryDC, hOldBitmap);
        DeleteObject(hBitmap);
        DeleteDC(hMemoryDC);
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    // Retrieve bitmap information
    BITMAP bitmap;
    if (!GetObject(hBitmap, sizeof(BITMAP), &bitmap)) {
        SelectObject(hMemoryDC, hOldBitmap);
        DeleteObject(hBitmap);
        DeleteDC(hMemoryDC);
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    // Calculate stride and data size
    size_t stride = ((windowWidth * 3) + 3) & ~3;  // Align stride to 4 bytes
    size_t dataSize = stride * windowHeight;

    unsigned char* bgrData = (unsigned char*)malloc(dataSize);
    if (!bgrData) {
        SelectObject(hMemoryDC, hOldBitmap);
        DeleteObject(hBitmap);
        DeleteDC(hMemoryDC);
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    // Retrieve pixel data using GetDIBits
    BITMAPINFOHEADER bi = {0};
    bi.biSize = sizeof(BITMAPINFOHEADER);
    bi.biWidth = windowWidth;
    bi.biHeight = -windowHeight; // Negative height for top-down DIB
    bi.biPlanes = 1;
    bi.biBitCount = 24;          // 24-bit BGR format
    bi.biCompression = BI_RGB;

    if (!GetDIBits(hMemoryDC, hBitmap, 0, windowHeight, bgrData, (BITMAPINFO*)&bi, DIB_RGB_COLORS)) {
        free(bgrData);
        SelectObject(hMemoryDC, hOldBitmap);
        DeleteObject(hBitmap);
        DeleteDC(hMemoryDC);
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    // Convert BGR to RGBA
    size_t rgbaSize = windowWidth * windowHeight * 4; // 4 bytes per pixel (RGBA)
    unsigned char* rgbaData = (unsigned char*)malloc(rgbaSize);
    if (!rgbaData) {
        free(bgrData);
        SelectObject(hMemoryDC, hOldBitmap);
        DeleteObject(hBitmap);
        DeleteDC(hMemoryDC);
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    for (int y = 0; y < windowHeight; y++) {
        for (int x = 0; x < windowWidth; x++) {
            size_t bgrIndex = y * stride + x * 3;
            size_t rgbaIndex = (y * windowWidth + x) * 4;

            // Copy BGR to RGBA and set alpha channel to 255
            rgbaData[rgbaIndex + 0] = bgrData[bgrIndex + 2]; // Red
            rgbaData[rgbaIndex + 1] = bgrData[bgrIndex + 1]; // Green
            rgbaData[rgbaIndex + 2] = bgrData[bgrIndex + 0]; // Blue
            rgbaData[rgbaIndex + 3] = 255;                  // Alpha
        }
    }

    free(bgrData);

    // Populate the Screenshot structure
    Screenshot* screenshot = (Screenshot*)malloc(sizeof(Screenshot));
    if (!screenshot) {
        free(rgbaData);
        SelectObject(hMemoryDC, hOldBitmap);
        DeleteObject(hBitmap);
        DeleteDC(hMemoryDC);
        ReleaseDC(NULL, hScreenDC);
        return NULL;
    }

    screenshot->width = windowWidth;
    screenshot->height = windowHeight;
    screenshot->stride = windowWidth * 4; // RGBA stride
    screenshot->len = (unsigned int)rgbaSize;
    screenshot->data = rgbaData;

    // Cleanup
    SelectObject(hMemoryDC, hOldBitmap);
    DeleteObject(hBitmap);
    DeleteDC(hMemoryDC);
    ReleaseDC(NULL, hScreenDC);

    return screenshot;
}

static void set_window_frame(const Window* window, const int width, const int height, const int x, const int y) {
    SetWindowPos(window->hwnd, HWND_TOP, x, y, width, height, SWP_NOZORDER | SWP_NOACTIVATE);
}

static Frame* get_window_frame(const Window* window) {
    RECT rect;
    if (GetWindowRect(window->hwnd, &rect)) {
        Frame *frame = malloc(sizeof(Frame));
    	frame->width = rect.right - rect.left;
    	frame->height = rect.bottom - rect.top;
    	frame->x = rect.left;
        frame->y = rect.top;
        return frame;
    } else {
        return NULL;
    }
}

static void activate_window(const Window* window) {
  if (GetForegroundWindow() != window->hwnd) {
      SetForegroundWindow(window->hwnd);
      for (int i = 0; i < 50; i++) {
          if (GetForegroundWindow() == window->hwnd) {
              return;
          }
          Sleep(10);
      }
  }
}

static BOOL CALLBACK EnumDisplayMonitorsProc(HMONITOR hMonitor, HDC hdcMonitor, LPRECT lprcMonitor, LPARAM dwData) {
	Frames* frames = (Frames*)dwData;
	Frame* data = frames->frames;

	MONITORINFO monitorInfo;
	monitorInfo.cbSize = sizeof(MONITORINFOEX);
	if (GetMonitorInfo(hMonitor, &monitorInfo)) {
		RECT rect = monitorInfo.rcMonitor;
		int width = rect.right - rect.left;
		int height = rect.bottom - rect.top;

		HRESULT hr;
		DEVICE_SCALE_FACTOR scaleFactor;
		hr = GetScaleFactorForMonitor(hMonitor, &scaleFactor);
        if (SUCCEEDED(hr)) {
        	scaleFactor = scaleFactor;
        } else {
          	scaleFactor = SCALE_100_PERCENT;
        }

        Frame *frame = malloc(sizeof(Frame));
    	frame->width = (int)width;
    	frame->height = (int)height;
    	frame->x = rect.left;
    	frame->y = rect.top;
        frame->scale = scaleFactor / 100;
		data[frames->len++] = *frame;
	}

	return TRUE;
}

static Frames* get_display_frames() {
	// Get the number of displays
	int displayCount = GetSystemMetrics(SM_CMONITORS);
	if (displayCount <= 0) {
		return NULL;
	}

	Frames* frames = (Frames*)malloc(sizeof(Frames));
	Frame* data = (Frame*)malloc(sizeof(Frame) * displayCount);
	frames->frames = data;
	frames->len = 0;

	EnumDisplayMonitors(NULL, NULL, EnumDisplayMonitorsProc, (LPARAM)frames);

	return frames;
}

static BOOL CALLBACK EnumWindowVisibleCountProc(HWND hwnd, LPARAM lParam) {
	WindowCount* data = (WindowCount*)lParam;

	DWORD windowPid = 0;
	GetWindowThreadProcessId(hwnd, &windowPid);

	if (windowPid == data->pid && IsWindowVisible(hwnd)) {
		data->windowCount++;
	}

	return TRUE;
}

static BOOL CALLBACK EnumWindowHwndProc(HWND hwnd, LPARAM lParam) {
	Window* window = (Window*)lParam;

	DWORD windowPid = 0;
	GetWindowThreadProcessId(hwnd, &windowPid);

	if (windowPid == window->pid) {
		if (IsWindowVisible(hwnd)) {
			window->hwnd = hwnd;
			return FALSE;
		}
	}
	return TRUE;
}

static int get_window_visible_count(int pid) {
	WindowCount data = { 0 };
	data.pid = pid;
	data.windowCount = 0;

	EnumWindows(EnumWindowVisibleCountProc, (LPARAM)&data);

	return data.windowCount;
}

static Window* get_window_with_pid(int pid) {
	Window* data = malloc(sizeof(Window));
	data->pid = pid;
	data->hwnd = NULL;

	EnumWindows(EnumWindowHwndProc, (LPARAM)data);

	if (data->hwnd == NULL) {
	    return NULL;
	}

	return data;
}
#endif