/*
 * Copyright (c) 2024
 * Author: Liam Sagi
 */

#include "CaptureController.h"
#include <dxgi.h>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <thread>
#include <algorithm>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")

static void SafeRelease(IUnknown* obj) {
    if (obj) obj->Release();
}

CaptureController::CaptureController(int id,
    HWND hwnd,
    CaptureCallback captureCb,
    ErrorCallback errorCb)
    : id_(id),
    hwnd_(hwnd),
    captureCallback_(captureCb),
    errorCallback_(errorCb),
    running_(false),
    device_(nullptr),
    context_(nullptr),
    duplication_(nullptr) {
}

CaptureController::~CaptureController() {
}

void CaptureController::StartCapture() {
    if (!initDuplication()) {
        reportError("Failed to initialize duplication.");
        return;
    }
    if (running_) return;
    running_ = true;
    thread_ = std::thread(&CaptureController::captureLoop, this);
}

void CaptureController::StopCapture() {
  	if (!running_) return;
    running_ = false;
    if (thread_.joinable()) {
        thread_.join();
    }
    cleanupDuplication();
}

bool CaptureController::initDuplication() {
    // Get the monitor for the HWND
    RECT rc;
    if (!GetWindowRect(hwnd_, &rc)) {
        reportError("GetWindowRect failed.");
        return false;
    }
    HMONITOR hMon = MonitorFromWindow(hwnd_, MONITOR_DEFAULTTONEAREST);
    if (!hMon) {
        reportError("MonitorFromWindow returned null.");
        return false;
    }

    // Create DXGI factory
    IDXGIFactory1* factory = nullptr;
    HRESULT hr = CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void**)&factory);
    if (FAILED(hr) || !factory) {
        reportHResultError("CreateDXGIFactory1 failed", hr);
        return false;
    }

    // Find adapter/output
    IDXGIAdapter1* adapter = nullptr;
    bool foundAdapter = false;
    for (UINT i = 0;; i++) {
        if (factory->EnumAdapters1(i, &adapter) == DXGI_ERROR_NOT_FOUND) {
            break;
        }
        if (!adapter) break;

        IDXGIOutput* output = nullptr;
        for (UINT j = 0;; j++) {
            if (adapter->EnumOutputs(j, &output) == DXGI_ERROR_NOT_FOUND) {
                break;
            }
            if (!output) break;

            DXGI_OUTPUT_DESC desc;
            output->GetDesc(&desc);
            if (desc.Monitor == hMon) {
                SafeRelease(output);
                foundAdapter = true;
                goto FoundAdapter;
            }
            SafeRelease(output);
        }
        SafeRelease(adapter);
    }
    if (!foundAdapter) {
        reportError("Unable to find matching adapter for the monitor.");
        SafeRelease(factory);
        return false;
    }

FoundAdapter:
    {
        // Create D3D11 device
        D3D_FEATURE_LEVEL levels[] = { D3D_FEATURE_LEVEL_11_0 };
        D3D_FEATURE_LEVEL outLevel;
        hr = D3D11CreateDevice(
            adapter,
            D3D_DRIVER_TYPE_UNKNOWN,
            nullptr,
            0,  // or D3D11_CREATE_DEVICE_DEBUG
            levels, 1,
            D3D11_SDK_VERSION,
            &device_,
            &outLevel,
            &context_
        );
        if (FAILED(hr) || !device_ || !context_) {
            reportHResultError("D3D11CreateDevice failed", hr);
            SafeRelease(adapter);
            SafeRelease(factory);
            return false;
        }
    }

    // Duplicate output
    IDXGIOutput* dxgiOutput = nullptr;
    adapter->EnumOutputs(0, &dxgiOutput);
    if (!dxgiOutput) {
        reportError("adapter->EnumOutputs(0) returned null.");
        SafeRelease(adapter);
        SafeRelease(factory);
        return false;
    }

    IDXGIOutput1* output1 = nullptr;
    hr = dxgiOutput->QueryInterface(__uuidof(IDXGIOutput1), (void**)&output1);
    if (FAILED(hr) || !output1) {
        reportHResultError("QueryInterface IDXGIOutput1 failed", hr);
        SafeRelease(dxgiOutput);
        SafeRelease(adapter);
        SafeRelease(factory);
        return false;
    }

    hr = output1->DuplicateOutput(device_, &duplication_);
    if (FAILED(hr) || !duplication_) {
        reportHResultError("DuplicateOutput failed", hr);
        SafeRelease(output1);
        SafeRelease(dxgiOutput);
        SafeRelease(adapter);
        SafeRelease(factory);
        return false;
    }
    SafeRelease(output1);
    SafeRelease(dxgiOutput);
    SafeRelease(adapter);
    SafeRelease(factory);
    return true;
}

void CaptureController::cleanupDuplication() {
    SafeRelease(duplication_);
    SafeRelease(context_);
    SafeRelease(device_);
}

