package main

import (
	"fmt"
	"syscall"
	"unsafe"
)

type OSVERSIONINFOEX struct {
	dwOSVersionInfoSize uint32
	dwMajorVersion      uint32
	dwMinorVersion      uint32
	dwBuildNumber       uint32
	dwPlatformId        uint32
	szCSDVersion        [128]byte
	wServicePackMajor   uint16
	wServicePackMinor   uint16
	wSuiteMask          uint16
	wProductType        byte
	wReserved           byte
}

func determineOs() string {
	var osInfo OSVERSIONINFOEX
	osInfo.dwOSVersionInfoSize = uint32(unsafe.Sizeof(osInfo))

	ntdll := syscall.NewLazyDLL("ntdll.dll")
	rtlGetVersion := ntdll.NewProc("RtlGetVersion")

	ret, _, _ := rtlGetVersion.Call(uintptr(unsafe.Pointer(&osInfo)))
	if ret != 0 {
		fmt.Println("Failed to get OS version.")
		return "unknown"
	}

	if osInfo.dwMajorVersion == 10 && osInfo.dwBuildNumber >= 22000 {
		return "windows11"
	} else if osInfo.dwMajorVersion == 10 {
		return "windows10"
	}

	return "unknown"
}
