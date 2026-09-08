#include "base.h"

#if defined(IS_MACOSX)

#include <mach/mach.h>
#include <mach/mach_time.h>
#include <unistd.h>
#include <stdio.h>

void microsleep(int ms, int* interrupt) {
    static mach_timebase_info_data_t timebaseInfo;
    mach_timebase_info(&timebaseInfo);
    uint64_t start = mach_continuous_time();

    for (;;) {
        usleep(0);
        if (*interrupt > 0) {break;}
        uint64_t now = mach_continuous_time();
        uint64_t nanos = (now - start) * (timebaseInfo.numer / timebaseInfo.denom);
        if (nanos / 1e6 >= ms) {break;}
    }
}

void move_mouse(int x, int y) {
    CGEventRef get = CGEventCreate(NULL);
    CGPoint mouse = CGEventGetLocation(get);

    CGPoint position = { .x = x - mouse.x, .y = y - mouse.y};
    CGEventRef move = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, position, kCGMouseButtonLeft);

    CGEventPost(kCGSessionEventTap, move);
    CFRelease(move);
}

void scroll_mouse(int x, int y) {
		CGEventRef event;
		event = CGEventCreateScrollWheelEvent(NULL, kCGScrollEventUnitPixel, 2, y, x);
		CGEventPost(kCGHIDEventTap, event);
		CFRelease(event);
}

void send_key_event(int pid, bool down, int key) {
    CGEventRef eventDown, eventUp;
    bool isFn = key == 0x74 || key == 0x75;

    if (isFn) {
        eventDown = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)63, true);
        CGEventPost(kCGHIDEventTap, eventDown);
        CFRelease(eventDown);
    }

    CGEventRef keyEvent = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)key, down);
    assert(keyEvent != NULL);

    CGEventSetType(keyEvent, down ? kCGEventKeyDown : kCGEventKeyUp);
    if (pid == 0) {
        CGEventPost(kCGSessionEventTap, keyEvent);
    } else {
        CGEventPostToPid(pid, keyEvent);
    }
    CFRelease(keyEvent);

    if (isFn) {
        eventUp = CGEventCreateKeyboardEvent(NULL, (CGKeyCode)63, false);
        CGEventPost(kCGHIDEventTap, eventUp);
        CFRelease(eventUp);
    }
}

void attach_input_thread(int pid) {
    // noop
}

#endif
#if defined(IS_WINDOWS)
#include <windows.h>
#include <stdbool.h>
#include <stdio.h>
#include <tlhelp32.h>
#include <stdio.h>

void microsleep(int ms, int* interrupt) {

}

void move_mouse(int x, int y) {
    SetCursorPos(x, y);
}

void scroll_mouse(int x, int y) {
    INPUT input = { 0 };
    input.type = INPUT_MOUSE;

    if (y != 0) {
        input.mi.dwFlags = MOUSEEVENTF_WHEEL;
        input.mi.mouseData = y * WHEEL_DELTA;
        SendInput(1, &input, sizeof(INPUT));
    }

    if (x != 0) {
        input.mi.dwFlags = MOUSEEVENTF_HWHEEL;
        input.mi.mouseData = x * WHEEL_DELTA;
        SendInput(1, &input, sizeof(INPUT));
    }
}

void attach_input_thread(int pid) {
    HANDLE hSnapshot;
    THREADENTRY32 te32;
    DWORD targetThreadId = 0;
    DWORD currentThreadId = GetCurrentThreadId();

    // Take a snapshot of all threads in the system
    hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE) {
        printf("Failed to create thread snapshot.\n");
        return;
    }

    te32.dwSize = sizeof(THREADENTRY32);

    // Retrieve the first thread
    if (Thread32First(hSnapshot, &te32)) {
        do {
            if (te32.th32OwnerProcessID == pid) {
                targetThreadId = te32.th32ThreadID;
                break;
            }
        } while (Thread32Next(hSnapshot, &te32));
    } else {
        printf("Failed to retrieve the first thread.\n");
        CloseHandle(hSnapshot);
        return;
    }

    CloseHandle(hSnapshot);

    if (targetThreadId == 0) {
        printf("No threads found for process ID %d.\n", pid);
        return;
    }

    printf("Attaching current thread (TID: %lu) to target thread (TID: %lu)\n",
           currentThreadId, targetThreadId);

    // Attach the input threads
    if (!AttachThreadInput(currentThreadId, targetThreadId, TRUE)) {
        printf("Failed to attach input threads.\n");
    }
}

void send_key_event(int extended, bool down, int key) {
    INPUT input = { 0 };
    input.type = INPUT_KEYBOARD;

    input.ki.wScan = key;
    input.ki.dwFlags = KEYEVENTF_SCANCODE;

    if (extended) {
        input.ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
    }

    if (!down) {
        input.ki.dwFlags |= KEYEVENTF_KEYUP;
    }

    // Send the input event
    UINT result = SendInput(1, &input, sizeof(INPUT));
    if (result == 0) {
        DWORD error = GetLastError();
        printf("SendInput failed with error code: %lu\n", error);
    }
}
#endif