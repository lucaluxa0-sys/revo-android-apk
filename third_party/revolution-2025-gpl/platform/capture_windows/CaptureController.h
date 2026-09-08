/*
 * Copyright (c) 2024
 * Author: Liam Sagi
 */

#pragma once

#include <Windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <thread>
#include <atomic>
 

typedef void (*CaptureCallback)(int id, unsigned char* rgbaData, int length, int width, int height, int stride);
typedef void (*ErrorCallback)(int id, const char* errorMessage);

class CaptureController {
private:
    HWND            hwnd_;
    CaptureCallback captureCallback_;
    ErrorCallback   errorCallback_;
    int             id_;

    std::thread             thread_;
    std::atomic<bool>       running_;

    ID3D11Device*           device_;
    ID3D11DeviceContext*    context_;
    IDXGIOutputDuplication* duplication_;

    bool initDuplication();
    void cleanupDuplication();
    void captureLoop();
    void reportError(const char* msg);
    void reportHResultError(const char* msg, HRESULT hr);
public:
    CaptureController(int id, HWND hwnd, CaptureCallback captureCallback, ErrorCallback errorCallback);
    ~CaptureController();

    void StartCapture();
    void StopCapture();
};