void CaptureController::captureLoop() {
    DXGI_OUTDUPL_FRAME_INFO frameInfo;
    HRESULT hr;

    // Fetch the first frame (will always be blank)
    IDXGIResource* desktopRes = nullptr;
    hr = duplication_->AcquireNextFrame(100000, &frameInfo, &desktopRes);
    if (FAILED(hr)) {
        reportHResultError("Failed to acquire first frame", hr);
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        return;
    }
    duplication_->ReleaseFrame();

    while (running_) {
        // Acquire frame
        IDXGIResource* desktopRes = nullptr;
        HRESULT hr = duplication_->AcquireNextFrame(50, &frameInfo, &desktopRes);
        if (hr == DXGI_ERROR_WAIT_TIMEOUT) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            continue;
        }
        if (FAILED(hr) || !desktopRes) {
            reportHResultError("AcquireNextFrame failed", hr);
            SafeRelease(desktopRes);
            break;
        }

        // Query for ID3D11Texture2D
        ID3D11Texture2D* srcTex = nullptr;
        hr = desktopRes->QueryInterface(__uuidof(ID3D11Texture2D), (void**)&srcTex);
        if (FAILED(hr) || !srcTex) {
            reportHResultError("QueryInterface for ID3D11Texture2D failed", hr);
            SafeRelease(desktopRes);
            duplication_->ReleaseFrame();
            break;
        }

        // Copy outTex to a staging texture for CPU read
        D3D11_TEXTURE2D_DESC stagingDesc;
        srcTex->GetDesc(&stagingDesc);
        stagingDesc.BindFlags = 0;
        stagingDesc.Usage = D3D11_USAGE_STAGING;
        stagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE | D3D11_CPU_ACCESS_READ;
        stagingDesc.MiscFlags = 0;

        ID3D11Texture2D* stagingTex = nullptr;
        hr = device_->CreateTexture2D(&stagingDesc, nullptr, &stagingTex);
        if (FAILED(hr) || !stagingTex) {
            reportHResultError("Create stagingTex failed", hr);
            SafeRelease(srcTex);
            SafeRelease(desktopRes);
            duplication_->ReleaseFrame();
            break;
        }

        context_->CopyResource(stagingTex, srcTex);

        // Map the staging texture for CPU read
        D3D11_MAPPED_SUBRESOURCE mapped;
        hr = context_->Map(stagingTex, 0, D3D11_MAP_READ, 0, &mapped);
        if (FAILED(hr)) {
            reportHResultError("Map stagingTex failed", hr);
            SafeRelease(stagingTex);
            SafeRelease(srcTex);
            SafeRelease(desktopRes);
            duplication_->ReleaseFrame();
            break;
        }

        {
            RECT clientRect;
            if (!GetClientRect(hwnd_, &clientRect)) {
                reportError("GetClientRect failed.");
                context_->Unmap(stagingTex, 0);
                SafeRelease(stagingTex);
                SafeRelease(srcTex);
                SafeRelease(desktopRes);
                duplication_->ReleaseFrame();
                break;
            }

            POINT origin = {0, 0};
            if (!ClientToScreen(hwnd_, &origin)) {
                reportError("ClientToScreen failed.");
                context_->Unmap(stagingTex, 0);
                SafeRelease(stagingTex);
                SafeRelease(srcTex);
                SafeRelease(desktopRes);
                duplication_->ReleaseFrame();
                break;
            }
            OffsetRect(&clientRect, origin.x, origin.y);

            int cropX      = clientRect.left;
            int cropY      = clientRect.top;
            int cropWidth  = clientRect.right  - clientRect.left;
            int cropHeight = clientRect.bottom - clientRect.top;

            cropX      = std::max(0, cropX);
            cropY      = std::max(0, cropY);
            cropWidth  = std::min(cropWidth,  (int)stagingDesc.Width  - cropX);
            cropHeight = std::min(cropHeight, (int)stagingDesc.Height - cropY);

            int outSize = cropWidth * cropHeight * 4; // RGBA
            unsigned char* rgbaData = new unsigned char[outSize];

            const int rowPitch = mapped.RowPitch;
            const unsigned char* rowSrc = static_cast<const unsigned char*>(mapped.pData);

            for (int y = 0; y < cropHeight; y++) {
                const unsigned char* srcRow = rowSrc + (y + cropY) * rowPitch + cropX * 4;
                unsigned char* dstRow = rgbaData + y * cropWidth * 4;

                for (int x = 0; x < cropWidth; x++) {
                    unsigned char b = srcRow[x * 4 + 0];
                    unsigned char g = srcRow[x * 4 + 1];
                    unsigned char r = srcRow[x * 4 + 2];
                    unsigned char a = srcRow[x * 4 + 3];

                    dstRow[x * 4 + 0] = r;
                    dstRow[x * 4 + 1] = g;
                    dstRow[x * 4 + 2] = b;
                    dstRow[x * 4 + 3] = a;
                }
            }

            if (captureCallback_) {
                captureCallback_(id_, rgbaData, outSize, cropWidth, cropHeight, cropWidth * 4);
            }

            delete[] rgbaData;
        }

        context_->Unmap(stagingTex, 0);

        SafeRelease(stagingTex);
        SafeRelease(srcTex);
        SafeRelease(desktopRes);
        duplication_->ReleaseFrame();

        std::this_thread::sleep_for(std::chrono::milliseconds(33));
    }
}

// Error reporting
void CaptureController::reportError(const char* msg) {
    if (errorCallback_) {
        errorCallback_(id_, msg);
    }
}

void CaptureController::reportHResultError(const char* msg, HRESULT hr) {
    if (!errorCallback_) return;
    char buffer[512];
    std::snprintf(buffer, sizeof(buffer), "%s (HRESULT=0x%08lX)", msg, hr);
    errorCallback_(id_, buffer);
}